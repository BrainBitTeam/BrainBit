import sys, json, webrtcvad, os
from vosk import Model, KaldiRecognizer

MODEL_PATH = "model"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"
LOG_FILE = "/home/root/vosk_text.txt"

def dispatch_command(text):
    print(f"\n[EXECUTE] Command: '{text}'")
    with open(LOG_FILE, "a") as f:
        f.write(text + "\n")
    if "frequency" in text:
        print(">>> ACTION: Tuning Radio...")
    elif "status" in text:
        print(">>> ACTION: Fetching Status...")

def run_live_system():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}"); return
    
    model = Model(MODEL_PATH)
    vad = webrtcvad.Vad(3)
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    state = 0 
    
    print(f"\n--- System Ready. Say '{HOTWORD}' ---", flush=True)

    while True:
        data = sys.stdin.buffer.read(n)
        if not data: break

        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text = res.get("text", "").lower()
                if state == 1 and text:
                    dispatch_command(text)
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
                    print(f"\n--- Waiting for '{HOTWORD}' ---")
            else:
                partial = json.loads(rec.PartialResult())
                p_text = partial.get("partial", "").lower()
                if state == 0 and HOTWORD in p_text:
                    print("\n" + "="*25 + "\n>>> RADIO ACTIVE\n" + "="*25)
                    rec = KaldiRecognizer(model, SAMPLE_RATE)
                    state = 1
                    print("Listening for command...")

if __name__ == "__main__":
    try:
        run_live_system()
    except KeyboardInterrupt:
        print("\nStopping...")