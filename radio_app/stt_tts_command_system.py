#!/usr/bin/env python3
"""
ZCU102 Side - Voice Command System with Confirmation
Integrates STT, TTS, TCP, and RadioCommandParser.
Asks for yes/no confirmation on control commands.
Offers "anything else?" prompt after each command with 10s timeout.
"""

import socket
import threading
import sys
import json
import os
import subprocess
import queue
import time
import webrtcvad
from vosk import Model, KaldiRecognizer
from radio_command_parser import RadioCommandParser

# --- CONFIGURATION ---
HOST = "0.0.0.0"
PORT = 5000
PC_CONN = None
PARSER = None  # Global parser reference for startup data

MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
FRAME_MS = 30
HOTWORD = "hi radio"
CONTINUE_TIMEOUT = 10.0  # seconds to wait for "anything else?" response

ESPEAK_BIN = "/home/root/espeak_native/bin/espeak-ng"
LIB_PATH = "/home/root/espeak_native/lib"
AUDIO_DEVICE = "plughw:1,0"

speech_queue = queue.Queue()

# State machine states
STATE_WAITING_HOTWORD = 0
STATE_LISTENING_COMMAND = 1
STATE_WAITING_CONFIRMATION = 2
STATE_WAITING_CONTINUE = 3

# --- TTS Worker ---
def speech_worker():
    while True:
        text = speech_queue.get()
        if text is None:
            break
        cmd = f'LD_LIBRARY_PATH={LIB_PATH} {ESPEAK_BIN} -v en-us -s 170 "{text}" --stdout | aplay -D {AUDIO_DEVICE} -q'
        try:
            subprocess.run(cmd, shell=True, check=True)
        except Exception as e:
            print(f"Error in TTS pipeline: {e}")
        speech_queue.task_done()

def speak_async(text):
    print(f"TTS: {text}")
    speech_queue.put(text)

def speak_sync(text):
    """Speak and wait for completion before continuing."""
    print(f"TTS: {text}")
    speech_queue.put(text)
    speech_queue.join()

# --- TCP Communication Threads ---
def tcp_listener(conn):
    """Receives and handles messages from PC."""
    global PC_CONN, PARSER
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                print("PC disconnected.")
                break
            message = data.decode('utf-8').strip()
            print(f"[PC]: {message}")

            # Check if it's a manual command from PC
            if message.lower().startswith("manual:"):
                handle_manual_command(message)
            else:
                speak_async(message)
        except ConnectionError:
            print("Connection lost.")
            break

def handle_manual_command(message):
    """Handle manual commands from PC to update radio state."""
    global PARSER
    if not PARSER:
        print("Parser not initialized")
        return

    # Parse: "manual: frequency: 400mhz" -> param="frequency", value="400mhz"
    try:
        # Remove "manual:" prefix
        content = message.split(":", 1)[1].strip()
        # Split into param and value
        parts = content.split(":", 1)
        if len(parts) != 2:
            print(f"Invalid manual command format: {message}")
            send_to_pc(f"error: invalid format")
            return

        param = parts[0].strip().lower()
        value = parts[1].strip().lower()

        state = PARSER.radio_state
        response = ""

        if param == "frequency":
            # Parse frequency value
            hz = parse_value_to_hz(value, default_unit="mhz")
            if hz:
                state["frequency_hz"] = hz
                response = f"frequency: {PARSER._hz_str(hz)}"
            else:
                response = "error: invalid frequency"

        elif param == "bandwidth" or param == "bw":
            # Parse bandwidth value
            hz = parse_value_to_hz(value, default_unit="khz")
            if hz:
                state["bandwidth_hz"] = hz
                response = f"bandwidth: {PARSER._hz_str(hz)}"
            else:
                response = "error: invalid bandwidth"

        elif param == "waveform" or param == "wf":
            wf = value.upper()
            if wf in ["NB", "WB"]:
                state["waveform"] = wf
                response = f"waveform: {wf}"
            else:
                response = "error: invalid waveform (use NB or WB)"

        elif param == "modulation" or param == "mod":
            mod = value.upper()
            state["modulation"] = mod
            response = f"modulation: {mod}"

        elif param == "battery":
            try:
                percent = int(value.replace("%", ""))
                state["battery_percent"] = percent
                response = f"battery: {percent}%"
            except:
                response = "error: invalid battery value"

        elif param == "members":
            try:
                count = int(value)
                state["members_count"] = count
                response = f"members: {count}"
            except:
                response = "error: invalid members value"

        else:
            response = f"error: unknown parameter '{param}'"

        # Save state
        if not response.startswith("error"):
            PARSER._save_state()
            print(f"Manual update: {response}")
        else:
            print(f"Manual command error: {response}")

    except Exception as e:
        print(f"Error handling manual command: {e}")

