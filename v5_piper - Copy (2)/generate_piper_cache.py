#!/usr/bin/env python3
"""
Generate TTS cache for v5 phrases using Piper (lessac voice).
Pre-generates all static and common dynamic phrases.

Usage:
    python generate_piper_cache.py
"""

import os
import subprocess
import hashlib
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, "tts_cache")

# Convert WSL paths to Windows paths if needed
def to_windows_path(path):
    """Convert WSL /mnt/c/... path to Windows C:\\... path."""
    if path.startswith('/mnt/'):
        drive = path[5].upper()
        rest = path[7:].replace('/', '\\')
        return f"{drive}:\\{rest}"
    return path

# Piper configuration
PIPER_PATH = os.path.join(SCRIPT_DIR, "piper", "piper.exe")
PIPER_MODEL = os.path.join(SCRIPT_DIR, "piper", "en_US-lessac-low.onnx")
SPEECH_SPEED = "1.3"  # 1.0 = normal, >1.0 = slower, <1.0 = faster

# =============================================================================
# STATIC PHRASES - System messages, confirmations, errors
# =============================================================================

STATIC_PHRASES = [
    # System messages
    "Radio command system is online",
    "I am listening",
    "Goodbye",
    "Anything else?",
    "Cancelled",
    "Not understood",
    "Not recognized",
    "Command not recognized",
    "Yes or no?",
    "Try again",
    "Say command or cancel.",

    # Confirmation messages
    "Radio settings, confirm?",

    # Clarification messages
    "Change what?",
    "What frequency?",
    "What bandwidth?",
    "Narrowband or wideband?",
    "What modulation?",
    "Low, medium, or high?",
    "What channel?",
    "What volume?",

    # Waveform responses
    "Waveform: narrowband",
    "Waveform: wideband",
    "Waveform changed to narrowband",
    "Waveform changed to wideband",
    "Already in NB mode",
    "Already in WB mode",
    "Waveform options: narrowband, wideband",

    # Modulation responses
    "Modulation: 8PSK",
    "Modulation: QAM4",
    "Modulation: QAM16",
    "Modulation: QAM32",
    "Modulation: QAM64",
    "Modulation set to 8PSK",
    "Modulation set to QAM4",
    "Modulation set to QAM16",
    "Modulation set to QAM32",
    "Modulation set to QAM64",
    "Modulation options for narrowband: 8PSK, QAM16",
    "Modulation options for wideband: QAM4, QAM16, QAM32, QAM64",

    # Power level responses
    "Power level: low",
    "Power level: medium",
    "Power level: high",
    "Power level set to low",
    "Power level set to medium",
    "Power level set to high",
    "Power level is already low",
    "Power level is already medium",
    "Power level is already high",
    "Power options: low, medium, high",

    # LED responses
    "LED: on",
    "LED: off",
    "LED turned on",
    "LED turned off",
    "LED is already on",
    "LED is already off",

    # GPS responses
    "GPS: on",
    "GPS: off",
    "GPS turned on",
    "GPS turned off",
    "GPS is already on",
    "GPS is already off",

    # Receive only mode responses
    "Receive only mode: on",
    "Receive only mode: off",
    "Receive only mode enabled",
    "Receive only mode disabled",
    "Receive only mode is already enabled",
    "Receive only mode is already disabled",

    # BIT responses
    "Performing BIT. BIT results are: All tests passed, 0 errors detected",
    "BIT status: No errors detected",

    # Error/validation messages
    "Errors cleared",
    "No errors detected",
    "Channel 1 to 200 only",
    "Volume 1 to 10 only",
    "Channel options: 1 to 200",
    "Volume options: 1 to 10",
    "Only 'clear errors' is allowed",

    # Member responses
    "No members connected",
    "No weak signals, all members have good signal",
    "No strong signals detected",

    # Options responses
    "Frequency options for narrowband: 30 megahertz to 100 megahertz, 200 megahertz to 600 megahertz",
    "Frequency options for wideband: 200 megahertz to 600 megahertz",
    "Bandwidth options for narrowband: 25 kilohertz, 50 kilohertz",
    "Bandwidth options for wideband: 500 kilohertz, 1 megahertz, 2 megahertz, 4 megahertz",
    "LED options: on, off, toggle",
    "GPS options: on, off, toggle",
    "RXONLY options: on, off, toggle",
    "No options available for members",
    "No options available for battery",
    "No options available for status",
    "No options available for errors",
    "No options available for bit",
    "No options available for config",

    # Control not allowed validation messages
    "Control not allowed for members",
    "Control not allowed for battery",
    "Control not allowed for status",
    "Control not allowed for config",

    # Query not allowed validation messages
    "Query not allowed for frequency",
    "Query not allowed for bandwidth",
    "Query not allowed for waveform",
    "Query not allowed for modulation",
    "Query not allowed for power",
    "Query not allowed for channel",
    "Query not allowed for volume",

    # Additional confirmation prompts
    "members, confirm?",
    "Volume maximum, confirm?",
    "Volume minimum, confirm?",
    "Channel maximum, confirm?",
    "Channel minimum, confirm?",
    "frequency, confirm?",
    "bandwidth, confirm?",
    "waveform, confirm?",
    "modulation, confirm?",
    "power, confirm?",
    "channel, confirm?",
    "volume, confirm?",
    "errors, confirm?",
    "battery, confirm?",
    "status, confirm?",
    "config, confirm?",
    "bit, confirm?",
    "BIT, confirm?",

    # Channel/Volume at limit messages
    "Channel is at minimum",
    "Channel is at maximum",
    "Volume is at minimum",
    "Volume is at maximum",
    "Cannot decrease channel, already at minimum",
    "Cannot increase channel, already at maximum",
    "Cannot decrease volume, already at minimum",
    "Cannot increase volume, already at maximum",
]

