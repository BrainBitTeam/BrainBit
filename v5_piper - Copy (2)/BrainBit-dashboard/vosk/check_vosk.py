import wave
import sys
import json
from vosk import Model, KaldiRecognizer

# Update this path to where your model folder is located
MODEL_PATH = "vosk-model-small-en-us-0.15" 

if not wave.open("test.wav", "rb"):
    print("Could not open test.wav")
    exit(1)

model = Model(MODEL_PATH)
wf = wave.open("test.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

print("--- Starting Vosk Processing ---")
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        print(rec.Result())

print("\n--- Final Result ---")
print(rec.FinalResult())