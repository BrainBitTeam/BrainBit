import sys
import json
import webrtcvad
import os
import subprocess
from vosk import Model, KaldiRecognizer

# --- CONFIGURATION ---
# Updated to your actual model path
MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"

# Path to your NEW native espeak-ng and the Jabra device (Card 1)
ESPEAK_BIN = "/home/root/espeak_native/bin/espeak-ng"
AUDIO_DEVICE = "hw:1,0" 

def speak(text):
    """Uses the natively built espeak-ng to talk through the Jabra headset."""
    print(f"DEBUG: Speaking -> {text}")
    try:
        # We use -D to specify the hardware device directly
        subprocess.run([ESPEAK_BIN, "-v", "en-us", "-D", AUDIO_DEVICE, text], check=True)
    except Exception as e:
        print(f"Error calling espeak-ng: {e}")

def run_live_system():
    # 1. Load Model
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        return

    model = Model(MODEL_PATH)
    
    # 2. Pre-initialize Recognizer
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    
    vad = webrtcvad.Vad(3)
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    state = 0 
    
    print(f"--- System Ready. Say '{HOTWORD}' ---", flush=True)
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
                        print("\n>>> RADIO ACTIVE")
                        speak("How can I help?")
                        # Switch to full vocab
                        rec = KaldiRecognizer(model, SAMPLE_RATE) 
                        state = 1
                else:
                    print(f">>> COMMAND RECEIVED: {text}")
                    speak(f"Received command {text}")
                    # Switch back to hotword
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
                    print(f"\n--- Waiting for '{HOTWORD}' ---")

if __name__ == "__main__":
    run_live_system()