# =============================================================================
# DYNAMIC PHRASES - Generated from value ranges
# =============================================================================

def generate_frequency_phrases():
    """Generate frequency-related phrases for common frequencies.

    Valid ranges:
    - Narrowband: 30-100 MHz, 200-600 MHz
    - Wideband: 200-600 MHz
    """
    phrases = []

    # Common frequencies only (selected values)
    common_freqs = [30, 40, 50, 60, 65, 70, 80, 88, 100, 150, 200, 225, 250, 300, 350, 400, 415, 450, 500, 550, 600]
    # Add decimal frequencies
    decimal_freqs = [0.5, 1.5, 2.5]

    for f in common_freqs:
        phrases.append(f"Frequency: {f} megahertz")
        phrases.append(f"Frequency set to {f} megahertz")
        phrases.append(f"Frequency changed to {f} megahertz")

    for f in decimal_freqs:
        phrases.append(f"Frequency: {f} megahertz")

    return phrases

def generate_bandwidth_phrases():
    """Generate bandwidth-related phrases."""
    phrases = []
    # kHz values
    for bw in [25, 50, 100]:
        phrases.append(f"Bandwidth: {bw} kilohertz")
        phrases.append(f"Bandwidth set to {bw} kilohertz")
    # MHz values
    for bw in [0.5, 1, 2, 4, 5]:
        if bw == int(bw):
            phrases.append(f"Bandwidth: {int(bw)} megahertz")
            phrases.append(f"Bandwidth set to {int(bw)} megahertz")
        else:
            phrases.append(f"Bandwidth: {bw} megahertz")
            phrases.append(f"Bandwidth set to {bw} megahertz")
    # Special: 500 kHz
    phrases.append("Bandwidth: 500 kilohertz")
    phrases.append("Bandwidth set to 500 kilohertz")
    return phrases

def generate_channel_phrases():
    """Generate channel-related phrases."""
    phrases = []
    # Channel values 1-200 (common ones)
    common_channels = list(range(1, 21)) + [25, 30, 40, 50, 75, 100, 125, 150, 175, 200]
    for ch in common_channels:
        phrases.append(f"Channel: {ch}")
        phrases.append(f"Channel set to {ch}")
        phrases.append(f"Channel changed to {ch}")
        phrases.append(f"Channel is already at {ch}")
        phrases.append(f"Channel increased to {ch}")
        phrases.append(f"Channel decreased to {ch}")

    # Min/max
    phrases.append("Channel set to minimum (1)")
    phrases.append("Channel set to maximum (200)")
    phrases.append("Channel is already at minimum (1)")
    phrases.append("Channel is already at maximum (200)")
    return phrases

def generate_volume_phrases():
    """Generate volume-related phrases."""
    phrases = []
    for vol in range(1, 11):
        phrases.append(f"Volume: {vol}")
        phrases.append(f"Volume set to {vol}")
        phrases.append(f"Volume changed to {vol}")
        phrases.append(f"Volume is already at {vol}")
        phrases.append(f"Volume increased to {vol}")
        phrases.append(f"Volume decreased to {vol}")

    # Min/max
    phrases.append("Volume set to minimum (1)")
    phrases.append("Volume set to maximum (10)")
    phrases.append("Volume is already at minimum (1)")
    phrases.append("Volume is already at maximum (10)")
    return phrases

