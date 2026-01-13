#!/usr/bin/env python3
"""
Radio Command Parser - Python Configuration
All allowed functions and parameter ranges defined in Python.
Handles WF changes with automatic parameter adjustment.
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path


# =============================================================================
# CONFIGURATION - Edit these to change allowed functions and ranges
# =============================================================================

# Allowed functions per parameter
# - queries: list of allowed query types ("all" means any query allowed)
# - control_allowed: True if SET/CHANGE commands allowed, False if read-only
# - change_methods: ["to"] for absolute, ["by"] for delta, ["to", "by"] for both
ALLOWED_FUNCTIONS = {
    "modulation": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
    },
    "bw": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
    },
    "frequency": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to", "by"]
    },
    "wf": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
    },
    "errors": {
        "queries": ["how many"],
        "control_allowed": False,
        "change_methods": []
    },
    "members": {
        "queries": ["how many"],
        "control_allowed": False,
        "change_methods": []
    },
    "battery": {
        "queries": ["how many", "what percentage"],
        "control_allowed": False,
        "change_methods": []
    }
}

# Allowed parameters per Waveform mode
# - bw: list of allowed bandwidth values in Hz
# - frequency_ranges: list of (min_hz, max_hz) tuples
# - modulations: list of allowed modulation types
WF_PARAMS = {
    "NB": {
        "bw": [25e3, 50e3],  # 25 kHz, 50 kHz
        "frequency_ranges": [(30e6, 100e6), (200e6, 600e6)],  # 30-100 MHz, 200-600 MHz
        "modulations": ["8PSK"]
    },
    "WB": {
        "bw": [0.5e6, 1e6, 2e6, 4e6],  # 0.5, 1, 2, 4 MHz
        "frequency_ranges": [(200e6, 600e6)],  # 200-600 MHz
        "modulations": ["QAM4", "QAM16", "QAM32", "QAM64"]
    }
}

# =============================================================================
# PARSER CLASS
# =============================================================================

class RadioCommandParser:
    """Parse and execute natural language commands for radio control."""

    def __init__(self, json_file: str = "radio_state.json"):
        self.json_file = json_file
        self.allowed_functions = ALLOWED_FUNCTIONS
        self.wf_params = WF_PARAMS
        self.radio_state = self._load_state()
        self._init_lexicon()
        print(f"Parser initialized: {len(self.allowed_functions)} parameters, {len(self.wf_params)} WF modes")

    def _load_state(self) -> Dict[str, Any]:
        """Load radio state from JSON file or create default."""
        if Path(self.json_file).exists():
            with open(self.json_file, 'r') as f:
                return json.load(f)
        else:
            # Default state - WB mode
            return {
                "frequency_hz": 450e6,
                "bandwidth_hz": 1e6,
                "waveform": "WB",
                "modulation": "QAM16",
                "battery_percent": 78,
                "battery_voltage": 12.60,
                "members_count": 5,
                "errors": []
            }

    def _save_state(self):
        """Save radio state to JSON file."""
        with open(self.json_file, 'w') as f:
            json.dump(self.radio_state, f, indent=2)

    def _init_lexicon(self):
        """Initialize command lexicon."""
        self.LEX = {
            "verbs": {
                "QUERY": ["get", "what", "which", "show", "read", "check", "query", "inspect", "display",
                         "reveal", "fetch", "lookup", "list", "report", "scan", "status", "diagnose",
                         "identify", "tell", "give", "provide", "current", "reading", "how many",
                         "how much", "what percentage"],
                "CONTROL": ["do", "set", "put", "tune", "change", "adjust", "switch", "modify", "configure",
                           "select", "choose", "increase", "decrease", "raise", "lower", "boost", "reduce",
                           "perform", "run", "execute", "start", "clear", "reset", "reboot"]
            },
            "objects": {
                "frequency": ["frequency", "freq"],
                "bw": ["bandwidth", "bw", "rbw", "vbw", "channel width"],
                "wf": ["waveform", "wf", "wb", "nb", "wideband", "narrowband", "wide band", "narrow band"],
                "modulation": ["modulation", "mod", "qam", "psk", "8psk", "qam4", "qam16", "qam32", "qam64"],
                "errors": ["error", "errors", "fault", "faults", "alarm", "alarms"],
                "members": ["member", "members", "nodes", "devices", "radios"],
                "battery": ["battery", "power", "charge", "voltage", "percent", "percentage", "level"]
            },
            "prepositions": ["to", "by", "at", "on", "into", "in", "for"],
            "units": {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
        }

    def _normalize(self, text: str) -> str:
        """Normalize text for parsing."""
        text = re.sub(r'\s+', ' ', re.sub(r'[^\w\s\.\-]', ' ', text.lower())).strip()
        # Convert spoken numbers to digits
        text = self._normalize_numbers(text)
        # Normalize spoken unit names to abbreviations
        text = self._normalize_units(text)
        return text

    def _normalize_numbers(self, text: str) -> str:
        """Convert spoken numbers to digits (e.g., 'four hundred fifty' -> '450')."""
        ones = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
            'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
            'eighteen': 18, 'nineteen': 19
        }
        tens = {
            'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
            'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
        }
        scales = {
            'hundred': 100,
            'thousand': 1000,
            'million': 1000000
        }

        all_number_words = set(ones.keys()) | set(tens.keys()) | set(scales.keys()) | {'and'}

        words = text.split()
        result = []
        i = 0

        while i < len(words):
            # Check if this word starts a number sequence
            if words[i] in all_number_words and words[i] != 'and':
                # Collect all consecutive number words
                num_words = []
                j = i
                while j < len(words) and words[j] in all_number_words:
                    if words[j] != 'and':  # Skip 'and' but continue collecting
                        num_words.append(words[j])
                    j += 1

                # Convert collected words to number
                if num_words:
                    number = self._words_to_number(num_words, ones, tens, scales)
                    result.append(str(number))
                    i = j
                else:
                    result.append(words[i])
                    i += 1
            else:
                result.append(words[i])
                i += 1

        return ' '.join(result)

    def _words_to_number(self, words: List[str], ones: dict, tens: dict, scales: dict) -> int:
        """Convert list of number words to integer."""
        current = 0
        total = 0

        for word in words:
            if word in ones:
                current += ones[word]
            elif word in tens:
                current += tens[word]
            elif word in scales:
                scale = scales[word]
                if scale == 100:
                    current = current * 100 if current else 100
                elif scale >= 1000:
                    current = current * scale if current else scale
                    total += current
                    current = 0

        return total + current

    def _normalize_units(self, text: str) -> str:
        """Convert spoken unit names to abbreviations."""
        # Order matters - check longer patterns first
        unit_mappings = [
            # Gigahertz variations
            (r'\bgiga\s*hertz\b', 'ghz'),
            (r'\bgigahertz\b', 'ghz'),
            (r'\bgiga\b', 'ghz'),
            # Megahertz variations
            (r'\bmega\s*hertz\b', 'mhz'),
            (r'\bmegahertz\b', 'mhz'),
            (r'\bmega\b', 'mhz'),
            # Kilohertz variations
            (r'\bkilo\s*hertz\b', 'khz'),
            (r'\bkilohertz\b', 'khz'),
            (r'\bkilo\b', 'khz'),
            # Hertz (must be after mega/kilo/giga hertz)
            (r'\bhertz\b', 'hz'),
        ]
        for pattern, replacement in unit_mappings:
            text = re.sub(pattern, replacement, text)
        return text

    def _contains_token(self, text: str, token: str) -> bool:
        """Check if token exists in text as whole word."""
        return f" {token} " in f" {text} "

    def _find_first(self, text: str, tokens: List[str]) -> Optional[str]:
        """Find first matching token in text."""
        for token in tokens:
            if self._contains_token(text, token):
                return token
        return None

    def _detect_verb(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Detect verb type and token."""
        for verb_type, tokens in self.LEX["verbs"].items():
            token = self._find_first(text, tokens)
            if token:
                return verb_type, token
        return None, None

    def _detect_object(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Detect object type and token."""
        for obj_type, tokens in self.LEX["objects"].items():
            token = self._find_first(text, tokens)
            if token:
                return obj_type, token
        return None, None

    def _extract_number_unit(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract number with unit from text."""
        match = re.search(r'\b(\d+(?:\.\d+)?)\s*(hz|khz|mhz|ghz)\b', text)
        if match:
            return {"value": float(match.group(1)), "unit": match.group(2)}
        return None

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract number from text."""
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
        return float(match.group(1)) if match else None

    def _hz_from(self, num_dict: Dict[str, Any]) -> float:
        """Convert number with unit to Hz."""
        unit = (num_dict.get("unit") or "mhz").lower()
        multiplier = self.LEX["units"].get(unit, 1)
        return num_dict["value"] * multiplier

    def _hz_str(self, hz: float) -> str:
        """Format Hz value as human-readable string. Omit decimals if whole number."""
        if hz >= 1e9:
            val = hz / 1e9
            return f"{val:.3f} GHz" if val % 1 else f"{int(val)} GHz"
        elif hz >= 1e6:
            val = hz / 1e6
            return f"{val:.3f} MHz" if val % 1 else f"{int(val)} MHz"
        elif hz >= 1e3:
            val = hz / 1e3
            return f"{val:.3f} kHz" if val % 1 else f"{int(val)} kHz"
        else:
            return f"{int(hz)} Hz" if hz % 1 == 0 else f"{hz:.1f} Hz"

    def _is_query_allowed(self, param: str) -> bool:
        """Check if query is allowed for parameter."""
        if param in self.allowed_functions:
            queries = self.allowed_functions[param]["queries"]
            return len(queries) > 0
        return False

    def _is_control_allowed(self, param: str) -> bool:
        """Check if control is allowed for parameter."""
        if param in self.allowed_functions:
            return self.allowed_functions[param]["control_allowed"]
        return False

    def _get_change_methods(self, param: str) -> List[str]:
        """Get allowed change methods for parameter."""
        if param in self.allowed_functions:
            return self.allowed_functions[param]["change_methods"]
        return []

    def _validate_frequency(self, freq_hz: float, wf: str) -> Tuple[bool, str]:
        """Validate frequency against WF constraints."""
        if wf not in self.wf_params:
            return True, ""

        ranges = self.wf_params[wf]["frequency_ranges"]
        if not ranges:
            return True, ""

        for low, high in ranges:
            if low <= freq_hz <= high:
                return True, ""

        range_strs = [f"{self._hz_str(l)}-{self._hz_str(h)}" for l, h in ranges]
        return False, f"Frequency must be in: {', '.join(range_strs)} for {wf} mode"

    def _validate_bandwidth(self, bw_hz: float, wf: str) -> Tuple[bool, str]:
        """Validate bandwidth against WF constraints."""
        if wf not in self.wf_params:
            return True, ""

        allowed_bw = self.wf_params[wf]["bw"]
        if not allowed_bw:
            return True, ""

        # Check if close to any allowed value (within 1%)
        for allowed in allowed_bw:
            if abs(bw_hz - allowed) / allowed < 0.01:
                return True, ""

        bw_strs = [self._hz_str(b) for b in allowed_bw]
        return False, f"Bandwidth must be one of: {', '.join(bw_strs)} for {wf} mode"

    def _validate_modulation(self, mod: str, wf: str) -> Tuple[bool, str]:
        """Validate modulation against WF constraints."""
        if wf not in self.wf_params:
            return True, ""

        allowed_mods = [m.upper() for m in self.wf_params[wf]["modulations"]]
        if not allowed_mods:
            return True, ""

        if mod.upper() in allowed_mods:
            return True, ""

        return False, f"Modulation must be one of: {', '.join(allowed_mods)} for {wf} mode"

    def _adjust_params_for_wf(self, new_wf: str) -> Dict[str, Any]:
        """Get adjusted parameters when switching WF mode."""
        adjustments = {}

        if new_wf not in self.wf_params:
            return adjustments

        wf_config = self.wf_params[new_wf]

        # Adjust BW if current not in allowed list
        current_bw = self.radio_state["bandwidth_hz"]
        valid_bw, _ = self._validate_bandwidth(current_bw, new_wf)
        if not valid_bw and wf_config["bw"]:
            adjustments["bandwidth_hz"] = wf_config["bw"][0]

        # Adjust frequency if current not in allowed range
        current_freq = self.radio_state["frequency_hz"]
        valid_freq, _ = self._validate_frequency(current_freq, new_wf)
        if not valid_freq and wf_config["frequency_ranges"]:
            # Set to middle of first range
            low, high = wf_config["frequency_ranges"][0]
            adjustments["frequency_hz"] = (low + high) / 2

        # Adjust modulation if current not in allowed list
        current_mod = self.radio_state["modulation"]
        valid_mod, _ = self._validate_modulation(current_mod, new_wf)
        if not valid_mod and wf_config["modulations"]:
            adjustments["modulation"] = wf_config["modulations"][0]

        return adjustments

    def _detect_wf_value(self, text: str) -> Optional[str]:
        """Detect WF value (NB/WB) from text."""
        normalized = self._normalize(text)
        if any(w in normalized for w in ["nb", "narrow", "narrowband", "narrow band"]):
            return "NB"
        if any(w in normalized for w in ["wb", "wide", "wideband", "wide band"]):
            return "WB"
        return None

    def _detect_modulation_value(self, text: str) -> Optional[str]:
        """Detect modulation value from text."""
        normalized = self._normalize(text)
        mods = ["8psk", "qam4", "qam16", "qam32", "qam64"]
        for mod in mods:
            if mod in normalized:
                return mod.upper()
        return None

    def get_command_type(self, user_input: str) -> str:
        """Determine if command is QUERY, CONTROL, or UNKNOWN."""
        normalized = self._normalize(user_input)
        verb_type, _ = self._detect_verb(normalized)
        return verb_type if verb_type else "UNKNOWN"

    def get_normalized(self, user_input: str) -> str:
        """Return the normalized version of the command (numbers and units converted)."""
        return self._normalize(user_input)

    def get_command_summary(self, user_input: str) -> str:
        """Return a clean summary of the command for logging (e.g., 'frequency: 450 MHz')."""
        normalized = self._normalize(user_input)
        verb_type, _ = self._detect_verb(normalized)
        obj_type, _ = self._detect_object(normalized)

        if not obj_type:
            return "unknown command"

        # For QUERY commands, return just the parameter name
        if verb_type == "QUERY":
            if obj_type == "frequency":
                return "frequency"
            elif obj_type == "bw":
                return "bandwidth"
            elif obj_type == "wf":
                return "waveform"
            elif obj_type == "modulation":
                return "modulation"
            elif obj_type == "battery":
                return "battery"
            elif obj_type == "members":
                return "members"
            elif obj_type == "errors":
                return "errors"
            else:
                return obj_type

        # For CONTROL commands, return the target value
        elif verb_type == "CONTROL":
            num_unit = self._extract_number_unit(normalized)
            num = self._extract_number(normalized)

            if obj_type == "frequency":
                if num_unit or num:
                    hz = self._hz_from(num_unit or {"value": num, "unit": "mhz"})
                    return f"frequency: {self._hz_str(hz)}"
                return "frequency: change"
            elif obj_type == "bw":
                if num_unit or num:
                    hz = self._hz_from(num_unit or {"value": num, "unit": "khz"})
                    return f"bandwidth: {self._hz_str(hz)}"
                return "bandwidth: change"
            elif obj_type == "wf":
                wf = self._detect_wf_value(normalized)
                return f"waveform: {wf}" if wf else "waveform: change"
            elif obj_type == "modulation":
                mod = self._detect_modulation_value(normalized)
                return f"modulation: {mod}" if mod else "modulation: change"
            elif obj_type == "errors":
                return "errors: clear"
            else:
                return f"{obj_type}: control"

        return f"{obj_type}: unknown"

    def process_command(self, user_input: str) -> str:
        """Process user command end-to-end."""
        normalized = self._normalize(user_input)
        verb_type, verb_token = self._detect_verb(normalized)

        if not verb_type:
            return "Unknown command - verb not detected"

        obj_type, obj_token = self._detect_object(normalized)

        if not obj_type:
            return "Unknown command - object not detected"

        # QUERY commands
        if verb_type == "QUERY":
            if not self._is_query_allowed(obj_type):
                return f"Query not allowed for {obj_type}"

            if obj_type == "frequency":
                return f"Frequency: {self._hz_str(self.radio_state['frequency_hz'])}"
            elif obj_type == "bw":
                return f"Bandwidth: {self._hz_str(self.radio_state['bandwidth_hz'])}"
            elif obj_type == "wf":
                return f"Waveform: {self.radio_state['waveform']}"
            elif obj_type == "modulation":
                return f"Modulation: {self.radio_state['modulation']}"
            elif obj_type == "errors":
                errors = self.radio_state.get('errors', [])
                return f"Errors: {len(errors)}" if not errors else f"Errors ({len(errors)}): {', '.join(errors)}"
            elif obj_type == "members":
                return f"Members count: {self.radio_state.get('members_count', 0)}"
            elif obj_type == "battery":
                return f"Battery: {self.radio_state['battery_percent']}% at {self.radio_state['battery_voltage']:.2f} V"

        # CONTROL commands
        elif verb_type == "CONTROL":
            if not self._is_control_allowed(obj_type):
                return f"Control not allowed for {obj_type}"

            prep = self._find_first(normalized, self.LEX["prepositions"])
            change_methods = self._get_change_methods(obj_type)

            if prep and prep not in change_methods:
                return f"Change method '{prep}' not allowed for {obj_type}. Use: {', '.join(change_methods)}"

            num_unit = self._extract_number_unit(normalized)
            num = self._extract_number(normalized)
            current_wf = self.radio_state["waveform"]

            # Frequency control
            if obj_type == "frequency":
                if prep == "to" and (num_unit or num):
                    new_freq = self._hz_from(num_unit or {"value": num, "unit": "mhz"})
                    valid, msg = self._validate_frequency(new_freq, current_wf)
                    if not valid:
                        return msg
                    self.radio_state["frequency_hz"] = new_freq
                    self._save_state()
                    return f"Frequency set to {self._hz_str(new_freq)}"
                elif prep == "by" and (num_unit or num):
                    delta = self._hz_from(num_unit or {"value": num, "unit": "mhz"})
                    if any(w in normalized for w in ["decrease", "lower", "reduce", "down"]):
                        delta = -delta
                    new_freq = self.radio_state["frequency_hz"] + delta
                    valid, msg = self._validate_frequency(new_freq, current_wf)
                    if not valid:
                        return msg
                    self.radio_state["frequency_hz"] = new_freq
                    self._save_state()
                    return f"Frequency changed to {self._hz_str(new_freq)}"
                else:
                    return "Specify frequency value with unit (e.g., 'set frequency to 450 mhz')"

            # Bandwidth control
            elif obj_type == "bw":
                if prep == "to" and (num_unit or num):
                    new_bw = self._hz_from(num_unit or {"value": num, "unit": "khz"})
                    valid, msg = self._validate_bandwidth(new_bw, current_wf)
                    if not valid:
                        return msg
                    self.radio_state["bandwidth_hz"] = new_bw
                    self._save_state()
                    return f"Bandwidth set to {self._hz_str(new_bw)}"
                else:
                    return "Specify bandwidth value with unit (e.g., 'set bw to 25 khz')"

            # Waveform control
            elif obj_type == "wf":
                new_wf = self._detect_wf_value(normalized)
                if not new_wf:
                    return "Specify waveform: NB (narrowband) or WB (wideband)"

                if new_wf == current_wf:
                    return f"Already in {new_wf} mode"

                # Get adjustments needed for new WF
                adjustments = self._adjust_params_for_wf(new_wf)

                # Apply WF change
                old_wf = self.radio_state["waveform"]
                self.radio_state["waveform"] = new_wf

                # Apply adjustments
                adjustment_msgs = []
                for key, value in adjustments.items():
                    old_val = self.radio_state[key]
                    self.radio_state[key] = value
                    if key == "frequency_hz":
                        adjustment_msgs.append(f"Frequency: {self._hz_str(old_val)} to {self._hz_str(value)}")
                    elif key == "bandwidth_hz":
                        adjustment_msgs.append(f"Bandwidth: {self._hz_str(old_val)} to {self._hz_str(value)}")
                    elif key == "modulation":
                        adjustment_msgs.append(f"Modulation: {old_val} to {value}")

                self._save_state()

                result = f"Waveform changed from {old_wf} to {new_wf}"
                if adjustment_msgs:
                    result += ". Auto-adjusted: " + ", ".join(adjustment_msgs)
                return result

            # Modulation control
            elif obj_type == "modulation":
                new_mod = self._detect_modulation_value(normalized)
                if not new_mod:
                    return "Specify modulation type (e.g., 8PSK, QAM16, QAM64)"

                valid, msg = self._validate_modulation(new_mod, current_wf)
                if not valid:
                    return msg

                self.radio_state["modulation"] = new_mod
                self._save_state()
                return f"Modulation set to {new_mod}"

            # Errors - only clear allowed
            elif obj_type == "errors":
                if any(w in normalized for w in ["clear", "reset"]):
                    self.radio_state["errors"] = []
                    self._save_state()
                    return "Errors cleared"
                return "Only 'clear errors' is allowed"

        return "Command not recognized"

    def get_state(self) -> Dict[str, Any]:
        """Get current radio state."""
        return self.radio_state.copy()

    def print_state(self):
        """Print formatted radio state."""
        print("\n=== Radio State ===")
        print(f"Waveform: {self.radio_state['waveform']}")
        print(f"Frequency: {self._hz_str(self.radio_state['frequency_hz'])}")
        print(f"Bandwidth: {self._hz_str(self.radio_state['bandwidth_hz'])}")
        print(f"Modulation: {self.radio_state['modulation']}")
        print(f"Battery: {self.radio_state['battery_percent']}% ({self.radio_state['battery_voltage']:.2f} V)")
        print(f"Members: {self.radio_state.get('members_count', 0)}")
        errors = self.radio_state.get('errors', [])
        print(f"Errors: {', '.join(errors) if errors else 'NONE'}")
        print("=" * 20 + "\n")


def interactive_mode():
    """Run interactive command mode."""
    parser = RadioCommandParser()

    print("=" * 60)
    print("RADIO COMMAND PARSER")
    print("=" * 60)
    parser.print_state()

    print("Examples:")
    print("  - get frequency")
    print("  - set frequency to 450 mhz")
    print("  - set wf to nb")
    print("  - set modulation to qam16")
    print("  - get battery")
    print("  - get members")
    print("\nType 'state' to see current state, 'quit' to exit\n")

    while True:
        try:
            user_input = input("Command> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if user_input.lower() == 'state':
                parser.print_state()
                continue

            response = parser.process_command(user_input)
            print(f"-> {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    interactive_mode()
