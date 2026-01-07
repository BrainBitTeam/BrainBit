import sys
import json
import webrtcvad
import os
import subprocess
import threading
import queue
from vosk import Model, KaldiRecognizer

# --- CONFIGURATION ---
MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FRAME_MS = 30 
HOTWORD = "hi radio"

# Paths for your native espeak-ng build
ESPEAK_BIN = "/home/root/espeak_native/bin/espeak-ng"
LIB_PATH = "/home/root/espeak_native/lib"
AUDIO_DEVICE = "plughw:1,0"

# Queue for non-blocking TTS
speech_queue = queue.Queue()

def speech_worker():
    """
    Worker thread to handle TTS. 
    Running this in a separate thread prevents the microphone 
    processing from lagging while the system is talking.
    """
    while True:
        text = speech_queue.get()
        if text is None: break
        
        # -q flag in aplay hides logs; LD_LIBRARY_PATH ensures the native lib is used
        cmd = f'LD_LIBRARY_PATH={LIB_PATH} {ESPEAK_BIN} -v en-us -s 170 "{text}" --stdout | aplay -D {AUDIO_DEVICE} -q'
        try:
            subprocess.run(cmd, shell=True, check=True)
        except Exception as e:
            print(f"Error in audio pipeline: {e}")
        
        speech_queue.task_done()

def speak_async(text):
    """Adds text to the speech queue without blocking the main loop."""
    print(f"DEBUG: Speaking -> {text}")
    speech_queue.put(text)

def run_test():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        return

    model = Model(MODEL_PATH)
    vad = webrtcvad.Vad(3)
    
    # Pre-initialize both recognizers to save CPU cycles during state switching
    rec_hotword = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    rec_generic = KaldiRecognizer(model, SAMPLE_RATE)
    
    # Start the TTS background thread
    threading.Thread(target=speech_worker, daemon=True).start()
    
    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)
    state = 0 # 0: Waiting for hotword, 1: Listening for echo
    current_rec = rec_hotword
    
    print(f"\n--- System Ready. Say '{HOTWORD}' ---")
    speak_async("Radio system is online")

    while True:
        # Read chunk from stdin (e.g., from arecord pipe)
        data = sys.stdin.buffer.read(n)
        if not data: continue

        if vad.is_speech(data, SAMPLE_RATE):
            if current_rec.AcceptWaveform(data):
                result = json.loads(current_rec.Result())
                text = result.get("text", "").lower()
                
                if not text: continue
                
                if state == 0:
                    if HOTWORD in text:
                        print("\n>>> HOTWORD DETECTED")
                        speak_async("I am listening")
                        current_rec = rec_generic
                        state = 1
                else:
                    # Echo Mode: Repeat what you said
                    print(f">>> ECHO: {text}")
                    speak_async(f"You said {text}")
                    
                    # Reset to Hotword mode immediately
                    current_rec = rec_hotword
                    state = 0
                    print(f"\n--- Ready for '{HOTWORD}' again ---")

if __name__ == "__main__":
    try:
        # Optimization: Set process priority if running as root
        try:
            os.nice(-10) 
        except:
            pass
            
        run_test()
    except KeyboardInterrupt:
        print("\nTest stopped.")