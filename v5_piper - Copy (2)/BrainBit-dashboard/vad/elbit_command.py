import wave
import json
import webrtcvad
import os
import sys
from vosk import Model, KaldiRecognizer

# Configuration
MODEL_PATH = "model"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi elbit"

def run_session():
    # Initialize
    vad = webrtcvad.Vad(3)
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, SAMPLE_RATE) # Full vocab for the command
    
    # We use a state machine: 0 = Waiting for Hotword, 1 = Capturing Command
    state = 0 
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    
    print(f"--- System Ready. Say '{HOTWORD}' followed by your command. ---")

    # If you want to use the test.wav file for a quick test:
    wf = wave.open("/home/root/test.wav", "rb")

    while True:
        data = wf.readframes(int(SAMPLE_RATE * FRAME_MS / 1000.0))
        if len(data) < n: break

        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                
                if not text: continue

                if state == 0:
                    if HOTWORD in text:
                        # Find what came after the hotword in the same string
                        command = text.split(HOTWORD)[-1].strip()
                        print("\n>>> HOTWORD TRIGGERED")
                        
                        if command:
                            print(f">>> COMMAND RECEIVED: {command}")
                            return command # Return the string
                        else:
                            print(">>> Listening for command...")
                            state = 1 # Switch to command mode
                else:
                    print(f">>> COMMAND RECEIVED: {text}")
                    return text

    # Check final buffer if file ends
    final = json.loads(rec.FinalResult()).get("text", "").lower()
    if state == 1 or HOTWORD in final:
        cmd = final.split(HOTWORD)[-1].strip()
        print(f">>> FINAL COMMAND: {cmd}")
        return cmd

if __name__ == "__main__":
    captured_text = run_session()
    # Now you can use captured_text for your next logic