def generate_battery_phrases():
    """Generate battery-related phrases."""
    phrases = []
    # Common percentages
    for pct in range(0, 101, 5):
        phrases.append(f"Battery: {pct} percent")
    return phrases

def generate_member_phrases():
    """Generate member-related phrases."""
    phrases = []

    # Member count (0-20 to cover larger networks)
    for count in range(0, 21):
        if count == 1:
            phrases.append("1 member connected")
        else:
            phrases.append(f"{count} members connected")

    # Signal quality with average
    for quality in ["excellent", "good", "fair", "poor"]:
        for rssi in range(-90, -25, 5):
            phrases.append(f"Average signal: {rssi} dBm, network quality: {quality}")

    # Closest/farthest radio (IDs 1-20, RSSI range)
    for id in range(1, 21):
        for rssi in range(-90, -25, 10):
            phrases.append(f"Closest radio: ID {id} with signal {rssi} dBm")
            phrases.append(f"Farthest radio: ID {id} with signal {rssi} dBm")

    # Weak/strong signal counts
    for count in range(1, 8):
        if count == 1:
            phrases.append("1 weak signal")
            phrases.append("1 strong signal")
        else:
            phrases.append(f"{count} weak signals")
            phrases.append(f"{count} strong signals")

    # Member details format (for small groups)
    for count in range(1, 8):
        if count == 1:
            phrases.append(f"{count} member")
        else:
            phrases.append(f"{count} members")
        # With "top 3 signals" prefix
        if count > 3:
            phrases.append(f"{count} members, top 3 signals")

    # Individual member signal reports
    for id in range(1, 21):
        for rssi in range(-90, -25, 10):
            phrases.append(f"ID {id} signal {rssi} dBm")
            phrases.append(f"ID {id} at {rssi} dBm")

    return phrases

def generate_radio_status_phrases():
    """Generate radio status response phrases."""
    phrases = []

    # Radio status with battery and error count
    for battery in range(0, 101, 5):
        for error_count in range(0, 5):
            phrases.append(f"Radio status: Battery {battery}%, {error_count} errors")

    # Radio configuration prefix (the full config is too dynamic to cache all combos)
    phrases.append("Radio configuration")

    return phrases

def generate_error_phrases():
    """Generate error detection phrases."""
    errors = ["VSWR error", "TX error", "RX error", "Voltage error"]
    phrases = []

    # Single errors
    for err in errors:
        phrases.append(f"1 error detected: {err}")
        phrases.append(f"BIT status: 1 errors: {err}")

    # Two error combinations
    for i, e1 in enumerate(errors):
        for e2 in errors[i+1:]:
            combo = f"{e1}, {e2}"
            phrases.append(f"2 errors detected: {combo}")

    # Three error combinations
    for i, e1 in enumerate(errors):
        for j, e2 in enumerate(errors[i+1:], i+1):
            for e3 in errors[j+1:]:
                combo = f"{e1}, {e2}, {e3}"
                phrases.append(f"3 errors detected: {combo}")

    # All four errors
    phrases.append(f"4 errors detected: {', '.join(errors)}")

    # BIT with errors
    for count in range(1, 5):
        phrases.append(f"Performing BIT. BIT results are: {count} errors detected: VSWR error")

    return phrases

def generate_confirmation_phrases():
    """Generate confirmation prompt phrases."""
    phrases = []

    # Frequency confirmations (common values only)
    for f in [30, 50, 100, 200, 300, 400, 450, 500, 600]:
        phrases.append(f"Frequency {f} megahertz, confirm?")

    # Bandwidth confirmations
    for bw in ["25 kilohertz", "50 kilohertz", "500 kilohertz", "1 megahertz", "2 megahertz", "4 megahertz"]:
        phrases.append(f"Bandwidth {bw}, confirm?")

    # Waveform confirmations
    phrases.append("Waveform narrowband, confirm?")
    phrases.append("Waveform wideband, confirm?")

    # Modulation confirmations
    for mod in ["8PSK", "QAM4", "QAM16", "QAM32", "QAM64"]:
        phrases.append(f"Modulation {mod}, confirm?")

    # Power confirmations
    for level in ["low", "medium", "high"]:
        phrases.append(f"Power {level}, confirm?")

    # Channel confirmations (common values)
    for ch in [1, 5, 10, 15, 20, 50, 100, 150, 200]:
        phrases.append(f"Channel {ch}, confirm?")

    # Volume confirmations
    for vol in range(1, 11):
        phrases.append(f"Volume {vol}, confirm?")

    # LED/GPS confirmations
    for state in ["on", "off"]:
        phrases.append(f"LED {state}, confirm?")
        phrases.append(f"GPS {state}, confirm?")

    # Receive only confirmations
    phrases.append("Receive only on, confirm?")
    phrases.append("Receive only off, confirm?")

    # BIT confirmation
    phrases.append("BIT perform, confirm?")

    return phrases

