import sys
import json
import webrtcvad
import os
import subprocess
from vosk import Model, KaldiRecognizer

# --- CONFIGURATION ---
MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"

# Paths for your native espeak-ng build
ESPEAK_BIN = "/home/root/espeak_native/bin/espeak-ng"
LIB_PATH = "/home/root/espeak_native/lib"
AUDIO_DEVICE = "plughw:1,0"  # Using plughw to handle Mono->Stereo

def speak(text):
    """Pipes espeak output to aplay with automatic channel conversion."""
    print(f"DEBUG: Speaking -> {text}")
    
    # We build the command string with the LD_LIBRARY_PATH included
    # -v en-us: Voice, -s 160: Speed, --stdout: Outputs raw wave
    cmd = f'LD_LIBRARY_PATH={LIB_PATH} {ESPEAK_BIN} -v en-us -s 160 "{text}" --stdout | aplay -D {AUDIO_DEVICE}'
    
    try:
        # shell=True is required to use the pipe (|)
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Error in audio pipeline: {e}")

def run_test():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        return

    model = Model(MODEL_PATH)
    vad = webrtcvad.Vad(3)
    
    # Initial recognizer for the hotword
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    state = 0 # 0: Waiting for hotword, 1: Listening for echo
    
    print(f"\n--- eSpeak Test Ready. Say '{HOTWORD}' ---")
    speak("Radio system is online")

    while True:
        data = sys.stdin.buffer.read(n)
        if not data: continue

        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                if not text: continue
                
                if state == 0:
                    if HOTWORD in text:
                        print("\n>>> HOTWORD DETECTED")
                        speak("I am listening")
                        # Switch to generic recognizer for any text
                        rec = KaldiRecognizer(model, SAMPLE_RATE) 
                        state = 1
                else:
                    # Echo Mode: Repeat what you said
                    print(f">>> ECHO: {text}")
                    speak(f"You said {text}")
                    
                    # Reset to Hotword
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
                    print(f"\n--- Ready for '{HOTWORD}' again ---")

if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print("\nTest stopped.")