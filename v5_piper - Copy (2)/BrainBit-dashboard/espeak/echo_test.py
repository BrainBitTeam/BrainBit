import sys
import json
import webrtcvad
import os
import subprocess
from vosk import Model, KaldiRecognizer

# --- SETTINGS ---
MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"

ESPEAK_BIN = "/home/root/espeak_native/bin/espeak-ng"
LIB_PATH = "/home/root/espeak_native/lib"
AUDIO_DEVICE = "plughw:1,0"

def speak(text):
    """The confirmed working pipe for your Jabra headset."""
    print(f"\n[SYSTEM SPEAKING]: {text}")
    # Using 'aplay -q' to keep the terminal clean
    cmd = f'LD_LIBRARY_PATH={LIB_PATH} {ESPEAK_BIN} -v en-us -s 160 "{text}" --stdout | aplay -D {AUDIO_DEVICE} -q'
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Audio Error: {e}")

def run_test():
    print("Initializing Vosk... please wait.")
    model = Model(MODEL_PATH)
    vad = webrtcvad.Vad(3)
    
    # State 0 = Waiting for 'Hi Radio'
    # State 1 = Listening to echo back
    state = 0 
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    
    # Pre-calculated frame size
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)

    # Initial greeting
    speak("System ready")
    print(f"--- Listening for '{HOTWORD}' ---")

    while True:
        # Read audio chunk from the pipe (from arecord)
        data = sys.stdin.buffer.read(n)
        if not data: continue

        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                
                if not text: continue
                print(f"Heard: {text}")

                if state == 0:
                    if HOTWORD in text:
                        speak("I am listening")
                        # Switch to 'Full Vocabulary' mode
                        rec = KaldiRecognizer(model, SAMPLE_RATE)
                        state = 1
                else:
                    # The Echo Action
                    speak(f"You said {text}")
                    # Switch back to 'Hotword' mode
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
                    print(f"--- Waiting for '{HOTWORD}' ---")

if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print("\nTest stopped by user.")