# =============================================================================
# CACHE GENERATION
# =============================================================================

def get_cache_filename(text):
    """Get cache filename for a phrase using MD5 hash."""
    text_hash = hashlib.md5(text.lower().strip().encode()).hexdigest()[:16]
    return f"{text_hash}.wav"


def generate_with_piper(text, output_path):
    """Generate WAV file using Piper."""
    try:
        if not os.path.exists(PIPER_PATH):
            print(f"ERROR: Piper not found at {PIPER_PATH}")
            return False

        if not os.path.exists(PIPER_MODEL):
            print(f"ERROR: Piper model not found at {PIPER_MODEL}")
            return False

        piper_dir = os.path.dirname(PIPER_PATH)
        win_model = to_windows_path(PIPER_MODEL)
        win_output = to_windows_path(output_path)

        cmd = [PIPER_PATH, "--model", win_model, "--output_file", win_output, "--length_scale", SPEECH_SPEED]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=piper_dir
        )
        stdout, stderr = proc.communicate(input=text.encode('utf-8'), timeout=60)

        if proc.returncode != 0:
            print(f"  Piper error: {stderr.decode()}")
            return False

        if not os.path.exists(output_path):
            print(f"  File not created: {output_path}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print(f"  Timeout generating: {text[:50]}...")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def generate_cache():
    """Generate cache files for all phrases."""
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Collect all phrases
    all_phrases = list(STATIC_PHRASES)
    all_phrases.extend(generate_frequency_phrases())
    all_phrases.extend(generate_bandwidth_phrases())
    all_phrases.extend(generate_channel_phrases())
    all_phrases.extend(generate_volume_phrases())
    all_phrases.extend(generate_battery_phrases())
    all_phrases.extend(generate_member_phrases())
    all_phrases.extend(generate_radio_status_phrases())
    all_phrases.extend(generate_error_phrases())
    all_phrases.extend(generate_confirmation_phrases())

    # Remove duplicates while preserving order
    seen = set()
    unique_phrases = []
    for p in all_phrases:
        p_lower = p.lower().strip()
        if p_lower not in seen:
            seen.add(p_lower)
            unique_phrases.append(p)

    print("=" * 60)
    print("PIPER TTS CACHE GENERATOR (v5)")
    print("=" * 60)
    print(f"Piper: {PIPER_PATH}")
    print(f"Model: {PIPER_MODEL}")
    print(f"Output: {CACHE_DIR}")
    print(f"Total phrases: {len(unique_phrases)}")
    print("=" * 60)
    print()

    mapping = {}
    generated = 0
    skipped = 0
    failed = 0

    for i, phrase in enumerate(unique_phrases, 1):
        filename = get_cache_filename(phrase)
        filepath = os.path.join(CACHE_DIR, filename)

        progress = f"[{i}/{len(unique_phrases)}]"

        if os.path.exists(filepath):
            print(f"{progress} [exists] {phrase[:50]}...")
            skipped += 1
        else:
            print(f"{progress} [generating] {phrase[:50]}...")
            if generate_with_piper(phrase, filepath):
                generated += 1
            else:
                failed += 1
                continue

        mapping[phrase.lower().strip()] = filename

    # Save mapping file
    mapping_file = os.path.join(CACHE_DIR, "mapping.json")
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Generated: {generated}")
    print(f"Skipped (existing): {skipped}")
    print(f"Failed: {failed}")
    print(f"Total cached: {generated + skipped}")
    print()
    print("NEXT STEPS:")
    print("1. Copy 'tts_cache' folder to ZCU102: /home/root/tts_cache/")
    print("2. Copy Python files to ZCU102: /home/root/")
    print("3. Run: python3 stt_tts_command_system_fast_v5.py")
    print("=" * 60)


if __name__ == "__main__":
    generate_cache()
