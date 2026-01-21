#!/usr/bin/env python3
"""
Voice Command System with Confirmation (Cross-Platform: Windows/Linux)
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

# --- PLATFORM (Linux Only) ---
IS_WINDOWS = False

# --- CONFIGURATION ---
HOST = "0.0.0.0"
PORT = 5000
PC_CONN = None
PARSER = None  # Global parser reference for startup data

# Platform-specific paths
if IS_WINDOWS:
    # Windows: Vosk model in same directory or specify your path
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "vosk-model-small-en-us-0.15")
    # Alternative: set absolute path
    # MODEL_PATH = r"C:\Users\user\vosk-model-small-en-us-0.15"
else:
    # Linux (ZCU102)
    MODEL_PATH = "/home/root/vosk-model-small-en-us-0.15"

SAMPLE_RATE = 16000
FRAME_MS = 30
HOTWORD = "hi radio"
CONTINUE_TIMEOUT = 10.0  # seconds to wait for "anything else?" response

# TTS configuration (platform-specific)
if IS_WINDOWS:
    # Windows: Piper TTS
    PIPER_DIR = os.path.join(os.path.dirname(__file__), "piper", "piper")
    PIPER_BIN = os.path.join(PIPER_DIR, "piper.exe")
    PIPER_MODEL = os.path.join(os.path.dirname(__file__), "piper", "en_US-lessac-medium.onnx")
else:
    # Linux (ZCU102): espeak-ng
    ESPEAK_BIN = "/home/root/espeak_native/bin/espeak-ng"
    LIB_PATH = "/home/root/espeak_native/lib"
    AUDIO_DEVICE = "plughw:1,0"

speech_queue = queue.Queue()

# --- TTS Engine Setup ---
if IS_WINDOWS:
    if os.path.exists(PIPER_BIN) and os.path.exists(PIPER_MODEL):
        print(f"TTS: Using Piper at {PIPER_BIN}")
    else:
        print("WARNING: Piper TTS not found. Check piper folder.")

# State machine states
STATE_WAITING_HOTWORD = 0
STATE_LISTENING_COMMAND = 1
STATE_WAITING_CONFIRMATION = 2
STATE_WAITING_CONTINUE = 3
STATE_WAITING_CLARIFICATION = 4  # Waiting for user to provide missing value

# --- TTS Worker ---
def speech_worker():
    import tempfile
    while True:
        text = speech_queue.get()
        if text is None:
            break
        try:
            if IS_WINDOWS:
                # Windows: Use Piper TTS
                if os.path.exists(PIPER_BIN):
                    # Create temp wav file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        temp_wav = f.name
                    # Generate speech with Piper
                    process = subprocess.Popen(
                        [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", temp_wav],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    process.communicate(input=text.encode('utf-8'))
                    # Play the wav file
                    import winsound
                    winsound.PlaySound(temp_wav, winsound.SND_FILENAME)
                    # Clean up
                    os.unlink(temp_wav)
                else:
                    print(f"[TTS disabled] Would say: {text}")
            else:
                # Linux: Use espeak-ng with aplay
                cmd = f'LD_LIBRARY_PATH={LIB_PATH} {ESPEAK_BIN} -v en-us -s 170 "{text}" --stdout | aplay -D {AUDIO_DEVICE} -q'
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
    # Socket options differ between Windows and Linux
    if IS_WINDOWS:
        # On Windows, SO_REUSEADDR allows multiple sockets to bind to same port
        # which is usually not what we want, so we skip it
        # But we can use SO_EXCLUSIVEADDRUSE to prevent port hijacking
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except AttributeError:
            pass  # Not available on older Python versions
    else:
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

# --- Global abort words - can exit from any state ---
ABORT_WORDS = ["abort", "cancel", "exit", "bye", "goodbye", "stop", "quit", "nevermind", "never mind"]

def is_abort_command(text: str) -> bool:
    """Check if text is an abort command."""
    text_lower = text.lower()
    return any(word in text_lower for word in ABORT_WORDS)

# --- Helper function to transition to continue state ---
def go_to_continue_state():
    """Returns state info for 'anything else?' prompt."""
    speak_sync("Anything else?")
    return STATE_WAITING_CONTINUE, time.time()

def go_to_hotword_state(hotword):
    """Returns state info for hotword waiting."""
    print(f"\n--- Ready for '{hotword}' again ---")
    return STATE_WAITING_HOTWORD, None

# Object name mapping for pronoun resolution
OBJECT_NAMES = {
    "led": "light",
    "gps": "GPS",
    "rxonly": "receive only mode",
    "volume": "volume",
    "channel": "channel",
    "frequency": "frequency",
    "bw": "bandwidth",
    "wf": "waveform",
    "modulation": "modulation",
    "power": "power",
    "bit": "BIT"
}

def resolve_pronouns(text: str, last_object: str) -> str:
    """Replace pronouns like 'it' with the last discussed object.
    Only replaces in action patterns like 'turn it on', 'set it to', etc.
    Does NOT replace 'that', 'this' as they're often used in other contexts.
    """
    if not last_object:
        return text

    words = text.split()

    # Only replace "it" - not "that" or "this" as they cause false positives
    if "it" not in words:
        return text

    # Get the friendly name for the object
    obj_name = OBJECT_NAMES.get(last_object, last_object)

    # Only replace "it" in action contexts (followed by on/off/up/down/to or preceded by action verbs)
    action_patterns = [
        " it on", " it off", " it up", " it down", " it to ",
        "turn it", "set it", "change it", "get it", "check it",
        "increase it", "decrease it", "enable it", "disable it"
    ]

    # Check if any action pattern exists
    if any(pattern in text for pattern in action_patterns):
        text = text.replace(" it ", f" {obj_name} ")
        text = text.replace(" it on", f" {obj_name} on")
        text = text.replace(" it off", f" {obj_name} off")
        text = text.replace(" it up", f" {obj_name} up")
        text = text.replace(" it down", f" {obj_name} down")

    return text

def extract_object_from_summary(cmd_summary: str) -> str:
    """Extract the object type from command summary.
    Example: 'LED: off' -> 'led', 'volume: 5' -> 'volume'
    """
    if ":" in cmd_summary:
        param = cmd_summary.split(":")[0].strip().lower()
        # Map summary names back to internal object types
        name_to_obj = {
            "led": "led", "light": "led",
            "gps": "gps",
            "receive only": "rxonly",
            "volume": "volume",
            "channel": "channel",
            "frequency": "frequency",
            "bandwidth": "bw",
            "waveform": "wf",
            "modulation": "modulation",
            "power": "power",
            "bit": "bit",
            "configuration": "config"
        }
        return name_to_obj.get(param, param)
    return None

def get_confirmation_message(cmd_summary: str) -> str:
    """Generate a short confirmation message from command summary.
    Example: 'frequency: 400 MHz' -> 'Frequency 400 MHz, confirm?'
    """
    if ":" in cmd_summary:
        parts = cmd_summary.split(":", 1)
        param = parts[0].strip().capitalize()
        value = parts[1].strip()
        return f"{param} {value}, confirm?"
    else:
        return f"{cmd_summary}, confirm?"

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

    # --- Audio Input Setup (Platform-specific) ---
    audio_stream = None
    if IS_WINDOWS:
        try:
            import sounddevice as sd
            import numpy as np
            # Create a raw input stream for 16-bit audio
            print(f"Audio: Using sounddevice for microphone input")
            audio_stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='int16',
                blocksize=n // 2  # frames (samples), not bytes
            )
            audio_stream.start()
        except ImportError:
            print("ERROR: sounddevice not installed. Run: pip install sounddevice")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Could not open audio device: {e}")
            sys.exit(1)
    else:
        print("Audio: Using stdin (pipe audio with arecord or similar)")

    state = STATE_WAITING_HOTWORD
    current_rec = rec_hotword
    pending_command = ""
    pending_clarification_param = None  # Track what parameter needs clarification
    pending_confirmation_summary = ""   # Track command summary for confirmation
    last_error_param = None  # Track last parameter that had a validation error (for contextual responses)
    last_object = None  # Track last object discussed for pronoun resolution ("it", "that")
    continue_start_time = None

    print(f"\n--- System Ready. Say '{HOTWORD}' ---")
    speak_async("Radio command system is online")

    # VAD state tracking for realtime feedback
    vad_active = False
    silence_frames = 0
    SILENCE_THRESHOLD = 15  # frames of silence before speech end

    while True:
        # Read audio data (platform-specific)
        if IS_WINDOWS:
            try:
                data, overflowed = audio_stream.read(n // 2)  # read frames
                data = bytes(data)  # convert to bytes for VAD/recognizer
            except Exception as e:
                print(f"Audio read error: {e}")
                continue
        else:
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
                vad_active = False
                silence_frames = 0
                continue

        is_speech = vad.is_speech(data, SAMPLE_RATE)

        # VAD start/stop detection with visual feedback
        if is_speech:
            silence_frames = 0
            if not vad_active:
                vad_active = True
                #print("\n>>> [VAD START] Listening...")
        else:
            if vad_active:
                silence_frames += 1
                if silence_frames >= SILENCE_THRESHOLD:
                    vad_active = False
                    #print("\n>>> [VAD STOP]")

        # Always feed audio to recognizer
        current_rec.AcceptWaveform(data)

        # Show partial results in realtime while speaking
        #if vad_active:
        #    partial = json.loads(current_rec.PartialResult())
        #     partial_text = partial.get("partial", "").strip()
        #    if partial_text:
        #        print(f"\r>>> Hearing: {partial_text}                    ", end="", flush=True)

        # Process final result when speech ends
        if not vad_active and silence_frames == SILENCE_THRESHOLD:
            result = json.loads(current_rec.Result())
            text = result.get("text", "").lower().strip()
            if not text:
                continue
            print(f"\n>>> Final: {text}")

            # State 0: Waiting for hotword
            if state == STATE_WAITING_HOTWORD:
                if HOTWORD in text:
                    print(">>> HOTWORD DETECTED")
                    speak_sync("I am listening")
                    rec_generic.Reset()
                    current_rec = rec_generic
                    state = STATE_LISTENING_COMMAND

            # State 1: Listening for command
            elif state == STATE_LISTENING_COMMAND:
                print(f">>> Command heard: {text}")

                # Check for global abort
                if is_abort_command(text):
                    print(">>> Abort command detected")
                    speak_sync("Goodbye")
                    state, continue_start_time = go_to_hotword_state(HOTWORD)
                    continue

                # Resolve pronouns like "it", "that" using last discussed object
                original_text = text
                text = resolve_pronouns(text, last_object)
                if text != original_text:
                    print(f">>> Pronoun resolved: {text}")

                cmd_type = parser.get_command_type(text)
                print(f">>> Command type: {cmd_type}")

                if cmd_type == "QUERY":
                    # Track last object for pronoun resolution
                    cmd_summary = parser.get_command_summary(text)
                    detected_obj = extract_object_from_summary(cmd_summary)
                    if detected_obj:
                        last_object = detected_obj
                        print(f">>> Tracking object: {last_object}")

                    # Config/settings query needs confirmation (lots of info)
                    is_config_query = "configuration" in cmd_summary.lower() or (detected_obj and "config" in detected_obj)
                    if is_config_query:
                        print(">>> Settings query - asking confirmation")
                        pending_command = text
                        pending_confirmation_summary = cmd_summary
                        speak_sync("Radio settings, confirm?")
                        rec_yesno.Reset()
                        current_rec = rec_yesno
                        state = STATE_WAITING_CONFIRMATION
                    else:
                        # Other queries respond immediately
                        response = parser.process_command(text)
                        print(f">>> Query response: {response}")
                        speak_sync(response)
                        current_rec = rec_generic
                        state, continue_start_time = go_to_continue_state()

                elif cmd_type == "CONTROL":
                    # Get command summary to check if value is understood
                    cmd_summary = parser.get_command_summary(text)
                    # Track last object for pronoun resolution
                    detected_obj = extract_object_from_summary(cmd_summary)
                    if detected_obj:
                        last_object = detected_obj
                        print(f">>> Tracking object: {last_object}")

                    # Check if summary indicates missing value (ends with ": change" or similar)
                    needs_clarification = cmd_summary.endswith(": change") or "unknown" in cmd_summary.lower()

                    # Save state to memory BEFORE dry-run (file may be modified during dry-run)
                    saved_state = parser.radio_state.copy()

                    # Also do a dry-run to check for CLARIFY response
                    test_response = parser.process_command(text)
                    if parser.is_clarification(test_response):
                        needs_clarification = True
                        # Revert any changes from memory
                        parser.radio_state = saved_state
                        parser._save_state()

                    # Check if dry-run returned a validation error
                    is_validation_error = any(phrase in test_response.lower() for phrase in [
                        "must be", "not allowed", "invalid", "out of range", "cannot"
                    ])

                    if needs_clarification and parser.is_clarification(test_response):
                        # Value not understood - ask for clarification
                        clarify_msg = parser.get_clarification_message(test_response)
                        pending_clarification_param = parser.get_clarification_param(test_response)
                        print(f">>> Needs clarification for: {pending_clarification_param}")
                        speak_sync(clarify_msg)
                        rec_generic.Reset()
                        current_rec = rec_generic
                        state = STATE_WAITING_CLARIFICATION
                    elif is_validation_error:
                        # Value is invalid - revert from memory
                        parser.radio_state = saved_state
                        parser._save_state()
                        # Remember which parameter had the error for contextual follow-up
                        last_error_param = cmd_summary.split(":")[0].strip() if ":" in cmd_summary else None
                        print(f">>> Validation error for '{last_error_param}': {test_response}")
                        speak_sync(test_response)
                        current_rec = rec_generic
                        state, continue_start_time = go_to_continue_state()
                    else:
                        # Revert any changes from dry-run using saved memory state
                        parser.radio_state = saved_state
                        parser._save_state()
                        # Command understood - ask for confirmation with what it will do
                        pending_command = text
                        pending_confirmation_summary = cmd_summary
                        confirm_msg = get_confirmation_message(cmd_summary)
                        print(f">>> Asking confirmation: {confirm_msg}")
                        speak_sync(confirm_msg)
                        rec_yesno.Reset()
                        current_rec = rec_yesno
                        state = STATE_WAITING_CONFIRMATION

                else:
                    speak_sync("Not recognized")
                    current_rec = rec_generic
                    state, continue_start_time = go_to_continue_state()

            # State 2: Waiting for yes/no confirmation
            elif state == STATE_WAITING_CONFIRMATION:
                print(f">>> Confirmation response: {text}")

                # Check for global abort (exit completely)
                if any(word in text.lower() for word in ["abort", "exit", "bye", "goodbye", "quit"]):
                    print(">>> Abort command detected")
                    speak_sync("Goodbye")
                    pending_command = ""
                    state, continue_start_time = go_to_hotword_state(HOTWORD)
                    continue

                if any(word in text for word in ["yes", "yeah", "yep", "correct", "right", "affirmative"]):
                    print(f">>> Executing command: {pending_command}")
                    cmd_summary = parser.get_command_summary(pending_command)
                    response = parser.process_command(pending_command)
                    print(f">>> Parser response: {response}")
                    send_to_pc(f"CMD: {cmd_summary}")
                    speak_sync(response)
                    pending_command = ""
                    last_error_param = None  # Clear error context on success
                    current_rec = rec_generic
                    state, continue_start_time = go_to_continue_state()

                elif any(word in text for word in ["no", "nope", "cancel", "wrong", "negative"]):
                    print(">>> Command cancelled")
                    speak_sync("Cancelled")
                    pending_command = ""
                    current_rec = rec_generic
                    state, continue_start_time = go_to_continue_state()

                else:
                    speak_sync("Yes or no?")

            # State 3: Waiting for continue response
            elif state == STATE_WAITING_CONTINUE:
                print(f">>> Continue response: {text}")

                if any(word in text.lower() for word in ["no", "nope", "done", "nothing", "goodbye", "bye", "exit", "abort", "quit", "stop"]):
                    print(">>> User is done")
                    speak_sync("Goodbye")
                    rec_hotword.Reset()
                    rec_generic.Reset()
                    rec_yesno.Reset()
                    current_rec = rec_hotword
                    last_error_param = None  # Clear error context
                    state, continue_start_time = go_to_hotword_state(HOTWORD)

                elif any(word in text for word in ["yes", "yeah", "yep"]):
                    print(">>> User wants to continue")
                    speak_sync("I am listening")
                    rec_generic.Reset()
                    current_rec = rec_generic
                    state = STATE_LISTENING_COMMAND
                    continue_start_time = None

                else:
                    # Resolve pronouns like "it", "that" using last discussed object
                    original_text = text
                    text = resolve_pronouns(text, last_object)
                    if text != original_text:
                        print(f">>> Pronoun resolved: {text}")

                    cmd_type = parser.get_command_type(text)

                    if cmd_type == "QUERY":
                        # Track last object for pronoun resolution
                        cmd_summary = parser.get_command_summary(text)
                        detected_obj = extract_object_from_summary(cmd_summary)
                        if detected_obj:
                            last_object = detected_obj
                            print(f">>> Tracking object: {last_object}")

                        # Config/settings query needs confirmation (lots of info)
                        is_config_query = "configuration" in cmd_summary.lower() or (detected_obj and "config" in detected_obj)
                        if is_config_query:
                            print(">>> Settings query - asking confirmation")
                            pending_command = text
                            pending_confirmation_summary = cmd_summary
                            speak_sync("Radio settings, confirm?")
                            rec_yesno.Reset()
                            current_rec = rec_yesno
                            state = STATE_WAITING_CONFIRMATION
                            continue_start_time = None
                        else:
                            # Other queries respond immediately
                            response = parser.process_command(text)
                            print(f">>> Query response: {response}")
                            speak_sync(response)
                            current_rec = rec_generic
                            state, continue_start_time = go_to_continue_state()

                    elif cmd_type == "CONTROL":
                        # Get command summary to check if value is understood
                        cmd_summary = parser.get_command_summary(text)
                        # Track last object for pronoun resolution
                        detected_obj = extract_object_from_summary(cmd_summary)
                        if detected_obj:
                            last_object = detected_obj
                            print(f">>> Tracking object: {last_object}")

                        # Save state to memory BEFORE dry-run (file may be modified during dry-run)
                        saved_state = parser.radio_state.copy()

                        # Do a dry-run to check for CLARIFY response or validation error
                        test_response = parser.process_command(text)

                        # Check if dry-run returned a validation error
                        is_validation_error = any(phrase in test_response.lower() for phrase in [
                            "must be", "not allowed", "invalid", "out of range", "cannot"
                        ])

                        if parser.is_clarification(test_response):
                            # Revert from memory and ask for clarification
                            parser.radio_state = saved_state
                            parser._save_state()
                            clarify_msg = parser.get_clarification_message(test_response)
                            pending_clarification_param = parser.get_clarification_param(test_response)
                            print(f">>> Needs clarification for: {pending_clarification_param}")
                            speak_sync(clarify_msg)
                            rec_generic.Reset()
                            current_rec = rec_generic
                            state = STATE_WAITING_CLARIFICATION
                            continue_start_time = None
                        elif is_validation_error:
                            # Value is invalid - revert from memory
                            parser.radio_state = saved_state
                            parser._save_state()
                            last_error_param = cmd_summary.split(":")[0].strip() if ":" in cmd_summary else None
                            print(f">>> Validation error for '{last_error_param}': {test_response}")
                            speak_sync(test_response)
                            speak_sync("Try again")
                            continue_start_time = time.time()
                        else:
                            # Revert any changes from dry-run using saved memory state
                            parser.radio_state = saved_state
                            parser._save_state()
                            pending_command = text
                            pending_confirmation_summary = cmd_summary
                            confirm_msg = get_confirmation_message(cmd_summary)
                            speak_sync(confirm_msg)
                            current_rec = rec_yesno
                            state = STATE_WAITING_CONFIRMATION
                            continue_start_time = None

                    else:
                        # Command not recognized - but check if we have context from a recent validation error
                        if last_error_param:
                            # Save state to memory before dry-run
                            saved_state = parser.radio_state.copy()

                            # Try to interpret as a value for the last parameter that had an error
                            constructed_cmd = f"set {last_error_param} to {text}"
                            print(f">>> Trying contextual command: {constructed_cmd}")
                            test_response = parser.process_command(constructed_cmd)

                            if parser.is_clarification(test_response):
                                # Still didn't understand - revert from memory
                                parser.radio_state = saved_state
                                parser._save_state()
                                speak_sync("I didn't understand. Please say yes, no, or a command.")
                                continue_start_time = time.time()
                            elif any(phrase in test_response.lower() for phrase in ["must be", "not allowed", "invalid", "out of range", "cannot"]):
                                # Another validation error - revert from memory
                                parser.radio_state = saved_state
                                parser._save_state()
                                print(f">>> Validation error: {test_response}")
                                speak_sync(test_response)
                                continue_start_time = time.time()
                            else:
                                # Command understood - revert from memory and ask for confirmation
                                parser.radio_state = saved_state
                                parser._save_state()
                                pending_command = constructed_cmd
                                cmd_summary = parser.get_command_summary(constructed_cmd)
                                pending_confirmation_summary = cmd_summary
                                last_error_param = None  # Clear the context
                                confirm_msg = get_confirmation_message(cmd_summary)
                                print(f">>> Asking confirmation: {confirm_msg}")
                                speak_sync(confirm_msg)
                                current_rec = rec_yesno
                                state = STATE_WAITING_CONFIRMATION
                                continue_start_time = None
                        else:
                            speak_sync("I didn't understand. Please say yes, no, or a command.")
                            continue_start_time = time.time()

            # State 4: Waiting for clarification (user provides missing value)
            elif state == STATE_WAITING_CLARIFICATION:
                print(f">>> Clarification response: {text}")

                # Check for global abort (exit completely)
                if any(word in text.lower() for word in ["abort", "exit", "bye", "goodbye", "quit"]):
                    print(">>> Abort command detected")
                    speak_sync("Goodbye")
                    pending_clarification_param = None
                    state, continue_start_time = go_to_hotword_state(HOTWORD)
                    continue

                # Check if user wants to cancel (stay in conversation)
                if any(word in text for word in ["no", "nope", "cancel", "nevermind", "forget", "stop"]):
                    print(">>> Clarification cancelled")
                    speak_sync("Cancelled")
                    pending_clarification_param = None
                    current_rec = rec_generic
                    state, continue_start_time = go_to_continue_state()

                else:
                    # Try to construct command with clarified value
                    param = pending_clarification_param

                    # Special case: user is telling us WHAT parameter to change
                    if param == "parameter":
                        # User said something like "frequency" or "bandwidth"
                        # Construct a change command and see if it needs further clarification (for the value)
                        constructed_cmd = f"change {text}"
                    # Special case: user said waveform term when asked for bandwidth
                    # "narrow band" / "wide band" means waveform, not bandwidth value
                    elif param == "bw" and any(w in text for w in ["narrow", "wide", "nb", "wb", "narrowband", "wideband"]):
                        constructed_cmd = f"set waveform to {text}"
                        print(f">>> Detected waveform term, redirecting to waveform")
                    else:
                        constructed_cmd = f"set {param} to {text}"
                    print(f">>> Constructed command: {constructed_cmd}")

                    # Save state to memory BEFORE dry-run
                    saved_state = parser.radio_state.copy()

                    # Test the constructed command (dry-run)
                    test_response = parser.process_command(constructed_cmd)

                    if parser.is_clarification(test_response):
                        # Still didn't understand - revert from memory and ask again
                        parser.radio_state = saved_state
                        parser._save_state()
                        # Update the clarification param to the new one (e.g., "parameter" -> "frequency")
                        pending_clarification_param = parser.get_clarification_param(test_response)
                        clarify_msg = parser.get_clarification_message(test_response)
                        print(f">>> Still needs clarification for: {pending_clarification_param}")
                        speak_sync(clarify_msg)
                        # Stay in clarification state
                    else:
                        # Revert any changes from dry-run using saved memory state
                        parser.radio_state = saved_state
                        parser._save_state()
                        # Value understood - now ask for confirmation
                        pending_command = constructed_cmd
                        cmd_summary = parser.get_command_summary(constructed_cmd)
                        pending_confirmation_summary = cmd_summary
                        pending_clarification_param = None
                        confirm_msg = get_confirmation_message(cmd_summary)
                        print(f">>> Asking confirmation: {confirm_msg}")
                        speak_sync(confirm_msg)
                        rec_yesno.Reset()
                        current_rec = rec_yesno
                        state = STATE_WAITING_CONFIRMATION

if __name__ == "__main__":
    run_system()
