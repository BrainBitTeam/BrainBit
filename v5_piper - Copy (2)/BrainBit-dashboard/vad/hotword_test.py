import wave
import json
import webrtcvad
import os
from vosk import Model, KaldiRecognizer

# Configuration
MODEL_PATH = "model"
AUDIO_FILE = "/home/root/test.wav"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi elbit"

def run_hotword_test():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Vosk model not found at {MODEL_PATH}")
        return

    # Initialize
    vad = webrtcvad.Vad(3)
    model = Model(MODEL_PATH)
    # Optimization: You can tell Vosk to specifically look for your hotword
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    
    if not os.path.exists(AUDIO_FILE):
        print("ERROR: No test.wav found. Record one first!")
        return
        
    wf = wave.open(AUDIO_FILE, "rb")
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    
    print(f"--- Listening for Hotword: '{HOTWORD}' ---")

    while True:
        data = wf.readframes(int(SAMPLE_RATE * FRAME_MS / 1000.0))
        if len(data) < n:
            break

        # VAD Gatekeeper
        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                
                if HOTWORD in text:
                    print("\n" + "="*30)
                    print(">>> HOTWORD DETECTED: System Activated!")
                    print("="*30 + "\n")
                elif text:
                    print(f"Heard: {text}")

    # Check the final buffer
    final = json.loads(rec.FinalResult()).get("text", "").lower()
    if HOTWORD in final:
        print("\n>>> HOTWORD DETECTED in Final Buffer!")

if __name__ == "__main__":
    run_hotword_test()