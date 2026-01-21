import sys
import json
import webrtcvad
import socket
from vosk import Model, KaldiRecognizer

MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FRAME_MS = 30
HOTWORD = "hi radio"

# TCP Settings
PC_IP = '192.168.1.10'
PORT = 5000

def send_tcp_message(message):
    """Send message to PC via TCP"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((PC_IP, PORT))
            client.sendall(message.encode('utf-8'))
            print(f"[TCP] Sent: {message}")
    except Exception as e:
        print(f"[TCP] Error sending: {e}")

def run_live_system():
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    vad = webrtcvad.Vad(3)
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    state = 0

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
                        rec = KaldiRecognizer(model, SAMPLE_RATE)
                        state = 1
                else:
                    print(f">>> COMMAND RECEIVED: {text}")
                    # Send command via TCP to PC
                    send_tcp_message(text)
                    # Switch back to hotword
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
                    print(f"\n--- Waiting for '{HOTWORD}' ---")

if __name__ == "__main__":
    run_live_system()