def parse_value_to_hz(value, default_unit="mhz"):
    """Parse value string like '400mhz' or '25khz' to Hz."""
    import re
    value = value.lower().replace(" ", "")

    # Try to match number with unit
    match = re.match(r'([\d.]+)\s*(hz|khz|mhz|ghz)?', value)
    if match:
        num = float(match.group(1))
        unit = match.group(2) or default_unit

        multipliers = {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
        return num * multipliers.get(unit, 1e6)

    return None

def send_to_pc(message):
    """Sends message to connected PC."""
    global PC_CONN
    if PC_CONN:
        try:
            PC_CONN.sendall((message + "\n").encode('utf-8'))
        except:
            print("Failed to send message to PC.")

def send_startup_data():
    """Send all radio state data to PC on connection."""
    global PARSER, PC_CONN
    if not PARSER or not PC_CONN:
        return

    state = PARSER.radio_state

    # Format each value nicely
    freq_str = PARSER._hz_str(state['frequency_hz'])
    bw_str = PARSER._hz_str(state['bandwidth_hz'])

    startup_data = [
        f"startup: frequency: {freq_str}",
        f"startup: bandwidth: {bw_str}",
        f"startup: waveform: {state['waveform']}",
        f"startup: modulation: {state['modulation']}",
        f"startup: battery: {state['battery_percent']}%",
        f"startup: members: {state.get('members_count', 0)}",
        f"startup: errors: {len(state.get('errors', []))}"
    ]

    for line in startup_data:
        try:
            PC_CONN.sendall((line + "\n").encode('utf-8'))
            print(f"Sent: {line}")
        except:
            print(f"Failed to send: {line}")
            break

def tcp_server():
    """Handles new PC connections."""
    global PC_CONN
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Listening for PC on port {PORT}...")
    conn, addr = server.accept()
    print(f"Connected by {addr}")
    PC_CONN = conn
    # Wait 3 seconds before sending startup data
    time.sleep(3)
    send_startup_data()
    threading.Thread(target=tcp_listener, args=(conn,), daemon=True).start()

# --- Helper function to transition to continue state ---
def go_to_continue_state():
    """Returns state info for 'anything else?' prompt."""
    speak_sync("Anything else I can help you with?")
    return STATE_WAITING_CONTINUE, time.time()

def go_to_hotword_state(hotword):
    """Returns state info for hotword waiting."""
    print(f"\n--- Ready for '{hotword}' again ---")
    return STATE_WAITING_HOTWORD, None

# --- Speech Recognition Main Loop ---
def run_system():
    global PARSER

    model = Model(MODEL_PATH)
    vad = webrtcvad.Vad(3)

    # Initialize command parser BEFORE tcp_server so startup data is available
    parser = RadioCommandParser()
    PARSER = parser  # Set global reference for startup data
    print("Command parser initialized.")

    threading.Thread(target=speech_worker, daemon=True).start()
    threading.Thread(target=tcp_server, daemon=True).start()

    rec_hotword = KaldiRecognizer(model, SAMPLE_RATE, f'["{HOTWORD}", "[unk]"]')
    rec_generic = KaldiRecognizer(model, SAMPLE_RATE)
    rec_yesno = KaldiRecognizer(model, SAMPLE_RATE, '["yes", "no", "yeah", "yep", "nope", "cancel", "[unk]"]')

    n = int(SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)

    state = STATE_WAITING_HOTWORD
    current_rec = rec_hotword
    pending_command = ""
    continue_start_time = None

    print(f"\n--- System Ready. Say '{HOTWORD}' ---")
    speak_async("Radio command system is online")

    while True:
        data = sys.stdin.buffer.read(n)
        if not data:
            continue

        # Check timeout for continue state
        if state == STATE_WAITING_CONTINUE:
            if time.time() - continue_start_time > CONTINUE_TIMEOUT:
                print(">>> Continue timeout - returning to hotword state")
                speak_sync("Goodbye")
                # Reset recognizers to clear any buffered audio
                rec_hotword.Reset()
                rec_generic.Reset()
                rec_yesno.Reset()
                current_rec = rec_hotword
                state, continue_start_time = go_to_hotword_state(HOTWORD)
                continue

        if vad.is_speech(data, SAMPLE_RATE):
            if current_rec.AcceptWaveform(data):
                result = json.loads(current_rec.Result())
                text = result.get("text", "").lower().strip()
                if not text:
                    continue

                # State 0: Waiting for hotword
                if state == STATE_WAITING_HOTWORD:
                    if HOTWORD in text:
                        print("\n>>> HOTWORD DETECTED")
                        speak_sync("I am listening")
                        # Reset generic recognizer to clear any old buffered audio
                        rec_generic.Reset()
                        current_rec = rec_generic
                        state = STATE_LISTENING_COMMAND

                # State 1: Listening for command
                elif state == STATE_LISTENING_COMMAND:
                    print(f">>> Command heard: {text}")

                    # Check command type
                    cmd_type = parser.get_command_type(text)
                    print(f">>> Command type: {cmd_type}")

                    if cmd_type == "QUERY":
                        # Execute query immediately without confirmation
                        response = parser.process_command(text)
                        print(f">>> Query response: {response}")
                        speak_sync(response)

                        # Go to continue state (use generic recognizer for commands)
                        current_rec = rec_generic
                        state, continue_start_time = go_to_continue_state()

                    elif cmd_type == "CONTROL":
                        # Ask for confirmation on control commands
                        pending_command = text
                        speak_sync(f"You said {text}. Is that correct?")
                        # Reset yesno recognizer before using it
                        rec_yesno.Reset()
                        current_rec = rec_yesno
                        state = STATE_WAITING_CONFIRMATION

                    else:
                        # Unknown command type
                        speak_sync("Command not recognized.")
                        # Go to continue state (use generic recognizer for commands)
                        current_rec = rec_generic
                        state, continue_start_time = go_to_continue_state()

                # State 2: Waiting for yes/no confirmation (for CONTROL commands)
                elif state == STATE_WAITING_CONFIRMATION:
                    print(f">>> Confirmation response: {text}")

                    # Check for affirmative
                    if any(word in text for word in ["yes", "yeah", "yep", "correct", "right", "affirmative"]):
                        print(f">>> Executing command: {pending_command}")

                        # Get command summary before executing (to capture target value)
                        cmd_summary = parser.get_command_summary(pending_command)

                        # Process command through parser
                        response = parser.process_command(pending_command)
                        print(f">>> Parser response: {response}")

                        # Send to PC for logging (clean format)
                        send_to_pc(f"CMD: {cmd_summary}")

                        # Speak the result
                        speak_sync(response)

                        # Reset and go to continue state (use generic recognizer for commands)
                        pending_command = ""
                        current_rec = rec_generic
                        state, continue_start_time = go_to_continue_state()

                    # Check for negative
                    elif any(word in text for word in ["no", "nope", "cancel", "wrong", "negative"]):
                        print(">>> Command cancelled")
                        speak_sync("Command cancelled.")
                        pending_command = ""
                        # Go to continue state (use generic recognizer for commands)
                        current_rec = rec_generic
                        state, continue_start_time = go_to_continue_state()

                    else:
                        # Didn't understand, ask again
                        speak_sync("Please say yes or no")

                # State 3: Waiting for continue response
                elif state == STATE_WAITING_CONTINUE:
                    print(f">>> Continue response: {text}")

                    # Check for negative - user is done
                    if any(word in text for word in ["no", "nope", "done", "nothing", "goodbye"]):
                        print(">>> User is done")
                        speak_sync("Goodbye")
                        # Reset all recognizers to clear any buffered audio
                        rec_hotword.Reset()
                        rec_generic.Reset()
                        rec_yesno.Reset()
                        current_rec = rec_hotword
                        state, continue_start_time = go_to_hotword_state(HOTWORD)

                    # Check for affirmative - user wants another command
                    elif any(word in text for word in ["yes", "yeah", "yep"]):
                        print(">>> User wants to continue")
                        speak_sync("I am listening")
                        # Reset generic recognizer to clear any old buffered audio
                        rec_generic.Reset()
                        current_rec = rec_generic
                        state = STATE_LISTENING_COMMAND
                        continue_start_time = None

                    else:
                        # Try to process as a command directly
                        cmd_type = parser.get_command_type(text)

                        if cmd_type == "QUERY":
                            # Execute query immediately
                            response = parser.process_command(text)
                            print(f">>> Query response: {response}")
                            speak_sync(response)
                            # Ask again (use generic recognizer for commands)
                            current_rec = rec_generic
                            state, continue_start_time = go_to_continue_state()

                        elif cmd_type == "CONTROL":
                            # Ask for confirmation
                            pending_command = text
                            speak_sync(f"You said {text}. Is that correct?")
                            current_rec = rec_yesno
                            state = STATE_WAITING_CONFIRMATION
                            continue_start_time = None

                        else:
                            # Not recognized as command, ask again
                            speak_sync("I didn't understand. Please say yes, no, or a command.")
                            continue_start_time = time.time()

if __name__ == "__main__":
    run_system()
