import sys, json, webrtcvad, os, subprocess
from vosk import Model, KaldiRecognizer

# Settings
MODEL_PATH = "model"
SAMPLE_RATE = 16000
HOTWORD = "hi radio"

def speak(text):
    """Uses espeak to talk back through the ZCU102 audio out."""
    print(f">>> SPEAKING: {text}")
    # '-s 150' is speed, '-a 100' is volume
    subprocess.run(["espeak-ng", "-s", "160", text])

class RadioDecisionTree:
    def process(self, text):
        # This is your 'Decision Tree' logic
        if "frequency" in text:
            if "high" in text or "increase" in text:
                self.set_frequency("up")
            elif "low" in text or "decrease" in text:
                self.set_frequency("down")
            else:
                speak("Which frequency would you like?")
        
        elif "status" in text:
            # You could add logic here to check Zynq PL registers
            speak("System status is nominal. Temperature is 45 degrees.")
            
        elif "light" in text or "led" in text:
            speak("Toggling the onboard LED.")
            # os.system("echo 1 > /sys/class/gpio/...")

    def set_frequency(self, direction):
        speak(f"Changing frequency {direction}")
        # Add your FPGA/Hardware control here

def run_live_system():
    model = Model(MODEL_PATH)
    vad = webrtcvad.Vad(3)
    tree = RadioDecisionTree()
    
    # Start in Hotword Mode
    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    state = 0 
    
    print(f"--- System Ready. ---", flush=True)

    while True:
        data = sys.stdin.buffer.read(960) # 30ms frame
        if not data: break

        if vad.is_speech(data, SAMPLE_RATE):
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text = res.get("text", "").lower()
                
                if state == 1 and text:
                    # THINK AND ACT
                    tree.process(text)
                    # RESET to Hotword
                    rec = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
                    state = 0
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "")
                if state == 0 and HOTWORD in partial:
                    speak("Ready") # Auditory feedback that it heard the hotword
                    rec = KaldiRecognizer(model, SAMPLE_RATE)
                    state = 1

if __name__ == "__main__":
    run_live_system()