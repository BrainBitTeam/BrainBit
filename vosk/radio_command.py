import sys
import json
import webrtcvad
import os
from vosk import Model, KaldiRecognizer

# Configuration
MODEL_PATH = "model"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"

def run_live_system():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        return

    vad = webrtcvad.Vad(3)
    model = Model(MODEL_PATH)
    # Update this line inside your radio_command.py
    # This tells Vosk: "Only listen for 'hi radio' or unknown noise"
    rec = KaldiRecognizer(model, SAMPLE_RATE, '["hi radio", "[unk]"]')    
    # Bytes per 30ms frame (16000 samples/sec * 0.03 sec * 2 bytes)
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    
    state = 0 # 0: Waiting for Hotword, 1: Capturing Command
    print(f"--- System Ready. Say '{HOTWORD}' ---")

    while True:
        # Read exactly 'n' bytes from the pipe
        data = sys.stdin.buffer.read(n)
        
        if not data:
            continue # Keep loop alive even if pipe is momentarily empty

        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                
                if not text: continue
                
                print(f"[Heard]: {text}")

                if state == 0:
                    if HOTWORD in text:
                        command = text.split(HOTWORD)[-1].strip()
                        print("\n" + "="*20)
                        print(">>> RADIO ACTIVE")
                        print("="*20)
                        if command:
                            print(f">>> COMMAND: {command}")
                        state = 1
                else:
                    print(f">>> NEXT COMMAND: {text}")
                    # After one command, reset to wait for "Hi Radio" again
                    state = 0
                    print(f"\n--- Waiting for '{HOTWORD}' ---")

if __name__ == "__main__":
    try:
        run_live_system()
    except KeyboardInterrupt:
        print("\nStopping...")