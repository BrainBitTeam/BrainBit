import sys
import json
import webrtcvad
import os
from vosk import Model, KaldiRecognizer

MODEL_PATH = "model"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"

def run_live_system():
    # 1. Load Model (Heavy CPU)
    model = Model(MODEL_PATH)
    
    # 2. Pre-initialize Recognizer (Heavy CPU)
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    
    vad = webrtcvad.Vad(3)
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    state = 0 
    
    # 3. Print Ready ONLY after everything is loaded
    print(f"--- System Ready. Say '{HOTWORD}' ---", flush=True)

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
                        # Switch to full vocab
                        rec = KaldiRecognizer(model, SAMPLE_RATE) 
                        state = 1
                else:
                    print(f">>> COMMAND RECEIVED: {text}")
                    # Switch back to hotword
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
                    print(f"\n--- Waiting for '{HOTWORD}' ---")

if __name__ == "__main__":
    run_live_system()