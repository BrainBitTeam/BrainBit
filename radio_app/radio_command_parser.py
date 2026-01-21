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
    },
    "status": {
        "queries": ["all"],
        "control_allowed": False,
        "change_methods": []
    },
    "power": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
    },
    # New parameters
    "channel": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to", "by"],
        "range": (1, 200)
    },
    "volume": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to", "by"],
        "range": (1, 10)
    },
    "bit": {
        "queries": ["all"],
        "control_allowed": True,  # perform BIT
        "change_methods": []
    },
    "config": {
        "queries": ["all"],
        "control_allowed": False,
        "change_methods": []
    },
    "rxonly": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
    },
    "led": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
    },
    "gps": {
        "queries": ["all"],
        "control_allowed": True,
        "change_methods": ["to"]
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
        "modulations": ["8PSK", "QAM16"]
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
        default_state = {
            "frequency_hz": 450e6,
            "bandwidth_hz": 1e6,
            "waveform": "WB",
            "modulation": "QAM16",
            "power_level": "medium",  # low, medium, high
            "battery_percent": 78,
            "battery_voltage": 12.60,
            "members_count": 5,
            "errors": [],
            # New parameters
            "channel": 1,           # Channel 1-200
            "volume": 5,            # Volume 1-10
            "rx_only": False,       # Receive only mode
            "led_on": False,        # LED/Light status
            "gps_on": True,         # GPS status
            # Last used params per waveform (for restoring when switching)
            "last_wf_params": {
                "WB": {
                    "frequency_hz": 450e6,
                    "bandwidth_hz": 1e6,
                    "modulation": "QAM16"
                },
                "NB": {
                    "frequency_hz": 50e6,
                    "bandwidth_hz": 25e3,
                    "modulation": "8PSK"
                }
            }
        }

        if Path(self.json_file).exists():
            with open(self.json_file, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to handle new parameters
                for key, value in default_state.items():
                    if key not in loaded:
                        loaded[key] = value
                return loaded
        else:
            return default_state

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
                         "how much", "what percentage",
                         # Statement patterns that imply queries
                         "there is", "there are", "is there", "are there", "any", "do i have"],
                "CONTROL": ["do", "set", "put", "tune", "change", "adjust", "switch", "modify", "configure",
                           "select", "choose", "increase", "decrease", "raise", "lower", "boost", "reduce",
                           "perform", "run", "execute", "start", "clear", "reset", "reboot",
                           # Volume/channel specific verbs
                           "turn", "up", "down", "min", "max", "minimum", "maximum", "mute", "unmute",
                           "louder", "quieter", "softer", "enable", "disable", "activate", "deactivate",
                           "toggle", "next", "previous", "prev", "go to", "goto",
                           # On/off as control verbs (for "gps on", "led off", etc.)
                           "on", "off",
                           # Mode entry verbs
                           "enter", "exit", "leave"]
            },
            "objects": {
                "frequency": ["frequency", "freq", "frequencies", "free", "fre", "freak", "frequence",
                              "tuning", "tune", "carrier", "hertz", "megahertz"],
                "bw": ["bandwidth", "bw", "rbw", "vbw", "channel width", "band width", "bandwith",
                       "with", "width", "bands", "bandwidths", "ben width", "bad width",
                       "banned with", "band with", "ben with", "bandwitch", "bandwidth"],
                "wf": ["waveform", "wf", "wb", "nb", "wideband", "narrowband", "wide band", "narrow band",
                       "wide", "narrow",
                       "wave form", "wave", "form", "formed", "forms", "phone", "phones",
                       "waveforms", "way form", "way phone",
                       "wafer", "waver", "waivers", "weigh form", "way former", "wave former",
                       "wife form", "wife phone", "white form", "wife former", "way from",
                       "wavephone", "wavefone", "waveform", "wave phone", "whiteform",
                       # Wideband misrecognitions
                       "white been", "white ben", "white bent", "why the band", "why the ben",
                       "why been", "why ben", "wide been", "wide the band", "white the band",
                       "wide man", "white man", "why man", "wide van", "white van",
                       "wide ban", "white ban", "why ban", "wipe band", "wife band",
                       "wine band", "while band", "wild band",
                       # More wideband misrecognitions
                       "weidman", "weirdman", "whitman", "why the bend",
                       "i'd been", "id been", "i been", "i'd band", "id band",
                       "height band", "hide band", "hype band",
                       "white but", "wide but", "why but", "white bed", "wide bed",
                       # Narrowband misrecognitions
                       "narrow been", "narrow ben", "naro been", "naro ben",
                       "narrow the band", "narro band", "narrow man", "narrow van",
                       "narrow ban", "neural band", "neuro band", "arrow band", "nero been",
                       "new opened", "now opened", "never opened", "new open", "now open",
                       "new band", "now band", "new ben", "now ben"],
                "modulation": ["modulation", "mod", "qam", "psk", "8psk", "qam4", "qam16", "qam32", "qam64",
                               "modulations", "module", "modular", "model", "mode", "mods",
                               "modulate", "modulated", "modulating", "module asian", "modulation",
                               "moderation", "moderate", "moderator", "motivation", "modelation",
                               "guam", "qualm", "calm", "gum", "glam", "gram",
                               "operation", "operations", "manipulation", "duration"],
                "errors": ["error", "errors", "fault", "faults", "alarm", "alarms", "warning", "warnings",
                           "problem", "problems", "issue", "issues", "alert", "alerts"],
                "members": ["member", "members", "nodes", "devices", "radios", "connected", "connections",
                            "units", "stations", "clients", "peers", "network"],
                "battery": ["battery", "charge", "voltage", "percent", "percentage", "battery level",
                            "batteries", "bat", "power supply", "energy", "juice",
                            "battery status", "battery state", "battery info"],
                "status": ["radio status", "radio state", "radio info", "radio parameters",
                           "status", "state", "info", "information", "all", "everything", "summary",
                           "report", "parameters", "details",
                           "current", "show all", "tell me all", "full status", "complete"],
                "power": ["power", "power level", "transmit power", "tx power", "output power",
                          "transmission power", "strength", "signal strength", "output", "transmit",
                          "transmission", "tx level", "power output", "wattage", "watts"],
                # New objects
                "channel": ["channel", "channels", "chan", "ch", "channel number",
                            "next channel", "previous channel", "last channel",
                            # Misrecognitions
                            "chanel", "chanell", "shannel", "chennel", "chanal", "channle",
                            "general", "gennel", "kennel", "panel", "tunnel", "funnel",
                            "cannel", "canal", "handle", "chapel"],
                "volume": ["volume", "vol", "loudness", "sound", "sound level", "audio", "audio level",
                           "speaker", "speaker volume", "gain", "mute", "unmute",
                           "louder", "quieter", "softer", "loud", "quiet", "soft",
                           # Misrecognitions
                           "volum", "volumne", "volumn", "valume", "voleume", "vollume",
                           "column", "columns", "volumm", "voulume", "volme", "vollum",
                           "valum", "vilume", "voulum", "volium"],
                "bit": ["bit", "built in test", "built-in test", "self test", "selftest", "diagnostics",
                        "diagnostic", "test", "system test", "radio test", "health check",
                        # Misrecognitions
                        "bit test", "bittest", "b i t", "b.i.t", "bee eye tea",
                        "built and test", "build in test", "building test", "built test",
                        "built in", "builtin", "belt in test", "belt test",
                        "bit check", "beat", "bid", "bet", "but test", "butt test"],
                "config": ["config", "configuration", "configurations", "configure", "settings",
                           "radio settings", "radio configuration", "radio config",
                           "all settings", "current settings", "current config",
                           "audio settings", "sound settings", "my settings",
                           # Misrecognitions
                           "konfig", "configur", "configration", "configuation",
                           "setting", "sittings", "setings"],
                "rxonly": ["receive only", "rx only", "receive mode", "rx mode", "listen only",
                           "listen mode", "receiver only", "reception only", "listening mode",
                           # Misrecognitions
                           "receive only mode", "rx only mode", "are x only",
                           "our x only", "rx on lee", "receive on lee",
                           "receive only on", "receive only off",
                           "silent mode", "stealth mode", "passive mode", "passive",
                           "silence mode", "silence", "silent",
                           # Common STT misrecognitions of "receive"
                           "perceive only", "perceive mode", "perceive",
                           "recieve only", "recieve mode", "recieve",
                           "reseed only", "reseed mode",
                           "received only", "received mode",
                           "precede only", "precede mode"],
                "led": ["led", "l e d", "light", "lights", "indicator", "indicator light",
                        "lamp", "lamps", "flashlight", "torch", "illumination",
                        # Misrecognitions
                        "lead", "lid", "let", "lad", "laid", "led light",
                        "head", "red", "bed", "fed", "dead", "wed", "fled",
                        "lite", "lites", "lightning", "lighting"],
                "gps": ["gps", "g p s", "g.p" ,"global positioning", "positioning system",
                        "location", "navigation", "nav", "satellite", "sat nav",
                        "geo", "geolocation", "coordinates", "position",
                        # Misrecognitions
                        "jeep yes", "jeep s", "jeeps", "geeps", "jps", "gbs",
                        "gp", "g ps", "gpss", "g p", "gee pee ess",
                        "chips", "ships", "tips", "grips", "clips"]
            },
            "prepositions": ["to", "by", "at", "into", "in", "for"],  # "on"/"off" removed to avoid conflicts with LED/GPS commands
            "units": {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9},
            # Direction modifiers for volume/channel
            "direction": {
                "up": ["up", "increase", "raise", "higher", "louder", "boost", "more", "plus", "add", "next"],
                "down": ["down", "decrease", "lower", "reduce", "quieter", "softer", "less", "minus", "subtract", "previous", "prev", "back", "last"],
                "min": ["minimum", "min", "lowest", "mute", "zero", "silent"],
                "max": ["maximum", "max", "highest", "full", "loudest"]
            }
        }

    def _normalize(self, text: str) -> str:
        """Normalize text for parsing."""
        text = re.sub(r'\s+', ' ', re.sub(r'[^\w\s\.\-]', ' ', text.lower())).strip()
        # Remove filler words that don't contribute to command meaning
        text = self._remove_filler_words(text)
        # Fix common STT misrecognitions
        text = self._fix_misrecognitions(text)
        # Convert spoken numbers to digits
        text = self._normalize_numbers(text)
        # Normalize spoken unit names to abbreviations
        text = self._normalize_units(text)
        return text

    def _remove_filler_words(self, text: str) -> str:
        """Remove common filler words that don't affect command meaning."""
        filler_words = [
            r'\bso\b', r'\bum\b', r'\buh\b', r'\bwell\b', r'\blike\b',
            r'\bokay\b', r'\bok\b', r'\bactually\b', r'\bjust\b',
            r'\bmaybe\b', r'\bplease\b', r'\bcan you\b', r'\bcould you\b',
            r'\bi want\b', r'\bi need\b', r'\bi would like\b',
            r'\blet me\b', r'\blets\b', r"\blet's\b", r'\bhow about\b',
        ]
        for filler in filler_words:
            text = re.sub(filler, '', text, flags=re.IGNORECASE)
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _fix_misrecognitions(self, text: str) -> str:
        """Fix common speech-to-text misrecognitions."""
        fixes = [
            # Waveform misrecognitions (extensive list)
            ("way former", "waveform"),
            ("wave former", "waveform"),
            ("wife former", "waveform"),
            ("way form", "waveform"),
            ("wave form", "waveform"),
            ("way phone", "waveform"),
            ("wave phone", "waveform"),
            ("wife form", "waveform"),
            ("wife phone", "waveform"),
            ("white form", "waveform"),
            ("white phone", "waveform"),
            ("way from", "waveform"),
            ("weigh form", "waveform"),
            ("weigh phone", "waveform"),
            ("wafer form", "waveform"),
            ("wafer", "waveform"),
            ("waver form", "waveform"),
            ("waiver form", "waveform"),
            ("wave for", "waveform"),
            ("way for", "waveform"),
            ("wavefone", "waveform"),
            ("wavephone", "waveform"),
            ("whiteform", "waveform"),
            ("wait form", "waveform"),
            ("weight form", "waveform"),
            ("waveforms", "waveform"),
            ("way formed", "waveform"),
            ("wave formed", "waveform"),
            ("way forms", "waveform"),
            ("wave forms", "waveform"),
            # Wideband/narrowband misrecognitions
            ("wide the bend", "wideband"),
            ("wide band", "wideband"),
            ("why band", "wideband"),
            ("white band", "wideband"),
            ("wide bent", "wideband"),
            ("wide ben", "wideband"),
            ("wider band", "wideband"),
            ("wi band", "wideband"),
            # More wideband misrecognitions
            ("white been", "wideband"),
            ("white ben", "wideband"),
            ("white bent", "wideband"),
            ("why the band", "wideband"),
            ("why the ben", "wideband"),
            ("why the bent", "wideband"),
            ("why been", "wideband"),
            ("why ben", "wideband"),
            ("wide been", "wideband"),
            ("wide the band", "wideband"),
            ("wide the ben", "wideband"),
            ("white the band", "wideband"),
            ("white the ben", "wideband"),
            ("y band", "wideband"),
            ("y been", "wideband"),
            ("y ben", "wideband"),
            ("wide man", "wideband"),
            ("white man", "wideband"),
            ("why man", "wideband"),
            ("wide van", "wideband"),
            ("white van", "wideband"),
            ("wide pan", "wideband"),
            ("white pan", "wideband"),
            ("wide ban", "wideband"),
            ("white ban", "wideband"),
            ("why ban", "wideband"),
            ("wide and", "wideband"),
            ("white and", "wideband"),
            ("why and", "wideband"),
            ("wipe band", "wideband"),
            ("wipe ben", "wideband"),
            ("wife band", "wideband"),
            ("wife ben", "wideband"),
            ("wine band", "wideband"),
            ("wine ben", "wideband"),
            ("while band", "wideband"),
            ("while ben", "wideband"),
            ("wild band", "wideband"),
            ("wild ben", "wideband"),
            # More wideband misrecognitions
            ("weidman", "wideband"),
            ("weirdman", "wideband"),
            ("whitman", "wideband"),
            ("why the bend", "wideband"),
            ("wide the bend", "wideband"),
            ("white the bend", "wideband"),
            ("i'd been", "wideband"),
            ("id been", "wideband"),
            ("i been", "wideband"),
            ("i'd ben", "wideband"),
            ("id ben", "wideband"),
            ("i ben", "wideband"),
            ("i'd band", "wideband"),
            ("id band", "wideband"),
            ("i band", "wideband"),
            ("height band", "wideband"),
            ("height ben", "wideband"),
            ("height been", "wideband"),
            ("hide band", "wideband"),
            ("hide ben", "wideband"),
            ("hype band", "wideband"),
            ("hype ben", "wideband"),
            ("white been to", "wideband"),
            ("wide been to", "wideband"),
            ("white but", "wideband"),
            ("wide but", "wideband"),
            ("why but", "wideband"),
            ("white butt", "wideband"),
            ("wide butt", "wideband"),
            ("white bed", "wideband"),
            ("wide bed", "wideband"),
            ("white bud", "wideband"),
            ("wide bud", "wideband"),
            # Narrowband misrecognitions
            ("narrow band", "narrowband"),
            ("naro band", "narrowband"),
            ("narrower band", "narrowband"),
            ("nero band", "narrowband"),
            ("narrow bent", "narrowband"),
            ("narrow been", "narrowband"),
            ("narrow ben", "narrowband"),
            ("naro been", "narrowband"),
            ("naro ben", "narrowband"),
            ("narrow the band", "narrowband"),
            ("narrow the ben", "narrowband"),
            ("narro band", "narrowband"),
            ("narro ben", "narrowband"),
            ("narrow man", "narrowband"),
            ("narrow van", "narrowband"),
            ("narrow pan", "narrowband"),
            ("narrow ban", "narrowband"),
            ("narrow and", "narrowband"),
            ("neural band", "narrowband"),
            ("neural ben", "narrowband"),
            ("neuro band", "narrowband"),
            ("neuro ben", "narrowband"),
            ("narrow wand", "narrowband"),
            ("narrow one", "narrowband"),
            ("arrow band", "narrowband"),
            ("arrow ben", "narrowband"),
            ("nero been", "narrowband"),
            ("nero ben", "narrowband"),
            # More narrowband misrecognitions (Vosk hears "narrowband" as "___opened")
            ("new opened", "narrowband"),
            ("now opened", "narrowband"),
            ("never opened", "narrowband"),
            ("narrow opened", "narrowband"),
            ("naro opened", "narrowband"),
            ("new open", "narrowband"),
            ("now open", "narrowband"),
            ("narrow open", "narrowband"),
            ("new band", "narrowband"),
            ("now band", "narrowband"),
            ("new ben", "narrowband"),
            ("now ben", "narrowband"),
            ("new been", "narrowband"),
            ("now been", "narrowband"),
            ("nero opened", "narrowband"),
            ("narrow pend", "narrowband"),
            ("narrow pen", "narrowband"),
            ("naro pend", "narrowband"),
            # Frequency misrecognitions
            ("for frequency", "frequency"),
            ("free quincy", "frequency"),
            ("frequence", "frequency"),
            ("frequencies", "frequency"),
            ("frequent see", "frequency"),
            ("free quency", "frequency"),
            ("frequenzy", "frequency"),
            ("freak quincy", "frequency"),
            ("freak when see", "frequency"),
            # Bandwidth misrecognitions
            ("band with", "bandwidth"),
            ("banned width", "bandwidth"),
            ("band width", "bandwidth"),
            ("ben width", "bandwidth"),
            ("bad width", "bandwidth"),
            ("bandwith", "bandwidth"),
            ("banned with", "bandwidth"),
            ("ben with", "bandwidth"),
            ("band witch", "bandwidth"),
            ("bandwitch", "bandwidth"),
            ("band wid", "bandwidth"),
            ("bandwidth", "bandwidth"),
            ("van with", "bandwidth"),
            ("ban with", "bandwidth"),
            # Modulation misrecognitions
            ("moderation", "modulation"),
            ("moderation to", "modulation to"),
            ("moderation two", "modulation to"),
            ("moderate", "modulation"),
            ("moderator", "modulation"),
            ("module asian", "modulation"),
            ("module ation", "modulation"),
            ("mod you lation", "modulation"),
            ("modular", "modulation"),
            ("module", "modulation"),
            ("modulations", "modulation"),
            ("modelation", "modulation"),
            ("model asian", "modulation"),
            ("motor asian", "modulation"),
            ("motivation", "modulation"),
            ("operation", "modulation"),
            ("operations", "modulation"),
            ("modulation manipulation", "modulation"),
            ("gay manipulation", "modulation"),
            ("manipulation", "modulation"),
            ("want duration", "modulation"),
            ("one duration", "modulation"),
            ("duration", "modulation"),
            # QAM misrecognitions (Vosk often mishears QAM)
            ("guam", "qam"),
            ("gum", "qam"),
            ("glam", "qam"),
            ("gram", "qam"),
            ("qualm", "qam"),
            ("calm", "qam"),
            ("come", "qam"),
            ("com", "qam"),
            ("comb", "qam"),
            ("kahm", "qam"),
            ("kam", "qam"),
            ("kham", "qam"),
            ("quam", "qam"),
            ("quom", "qam"),
            ("kolm", "qam"),
            ("palm", "qam"),
            ("pam", "qam"),
            ("jam", "qam"),
            ("ham", "qam"),
            ("cam", "qam"),
            ("comma", "qam"),
            ("cram", "qam"),
            ("clam", "qam"),
            ("psalm", "qam"),
            ("kwame", "qam"),
            ("swam", "qam"),
            ("wham", "qam"),
            ("ma'am", "qam"),
            ("mam", "qam"),
            ("q a m", "qam"),
            ("q. a. m.", "qam"),
            ("que am", "qam"),
            ("queue am", "qam"),
            ("tomb", "qam"),
            ("tum", "qam"),
            ("tom", "qam"),
            ("dumb", "qam"),
            ("dome", "qam"),
            ("doom", "qam"),
            ("room", "qam"),
            ("whom", "qam"),
            # "took one" and similar misrecognitions for QAM
            ("took one", "qam"),
            ("took on", "qam"),
            ("to come", "qam"),
            ("to calm", "qam"),
            ("too calm", "qam"),
            ("two com", "qam"),
            # 8PSK misrecognitions (Vosk often mishears 8PSK badly)
            ("a b s k", "8psk"),
            ("a b sk", "8psk"),
            ("ab sk", "8psk"),
            ("absk", "8psk"),
            ("a bsk", "8psk"),
            ("be sk eight", "8psk"),
            ("be sk 8", "8psk"),
            ("besk eight", "8psk"),
            ("besk 8", "8psk"),
            ("b sk eight", "8psk"),
            ("b sk 8", "8psk"),
            ("eight be sk", "8psk"),
            ("8 be sk", "8psk"),
            ("eight besk", "8psk"),
            ("8 besk", "8psk"),
            ("a puppy sk", "8psk"),
            ("puppy sk", "8psk"),
            ("a p sk", "8psk"),
            ("ap sk", "8psk"),
            ("ape sk", "8psk"),
            ("eight p sk", "8psk"),
            ("8 p sk", "8psk"),
            ("ate psk", "8psk"),
            ("ate p sk", "8psk"),
            ("a psk", "8psk"),
            ("apsk", "8psk"),
            ("escape", "8psk"),
            ("he escape", "8psk"),
            ("the escape", "8psk"),
            ("a escape", "8psk"),
            ("hey psk", "8psk"),
            ("hey p sk", "8psk"),
            ("ape s k", "8psk"),
            ("a p s k", "8psk"),
            ("ap s k", "8psk"),
            ("eight bsk", "8psk"),
            ("8 bsk", "8psk"),
            ("eightbsk", "8psk"),
            ("p s k eight", "8psk"),
            ("p s k 8", "8psk"),
            ("psk eight", "8psk"),
            ("psk 8", "8psk"),
            ("ps k eight", "8psk"),
            ("ps k 8", "8psk"),
            # "gay" misrecognitions (Vosk hears PSK as "gay")
            ("eight a gay", "8psk"),
            ("eight be gay", "8psk"),
            ("eight the gay", "8psk"),
            ("8 a gay", "8psk"),
            ("8 be gay", "8psk"),
            ("8 the gay", "8psk"),
            ("a gay", "8psk"),
            ("be gay", "8psk"),
            ("the gay", "8psk"),
            ("eight gay", "8psk"),
            ("8 gay", "8psk"),
            # "k" only misrecognitions
            ("eight k", "8psk"),
            ("8 k", "8psk"),
            ("eightk", "8psk"),
            # "s k" separated misrecognitions
            ("s k eight", "8psk"),
            ("s k 8", "8psk"),
            ("sk eight", "8psk"),
            ("sk 8", "8psk"),
            # Phase shift keying variations
            ("8 phase shift keying", "8psk"),
            ("eight phase shift keying", "8psk"),
            ("phase shift keying 8", "8psk"),
            ("phase shift keying eight", "8psk"),
            ("phase shift keying", "8psk"),
            ("phase shift key", "8psk"),
            ("phase shift", "8psk"),
            ("8 phase shift", "8psk"),
            ("eight phase shift", "8psk"),
            # Vosk misrecognitions of "phase shift keying"
            ("face shift keying", "8psk"),
            ("fase shift keying", "8psk"),
            ("phase shift king", "8psk"),
            ("phase shift keen", "8psk"),
            ("phase shift key in", "8psk"),
            ("phase shift ki", "8psk"),
            ("faze shift keying", "8psk"),
            ("faze shift", "8psk"),
            ("face shift", "8psk"),
            ("phase shipped keying", "8psk"),
            ("phase shipped", "8psk"),
            ("phase ship keying", "8psk"),
            ("phase ship", "8psk"),
            ("phase sift keying", "8psk"),
            ("phase sift", "8psk"),
            ("pays shift keying", "8psk"),
            ("pays shift", "8psk"),
            ("phase chef keying", "8psk"),
            ("phase chef", "8psk"),
            ("phase gift keying", "8psk"),
            ("phase gift", "8psk"),
            ("8 face shift", "8psk"),
            ("eight face shift", "8psk"),
            ("8 phase ship", "8psk"),
            ("eight phase ship", "8psk"),
            # Power level misrecognitions
            ("power level", "power"),
            ("par level", "power"),
            ("pour level", "power"),
            # Unit misrecognitions
            ("killer hurts", "khz"),
            ("killer hertz", "khz"),
            ("kilo hurts", "khz"),
            ("kilo hertz", "khz"),
            ("kilowatts", "khz"),
            ("killa hurts", "khz"),
            ("killa hertz", "khz"),
            ("key low hurts", "khz"),
            ("kilohertz", "khz"),
            ("mega hurts", "mhz"),
            ("mega hertz", "mhz"),
            ("megawatts", "mhz"),
            ("my girls", "mhz"),
            ("megahertz", "mhz"),
            ("make a hurts", "mhz"),
            ("make a hertz", "mhz"),
            ("giga hurts", "ghz"),
            ("giga hertz", "ghz"),
            ("gigahertz", "ghz"),
            ("geiger hurts", "ghz"),
            ("geiger hertz", "ghz"),
            # Number misrecognitions (STT often mishears these)
            ("for", "four"),      # "for forty five" -> "four forty five"
            ("fore", "four"),     # "fore" -> "four"
            ("tree", "three"),    # Military/aviation pronunciation
            ("fife", "five"),     # Military pronunciation
            ("niner", "nine"),    # Aviation pronunciation
            ("have", "half"),     # "have megahertz" -> "half megahertz"
            ("hav", "half"),      # "hav" -> "half"
            ("halve", "half"),    # "halve" -> "half"
        ]
        for wrong, correct in fixes:
            # Use word boundaries to avoid matching inside other words
            # e.g., "y band" should not match inside "my bandwidth"
            pattern = r'\b' + re.escape(wrong) + r'\b'
            text = re.sub(pattern, correct, text)

        # Contextual fix: "two" -> "to" when it appears as preposition before numbers
        # Pattern: [parameter word] two [number word] -> [parameter] to [number]
        # e.g., "frequency two three two three" -> "frequency to three two three"
        param_words = r'(frequency|bandwidth|channel|volume|power|modulation|waveform)'
        number_words = r'(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|\d+)'
        # Replace "two" with "to" when between parameter and number
        pattern = rf'({param_words}\s+)two(\s+{number_words})'
        text = re.sub(pattern, r'\1to\3', text, flags=re.IGNORECASE)

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
        """Convert list of number words to integer.

        Handles both standard English (twenty five = 25) and radio-style
        digit-by-digit pronunciation (two five = 25).
        """
        single_digits = {'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'}

        # Check if this is radio-style digit-by-digit (only single digits 0-9)
        if all(word in single_digits for word in words) and len(words) > 1:
            # Radio-style: concatenate digits (e.g., "two five" = 25)
            return int(''.join(str(ones[word]) for word in words))

        # Check for radio shorthand: "four forty five" = 445 (digit + tens + digit)
        # Pattern: [single digit] [tens word] [single digit]
        if len(words) == 3 and words[0] in single_digits and words[1] in tens and words[2] in single_digits:
            # Extract the tens digit from the tens word (forty -> 4, thirty -> 3)
            tens_digit = tens[words[1]] // 10
            result = int(f"{ones[words[0]]}{tens_digit}{ones[words[2]]}")
            print(f"  [RADIO-SHORTHAND] '{' '.join(words)}' -> {result}")
            return result

        # Check for radio shorthand without trailing digit: "four forty" = 440
        if len(words) == 2 and words[0] in single_digits and words[1] in tens:
            tens_digit = tens[words[1]] // 10
            result = int(f"{ones[words[0]]}{tens_digit}0")
            print(f"  [RADIO-SHORTHAND] '{' '.join(words)}' -> {result}")
            return result

        # Standard English number parsing
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
        # Priority check: if text contains waveform-specific terms, prioritize "wf"
        # This prevents "narrow band" from matching "bw" due to the word "band"
        wf_priority_terms = ["narrow", "wide", "narrowband", "wideband", "nb", "wb"]
        if any(term in text.split() for term in wf_priority_terms):
            # Check if this looks like a waveform command (not bandwidth with a number)
            has_number = bool(re.search(r'\d', text))
            if not has_number:
                # No number, so "narrow band" means waveform, not bandwidth
                for token in self.LEX["objects"]["wf"]:
                    if self._contains_token(text, token):
                        return "wf", token

        # Priority check: if text contains receive/silence/listen terms, prioritize "rxonly"
        # This prevents "receive only mode" or "silence mode" from matching "modulation" due to "mode"
        rxonly_priority_terms = ["receive", "rx only", "listen only", "silence", "silent",
                                  "perceive", "passive", "stealth"]
        if any(term in text for term in rxonly_priority_terms):
            for token in self.LEX["objects"]["rxonly"]:
                if token in text:
                    return "rxonly", token
            # Also check if just the priority term itself should trigger rxonly
            for term in rxonly_priority_terms:
                if term in text:
                    return "rxonly", term

        # Priority check: "config" should take precedence when "settings" is mentioned
        # "radio settings", "audio settings", etc. should match "config", not "status" or single params
        config_priority_terms = ["settings", "configuration", "config", "all settings", "current settings"]
        if any(term in text for term in config_priority_terms):
            for token in self.LEX["objects"]["config"]:
                if token in text:
                    return "config", token
            # If just "settings" is mentioned, default to config
            if "settings" in text:
                return "config", "settings"

        # Priority check: specific objects should take precedence over generic "status"
        # "gps status" should match "gps", not "status"
        # "led status" should match "led", not "status"
        priority_objects = ["gps", "led", "volume", "channel", "bit", "config"]
        for obj in priority_objects:
            for token in self.LEX["objects"].get(obj, []):
                if self._contains_token(text, token):
                    return obj, token

        for obj_type, tokens in self.LEX["objects"].items():
            token = self._find_first(text, tokens)
            if token:
                return obj_type, token
        return None, None

    def _extract_number_unit(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract number with unit from text."""
        # Check for "half" before unit (e.g., "half mhz" = 0.5 mhz)
        half_match = re.search(r'\bhalf\s*(hz|khz|mhz|ghz)\b', text, re.IGNORECASE)
        if half_match:
            return {"value": 0.5, "unit": half_match.group(1).lower()}
        # Check for "point 5" or ".5" before unit (e.g., "point 5 mhz" = 0.5 mhz)
        point_match = re.search(r'\b(?:point\s*)?\.?5\s*(hz|khz|mhz|ghz)\b', text, re.IGNORECASE)
        if point_match and 'point' in text.lower():
            return {"value": 0.5, "unit": point_match.group(1).lower()}
        # Standard number with unit
        match = re.search(r'\b(\d+(?:\.\d+)?)\s*(hz|khz|mhz|ghz)\b', text)
        if match:
            return {"value": float(match.group(1)), "unit": match.group(2)}
        return None

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract number from text."""
        # Check for "half" as 0.5
        if re.search(r'\bhalf\b', text, re.IGNORECASE):
            return 0.5
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

        return False, f"Frequency not valid for {wf}"

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

        return False, f"Bandwidth not valid for {wf}"

    def _validate_modulation(self, mod: str, wf: str) -> Tuple[bool, str]:
        """Validate modulation against WF constraints."""
        if wf not in self.wf_params:
            return True, ""

        allowed_mods = [m.upper() for m in self.wf_params[wf]["modulations"]]
        if not allowed_mods:
            return True, ""

        if mod.upper() in allowed_mods:
            return True, ""

        return False, f"Modulation not valid for {wf}"

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

    def _contains_word(self, text: str, word: str) -> bool:
        """Check if word exists in text as a complete word (with word boundaries)."""
        pattern = r'\b' + re.escape(word) + r'\b'
        return bool(re.search(pattern, text))

    def _detect_wf_value(self, text: str) -> Optional[str]:
        """Detect WF value (NB/WB) from text."""
        normalized = self._normalize(text)
        # Narrowband detection (check first as it's more specific)
        nb_words = [
            "nb", "narrow", "narrowband", "narrow band", "naro", "nero",
            "narrower", "narrow bent", "narrow ben", "narrow been",
            "naro been", "naro ben", "narrow the band", "narrow the ben",
            "narro band", "narro ben", "narrow man", "narrow van",
            "narrow pan", "narrow ban", "narrow and", "neural band",
            "neural ben", "neuro band", "neuro ben", "narrow wand",
            "narrow one", "arrow band", "arrow ben", "nero been", "nero ben",
            # "opened" misrecognitions
            "new opened", "now opened", "never opened", "narrow opened",
            "naro opened", "new open", "now open", "narrow open",
            "new band", "now band", "new ben", "now ben",
            "new been", "now been", "nero opened",
            "narrow pend", "narrow pen", "naro pend"
        ]
        if any(self._contains_word(normalized, w) for w in nb_words):
            return "NB"
        # Wideband detection
        wb_words = [
            "wb", "wide", "wideband", "wide band", "wider", "white band",
            "why band", "wi band", "wide bent", "wide ben", "white ben",
            "white been", "white bent", "why the band", "why the ben",
            "why the bent", "why been", "why ben", "wide been",
            "wide the band", "wide the ben", "white the band", "white the ben",
            "y band", "y been", "y ben", "wide man", "white man", "why man",
            "wide van", "white van", "wide pan", "white pan",
            "wide ban", "white ban", "why ban", "wide and", "white and",
            "why and", "wipe band", "wipe ben", "wife band", "wife ben",
            "wine band", "wine ben", "while band", "while ben",
            "wild band", "wild ben",
            # More variations
            "weidman", "weirdman", "whitman",
            "why the bend", "wide the bend", "white the bend",
            "i'd been", "id been", "i been", "i'd ben", "id ben", "i ben",
            "i'd band", "id band", "i band",
            "height band", "height ben", "height been",
            "hide band", "hide ben", "hype band", "hype ben",
            # "but/butt/bed/bud" misrecognitions
            "white but", "wide but", "why but",
            "white butt", "wide butt",
            "white bed", "wide bed",
            "white bud", "wide bud"
        ]
        if any(self._contains_word(normalized, w) for w in wb_words):
            return "WB"
        return None

    def _detect_modulation_value(self, text: str) -> Optional[str]:
        """Detect modulation value from text."""
        normalized = self._normalize(text)

        # Remove spaces for easier matching
        no_spaces = normalized.replace(" ", "")

        # Check for 8PSK variations (extensive list due to Vosk misrecognitions)
        psk_patterns = [
            "8psk", "psk8", "8 psk", "psk 8", "eight psk", "psk eight",
            "8 p s k", "p s k 8", "eightpsk", "pskeight",
            # Vosk misrecognitions
            "a b s k", "a b sk", "ab sk", "absk", "a bsk",
            "be sk eight", "be sk 8", "besk eight", "besk 8",
            "b sk eight", "b sk 8", "eight be sk", "8 be sk",
            "eight besk", "8 besk", "a puppy sk", "puppy sk",
            "a p sk", "ap sk", "ape sk", "eight p sk", "8 p sk",
            "ate psk", "ate p sk", "a psk", "apsk",
            "escape", "he escape", "the escape", "a escape",
            "hey psk", "hey p sk", "ape s k", "a p s k", "ap s k",
            "eight bsk", "8 bsk", "eightbsk",
            "p s k eight", "p s k 8", "psk eight", "psk 8",
            "ps k eight", "ps k 8",
            # More variations
            "sk eight", "sk 8", "s k eight", "s k 8",
            "bpsk", "b psk", "bee psk", "bee sk",
            "eight p", "8 p", "eightp", "8p",
            # "gay" misrecognitions (Vosk hears PSK as "gay")
            "eight a gay", "eight be gay", "eight the gay",
            "8 a gay", "8 be gay", "8 the gay",
            "a gay", "be gay", "the gay",
            "eight gay", "8 gay",
            # "k" only misrecognitions
            "eight k", "8 k", "eightk",
            # Phase shift keying variations
            "8 phase shift keying", "eight phase shift keying",
            "phase shift keying 8", "phase shift keying eight",
            "phase shift keying", "phase shift key", "phase shift",
            "8 phase shift", "eight phase shift",
            # Vosk misrecognitions of phase shift keying
            "face shift keying", "fase shift keying",
            "phase shift king", "phase shift keen", "phase shift key in",
            "faze shift keying", "faze shift", "face shift",
            "phase shipped keying", "phase shipped",
            "phase ship keying", "phase ship",
            "phase sift keying", "phase sift",
            "pays shift keying", "pays shift",
            "phase chef keying", "phase chef",
            "phase gift keying", "phase gift",
            "8 face shift", "eight face shift",
            "8 phase ship", "eight phase ship"
        ]
        # Check no-space version
        psk_nospace = ["8psk", "psk8", "absk", "apsk", "bsk8", "8bsk", "eightpsk", "pskeight", "8k", "eightk", "8gay", "eightgay", "phaseshift", "phaseshiftkeying"]
        if any(p in no_spaces for p in psk_nospace) or \
           any(p in normalized for p in psk_patterns):
            return "8PSK"

        # QAM-like words that Vosk might recognize instead of "qam"
        qam_aliases = ["qam", "guam", "gum", "glam", "gram", "qualm", "calm", "come",
                       "com", "comb", "kahm", "kam", "kham", "quam", "quom", "kolm",
                       "palm", "pam", "jam", "ham", "cam", "comma", "cram", "clam",
                       "psalm", "kwame", "swam", "wham", "mam", "que", "queue", "cue",
                       "q", "tomb", "tum", "tom", "dumb", "dome", "doom", "room", "whom",
                       "gam", "gams", "game", "tram", "scam", "spam", "slam", "sham"]

        # Check for QAM variations (order matters - check larger numbers first)
        qam_values = [64, 32, 16, 4]
        for val in qam_values:
            # Check with all QAM aliases
            for alias in qam_aliases:
                # Patterns: qam64, 64qam, qam 64, 64 qam, etc.
                if f"{alias}{val}" in no_spaces or f"{val}{alias}" in no_spaces:
                    return f"QAM{val}"
                if f"{alias} {val}" in normalized or f"{val} {alias}" in normalized:
                    return f"QAM{val}"
                if f"{alias}{val}" in normalized or f"{val}{alias}" in normalized:
                    return f"QAM{val}"

        # Also check for spoken numbers with QAM aliases
        spoken_numbers = {
            "four": 4, "for": 4, "fore": 4,
            "sixteen": 16, "six teen": 16, "sixteenth": 16,
            "thirty two": 32, "thirtytwo": 32, "thirty 2": 32, "32": 32,
            "sixty four": 64, "sixtyfour": 64, "sixty 4": 64, "64": 64
        }
        for spoken, val in spoken_numbers.items():
            for alias in qam_aliases:
                if f"{alias} {spoken}" in normalized or f"{spoken} {alias}" in normalized:
                    return f"QAM{val}"

        return None

    def _detect_power_level(self, text: str) -> Optional[str]:
        """Detect power level (low, medium, high) from text."""
        normalized = self._normalize(text)
        if any(w in normalized for w in ["low", "lo", "minimum", "min", "lowest"]):
            return "low"
        if any(w in normalized for w in ["medium", "med", "mid", "middle", "normal", "standard"]):
            return "medium"
        if any(w in normalized for w in ["high", "hi", "maximum", "max", "highest", "full"]):
            return "high"
        return None

    def _detect_on_off(self, text: str) -> Optional[bool]:
        """Detect on/off state from text. Returns True for on, False for off, None if unclear."""
        normalized = self._normalize(text)
        on_words = ["on", "enable", "enabled", "activate", "activated", "start", "started",
                    "turn on", "switch on", "open", "yes", "true", "active"]
        off_words = ["off", "disable", "disabled", "deactivate", "deactivated", "stop", "stopped",
                     "turn off", "switch off", "close", "no", "false", "inactive"]

        # Check for off first (more specific patterns)
        if any(w in normalized for w in off_words):
            return False
        if any(w in normalized for w in on_words):
            return True
        return None

    def _detect_direction(self, text: str) -> Optional[str]:
        """Detect direction modifier (up/down/min/max) from text."""
        normalized = self._normalize(text)

        # Special case: "unmute" should be treated as "up" not "min"
        if "unmute" in normalized:
            return "up"

        # Check min/max first (more specific)
        for word in self.LEX["direction"]["min"]:
            if word in normalized:
                return "min"
        for word in self.LEX["direction"]["max"]:
            if word in normalized:
                return "max"
        for word in self.LEX["direction"]["up"]:
            if word in normalized:
                return "up"
        for word in self.LEX["direction"]["down"]:
            if word in normalized:
                return "down"
        return None

    def _apply_direction(self, current_val: int, direction: str, min_val: int, max_val: int, step: int = 1) -> int:
        """Apply direction change to a value within bounds."""
        if direction == "up":
            return min(current_val + step, max_val)
        elif direction == "down":
            return max(current_val - step, min_val)
        elif direction == "min":
            return min_val
        elif direction == "max":
            return max_val
        return current_val

    def _smart_infer_command(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fuzzy command inference - understand intent even from partial/garbled speech.
        Examples:
          "bla bla frequency to 400 mhz" -> CONTROL, frequency, to
          "change bla bla to narrowband" -> CONTROL, wf, to
          "narrowband" -> CONTROL, wf, to
          "400 megahertz" -> CONTROL, frequency, to
        Returns (verb_type, obj_type, prep)
        """
        normalized = self._normalize(text)

        # First try normal detection
        verb_type, _ = self._detect_verb(normalized)
        obj_type, _ = self._detect_object(normalized)
        prep = self._find_first(normalized, self.LEX["prepositions"])

        # Extract potential values
        num_unit = self._extract_number_unit(normalized)
        num = self._extract_number(normalized)
        wf_val = self._detect_wf_value(text)  # Use original text for WF detection
        mod_val = self._detect_modulation_value(normalized)

        # --- Infer object from values if not detected ---

        # If we see narrowband/wideband, it's a WF command
        if wf_val and not obj_type:
            obj_type = "wf"
            print(f"  [INFER] Detected WF value '{wf_val}' -> object=wf")

        # If we see modulation value (qam16, 8psk, etc), it's modulation
        if mod_val and not obj_type:
            obj_type = "modulation"
            print(f"  [INFER] Detected modulation '{mod_val}' -> object=modulation")

        # If we have MHz/GHz number, likely frequency
        if num_unit and num_unit.get("unit") in ["mhz", "ghz"] and not obj_type:
            obj_type = "frequency"
            print(f"  [INFER] Detected {num_unit['value']} {num_unit['unit']} -> object=frequency")

        # If we have kHz number, likely bandwidth
        if num_unit and num_unit.get("unit") == "khz" and not obj_type:
            obj_type = "bw"
            print(f"  [INFER] Detected {num_unit['value']} khz -> object=bw")

        # --- Infer verb if not detected ---

        # If we have an object and a value/prep, assume CONTROL
        if obj_type and not verb_type:
            has_value = num_unit or num or wf_val or mod_val
            if has_value or prep:
                verb_type = "CONTROL"
                print(f"  [INFER] Have object '{obj_type}' + value -> verb=CONTROL")

        # If we have object but no verb and no value, might be QUERY
        if obj_type and not verb_type:
            # Check for query-like words
            query_hints = ["what", "how", "current", "status", "level"]
            if any(hint in normalized for hint in query_hints):
                verb_type = "QUERY"
                print(f"  [INFER] Query hint detected -> verb=QUERY")

        # For toggle-able objects (rxonly, led, gps), just saying the object name
        # implies a CONTROL command to toggle/enable it
        # e.g., "silent mode", "perceive only" -> enable rxonly
        if obj_type in ["rxonly", "led", "gps"] and not verb_type:
            verb_type = "CONTROL"
            print(f"  [INFER] Toggle object '{obj_type}' -> verb=CONTROL (toggle)")

        # --- Default preposition ---
        if verb_type == "CONTROL" and not prep:
            prep = "to"
            print(f"  [INFER] No preposition -> default prep='to'")

        return verb_type, obj_type, prep

    def get_command_type(self, user_input: str) -> str:
        """Determine if command is QUERY, CONTROL, or UNKNOWN. Uses fuzzy inference."""
        verb_type, obj_type, _ = self._smart_infer_command(user_input)
        return verb_type if verb_type else "UNKNOWN"

    def is_clarification(self, response: str) -> bool:
        """Check if response is a clarification request."""
        return response.startswith("CLARIFY:")

    def get_clarification_message(self, response: str) -> str:
        """Extract the spoken message from a clarification response."""
        if self.is_clarification(response):
            # Format: "CLARIFY:param:message"
            parts = response.split(":", 2)
            if len(parts) >= 3:
                return parts[2]
        return response

    def get_clarification_param(self, response: str) -> Optional[str]:
        """Extract the parameter being clarified."""
        if self.is_clarification(response):
            parts = response.split(":", 2)
            if len(parts) >= 2:
                return parts[1]
        return None

    def get_normalized(self, user_input: str) -> str:
        """Return the normalized version of the command (numbers and units converted)."""
        return self._normalize(user_input)

    def get_command_summary(self, user_input: str) -> str:
        """Return a clean summary of the command for logging (e.g., 'frequency: 450 MHz')."""
        normalized = self._normalize(user_input)

        # Use smart inference
        verb_type, obj_type, _ = self._smart_infer_command(user_input)

        if not obj_type:
            return "unknown command"

        # For QUERY commands, return just the parameter name
        if verb_type == "QUERY":
            query_names = {
                "frequency": "frequency", "bw": "bandwidth", "wf": "waveform",
                "modulation": "modulation", "battery": "battery", "members": "members",
                "errors": "errors", "status": "status", "power": "power",
                "channel": "channel", "volume": "volume", "config": "configuration",
                "bit": "BIT status", "rxonly": "receive only mode", "led": "LED",
                "gps": "GPS"
            }
            return query_names.get(obj_type, obj_type)

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
            elif obj_type == "power":
                power = self._detect_power_level(normalized)
                return f"power: {power}" if power else "power: change"
            elif obj_type == "errors":
                return "errors: clear"
            elif obj_type == "channel":
                direction = self._detect_direction(normalized)
                # Priority: min/max keywords override numbers
                if direction in ["min", "max"]:
                    return f"channel: {'minimum' if direction == 'min' else 'maximum'}"
                elif direction:
                    return f"channel: {direction}"
                elif num is not None:
                    return f"channel: {int(num)}"
                return "channel: change"
            elif obj_type == "volume":
                direction = self._detect_direction(normalized)
                # Priority: min/max keywords override numbers
                if direction in ["min", "max"]:
                    return f"volume: {'minimum' if direction == 'min' else 'maximum'}"
                elif direction:
                    return f"volume: {direction}"
                elif num is not None:
                    return f"volume: {int(num)}"
                return "volume: change"
            elif obj_type == "bit":
                return "BIT: perform"
            elif obj_type == "rxonly":
                on_off = self._detect_on_off(normalized)
                if on_off is not None:
                    return f"receive only: {'on' if on_off else 'off'}"
                return "receive only: toggle"
            elif obj_type == "led":
                on_off = self._detect_on_off(normalized)
                if on_off is not None:
                    return f"LED: {'on' if on_off else 'off'}"
                return "LED: toggle"
            elif obj_type == "gps":
                on_off = self._detect_on_off(normalized)
                if on_off is not None:
                    return f"GPS: {'on' if on_off else 'off'}"
                return "GPS: toggle"
            else:
                return f"{obj_type}: control"

        return f"{obj_type}: unknown"

    def process_command(self, user_input: str) -> str:
        """Process user command end-to-end. Uses fuzzy inference for partial commands."""
        normalized = self._normalize(user_input)

        # Use smart inference to understand partial/garbled commands
        verb_type, obj_type, prep = self._smart_infer_command(user_input)

        if not verb_type:
            return "Not understood"

        if not obj_type:
            if verb_type == "CONTROL":
                # User wants to change something but didn't specify what
                return "CLARIFY:parameter:Change what?"
            return "Not understood"

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
            elif obj_type == "power":
                power_level = self.radio_state.get('power_level', 'medium')
                return f"Power level: {power_level}"
            elif obj_type == "status":
                # Return radio status: battery percentage and errors
                battery_pct = self.radio_state['battery_percent']
                errors = self.radio_state.get('errors', [])
                error_count = len(errors)

                status_msg = f"Radio status: Battery {battery_pct}%, {error_count} errors"
                if error_count > 0:
                    status_msg += f": {', '.join(errors)}"
                return status_msg

            # New query handlers
            elif obj_type == "channel":
                return f"Channel: {self.radio_state.get('channel', 1)}"

            elif obj_type == "volume":
                return f"Volume: {self.radio_state.get('volume', 5)}"

            elif obj_type == "config":
                # Return all radio configuration settings
                state = self.radio_state
                config_lines = [
                    f"Frequency: {self._hz_str(state['frequency_hz'])}",
                    f"Bandwidth: {self._hz_str(state['bandwidth_hz'])}",
                    f"Waveform: {state['waveform']}",
                    f"Modulation: {state['modulation']}",
                    f"Channel: {state.get('channel', 1)}",
                    f"Volume: {state.get('volume', 5)}",
                    f"Power: {state.get('power_level', 'medium')}",
                    f"Receive only: {'on' if state.get('rx_only', False) else 'off'}",
                    f"LED: {'on' if state.get('led_on', False) else 'off'}",
                    f"GPS: {'on' if state.get('gps_on', True) else 'off'}"
                ]
                return "Radio configuration: " + ", ".join(config_lines)

            elif obj_type == "bit":
                # Query BIT status - return last BIT results
                errors = self.radio_state.get('errors', [])
                error_count = len(errors)
                if error_count == 0:
                    return "BIT status: No errors detected"
                return f"BIT status: {error_count} errors: {', '.join(errors)}"

            elif obj_type == "rxonly":
                rx_only = self.radio_state.get('rx_only', False)
                return f"Receive only mode: {'on' if rx_only else 'off'}"

            elif obj_type == "led":
                led_on = self.radio_state.get('led_on', False)
                return f"LED: {'on' if led_on else 'off'}"

            elif obj_type == "gps":
                gps_on = self.radio_state.get('gps_on', True)
                return f"GPS: {'on' if gps_on else 'off'}"

        # CONTROL commands
        elif verb_type == "CONTROL":
            if not self._is_control_allowed(obj_type):
                return f"Control not allowed for {obj_type}"

            # prep already inferred, but check change methods
            change_methods = self._get_change_methods(obj_type)

            # Skip preposition check for objects that don't use change methods
            # (like bit, led, gps, rxonly which use on/off or perform)
            if prep and change_methods and prep not in change_methods:
                # Don't fail if prep is "on" or "off" for toggle-type objects
                if prep not in ["on", "off"] or obj_type not in ["led", "gps", "rxonly"]:
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
                    # Value not understood - ask for clarification
                    return "CLARIFY:frequency:What frequency?"

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
                    # Value not understood - ask for clarification
                    return "CLARIFY:bw:What bandwidth?"

            # Waveform control
            elif obj_type == "wf":
                new_wf = self._detect_wf_value(normalized)
                if not new_wf:
                    # Value not understood - ask for clarification
                    return "CLARIFY:wf:Narrowband or wideband?"

                if new_wf == current_wf:
                    return f"Already in {new_wf} mode"

                old_wf = self.radio_state["waveform"]

                # Initialize last_wf_params if not present (for backward compatibility)
                if "last_wf_params" not in self.radio_state:
                    self.radio_state["last_wf_params"] = {
                        "WB": {"frequency_hz": 450e6, "bandwidth_hz": 1e6, "modulation": "QAM16"},
                        "NB": {"frequency_hz": 50e6, "bandwidth_hz": 25e3, "modulation": "8PSK"}
                    }

                # Save current params to the old waveform's storage BEFORE switching
                self.radio_state["last_wf_params"][old_wf] = {
                    "frequency_hz": self.radio_state["frequency_hz"],
                    "bandwidth_hz": self.radio_state["bandwidth_hz"],
                    "modulation": self.radio_state["modulation"]
                }

                # Get saved params for the new waveform
                new_wf_params = self.radio_state["last_wf_params"].get(new_wf, {})
                wf_config = self.wf_params[new_wf]

                # Track what we're changing
                adjustment_msgs = []
                old_freq = self.radio_state["frequency_hz"]
                old_bw = self.radio_state["bandwidth_hz"]
                old_mod = self.radio_state["modulation"]

                # Apply WF change
                self.radio_state["waveform"] = new_wf

                # Restore frequency (use saved if valid, otherwise use default)
                new_freq = new_wf_params.get("frequency_hz")
                if new_freq:
                    valid_freq, _ = self._validate_frequency(new_freq, new_wf)
                    if valid_freq:
                        self.radio_state["frequency_hz"] = new_freq
                    else:
                        # Use middle of first valid range as default
                        low, high = wf_config["frequency_ranges"][0]
                        self.radio_state["frequency_hz"] = (low + high) / 2
                else:
                    low, high = wf_config["frequency_ranges"][0]
                    self.radio_state["frequency_hz"] = (low + high) / 2

                if self.radio_state["frequency_hz"] != old_freq:
                    adjustment_msgs.append(f"Frequency: {self._hz_str(old_freq)} to {self._hz_str(self.radio_state['frequency_hz'])}")

                # Restore bandwidth (use saved if valid, otherwise use default)
                new_bw = new_wf_params.get("bandwidth_hz")
                if new_bw:
                    valid_bw, _ = self._validate_bandwidth(new_bw, new_wf)
                    if valid_bw:
                        self.radio_state["bandwidth_hz"] = new_bw
                    else:
                        self.radio_state["bandwidth_hz"] = wf_config["bw"][0]
                else:
                    self.radio_state["bandwidth_hz"] = wf_config["bw"][0]

                if self.radio_state["bandwidth_hz"] != old_bw:
                    adjustment_msgs.append(f"Bandwidth: {self._hz_str(old_bw)} to {self._hz_str(self.radio_state['bandwidth_hz'])}")

                # Restore modulation (use saved if valid, otherwise use default)
                new_mod = new_wf_params.get("modulation")
                if new_mod:
                    valid_mod, _ = self._validate_modulation(new_mod, new_wf)
                    if valid_mod:
                        self.radio_state["modulation"] = new_mod
                    else:
                        self.radio_state["modulation"] = wf_config["modulations"][0]
                else:
                    self.radio_state["modulation"] = wf_config["modulations"][0]

                if self.radio_state["modulation"] != old_mod:
                    adjustment_msgs.append(f"Modulation: {old_mod} to {self.radio_state['modulation']}")

                self._save_state()

                return f"Waveform changed to {new_wf}"

            # Modulation control
            elif obj_type == "modulation":
                new_mod = self._detect_modulation_value(normalized)
                if not new_mod:
                    # Value not understood - ask for clarification
                    return "CLARIFY:modulation:What modulation?"

                valid, msg = self._validate_modulation(new_mod, current_wf)
                if not valid:
                    return msg

                self.radio_state["modulation"] = new_mod
                self._save_state()
                return f"Modulation set to {new_mod}"

            # Power level control
            elif obj_type == "power":
                new_power = self._detect_power_level(normalized)
                if not new_power:
                    # Value not understood - ask for clarification
                    return "CLARIFY:power:Low, medium, or high?"

                current_power = self.radio_state.get('power_level', 'medium')
                if new_power == current_power:
                    return f"Power level is already {new_power}"

                self.radio_state["power_level"] = new_power
                self._save_state()
                return f"Power level set to {new_power}"

            # Errors - only clear allowed
            elif obj_type == "errors":
                if any(w in normalized for w in ["clear", "reset"]):
                    self.radio_state["errors"] = []
                    self._save_state()
                    return "Errors cleared"
                return "Only 'clear errors' is allowed"

            # Channel control (1-200)
            elif obj_type == "channel":
                current_channel = self.radio_state.get('channel', 1)
                direction = self._detect_direction(normalized)

                # Priority: min/max direction keywords override numbers
                # e.g., "channel 50 minimum" should set to 1, not 50
                if direction in ["min", "max"]:
                    new_channel = self._apply_direction(current_channel, direction, 1, 200)
                    if new_channel == current_channel:
                        return f"Channel is already at {'minimum' if direction == 'min' else 'maximum'} ({current_channel})"
                    self.radio_state["channel"] = new_channel
                    self._save_state()
                    if direction == "min":
                        return f"Channel set to minimum ({new_channel})"
                    else:
                        return f"Channel set to maximum ({new_channel})"
                elif direction:
                    # Direction-based change (up/down)
                    new_channel = self._apply_direction(current_channel, direction, 1, 200)
                    if new_channel == current_channel:
                        limit = "maximum" if direction == "up" else "minimum"
                        return f"Channel is already at {limit} ({current_channel})"
                    self.radio_state["channel"] = new_channel
                    self._save_state()
                    return f"Channel {'increased' if direction == 'up' else 'decreased'} to {new_channel}"
                elif num is not None:
                    # Absolute value
                    new_channel = int(num)
                    if new_channel < 1 or new_channel > 200:
                        # Check for STT stutter - repeated leading digit (e.g., "to two five" heard as "two two five" = 225)
                        # Auto-correct by removing duplicate first digit
                        num_str = str(new_channel)
                        if len(num_str) >= 2 and num_str[0] == num_str[1]:
                            suggested = int(num_str[1:])
                            if 1 <= suggested <= 200:
                                # Auto-correct the stutter
                                new_channel = suggested
                                print(f"  [AUTO-CORRECT] Detected STT stutter {num_str} -> {suggested}")
                    if new_channel < 1 or new_channel > 200:
                        return "Channel 1 to 200 only"
                    if new_channel == current_channel:
                        return f"Channel is already at {current_channel}"
                    self.radio_state["channel"] = new_channel
                    self._save_state()
                    return f"Channel set to {new_channel}"
                elif prep == "by" and num is not None:
                    # Delta change
                    delta = int(num)
                    if any(w in normalized for w in ["decrease", "lower", "reduce", "down"]):
                        delta = -delta
                    new_channel = max(1, min(200, current_channel + delta))
                    if new_channel == current_channel:
                        return f"Channel is already at {current_channel}"
                    self.radio_state["channel"] = new_channel
                    self._save_state()
                    return f"Channel changed to {new_channel}"
                else:
                    return "CLARIFY:channel:What channel?"

            # Volume control (1-10)
            elif obj_type == "volume":
                current_volume = self.radio_state.get('volume', 5)
                direction = self._detect_direction(normalized)

                # Priority: min/max direction keywords override numbers
                # e.g., "volume two minimum" should set to minimum, not 2
                if direction in ["min", "max"]:
                    new_volume = self._apply_direction(current_volume, direction, 1, 10)
                    if new_volume == current_volume:
                        return f"Volume is already at {'minimum' if direction == 'min' else 'maximum'} ({current_volume})"
                    self.radio_state["volume"] = new_volume
                    self._save_state()
                    if direction == "min":
                        return f"Volume set to minimum ({new_volume})"
                    else:
                        return f"Volume set to maximum ({new_volume})"
                elif direction:
                    # Direction-based change (up/down)
                    new_volume = self._apply_direction(current_volume, direction, 1, 10)
                    if new_volume == current_volume:
                        limit = "maximum" if direction == "up" else "minimum"
                        return f"Volume is already at {limit} ({current_volume})"
                    self.radio_state["volume"] = new_volume
                    self._save_state()
                    return f"Volume {'increased' if direction == 'up' else 'decreased'} to {new_volume}"
                elif num is not None:
                    # Absolute value
                    new_volume = int(num)
                    if new_volume < 1 or new_volume > 10:
                        # Check for STT stutter - repeated leading digit (e.g., "to five" heard as "two five" = 25)
                        # Auto-correct by removing duplicate first digit
                        num_str = str(new_volume)
                        if len(num_str) >= 2 and num_str[0] == num_str[1]:
                            suggested = int(num_str[1:])
                            if 1 <= suggested <= 10:
                                # Auto-correct the stutter
                                new_volume = suggested
                                print(f"  [AUTO-CORRECT] Detected STT stutter {num_str} -> {suggested}")
                    if new_volume < 1 or new_volume > 10:
                        return "Volume 1 to 10 only"
                    if new_volume == current_volume:
                        return f"Volume is already at {current_volume}"
                    self.radio_state["volume"] = new_volume
                    self._save_state()
                    return f"Volume set to {new_volume}"
                elif prep == "by" and num is not None:
                    # Delta change
                    delta = int(num)
                    if any(w in normalized for w in ["decrease", "lower", "reduce", "down"]):
                        delta = -delta
                    new_volume = max(1, min(10, current_volume + delta))
                    if new_volume == current_volume:
                        return f"Volume is already at {current_volume}"
                    self.radio_state["volume"] = new_volume
                    self._save_state()
                    return f"Volume changed to {new_volume}"
                else:
                    return "CLARIFY:volume:What volume?"

            # BIT - Perform Built-In Test
            elif obj_type == "bit":
                # Perform BIT - check for errors and return results
                errors = self.radio_state.get('errors', [])
                error_count = len(errors)
                if error_count == 0:
                    return "Performing BIT. BIT results are: All tests passed, 0 errors detected"
                else:
                    error_list = ', '.join(errors)
                    return f"Performing BIT. BIT results are: {error_count} errors detected: {error_list}"

            # Receive-only mode control
            elif obj_type == "rxonly":
                current = self.radio_state.get('rx_only', False)
                on_off = self._detect_on_off(normalized)
                # Handle "enter" as on, "exit/leave" as off
                if on_off is None:
                    if any(w in normalized for w in ["enter", "activate", "enable"]):
                        on_off = True
                    elif any(w in normalized for w in ["exit", "leave", "deactivate", "disable"]):
                        on_off = False
                    else:
                        # Toggle if no explicit on/off
                        on_off = not current
                if on_off == current:
                    return f"Receive only mode is already {'enabled' if current else 'disabled'}"
                self.radio_state["rx_only"] = on_off
                self._save_state()
                return f"Receive only mode {'enabled' if on_off else 'disabled'}"

            # LED/Light control
            elif obj_type == "led":
                current = self.radio_state.get('led_on', False)
                on_off = self._detect_on_off(normalized)
                if on_off is None:
                    # Toggle if no explicit on/off
                    on_off = not current
                if on_off == current:
                    return f"LED is already {'on' if current else 'off'}"
                self.radio_state["led_on"] = on_off
                self._save_state()
                return f"LED turned {'on' if on_off else 'off'}"

            # GPS control
            elif obj_type == "gps":
                current = self.radio_state.get('gps_on', True)
                on_off = self._detect_on_off(normalized)
                if on_off is None:
                    # Toggle if no explicit on/off
                    on_off = not current
                if on_off == current:
                    return f"GPS is already {'on' if current else 'off'}"
                self.radio_state["gps_on"] = on_off
                self._save_state()
                return f"GPS turned {'on' if on_off else 'off'}"

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
        print(f"Channel: {self.radio_state.get('channel', 1)}")
        print(f"Volume: {self.radio_state.get('volume', 5)}")
        print(f"Power Level: {self.radio_state.get('power_level', 'medium')}")
        print(f"Receive Only: {'ON' if self.radio_state.get('rx_only', False) else 'OFF'}")
        print(f"LED: {'ON' if self.radio_state.get('led_on', False) else 'OFF'}")
        print(f"GPS: {'ON' if self.radio_state.get('gps_on', True) else 'OFF'}")
        print(f"Battery: {self.radio_state['battery_percent']}% ({self.radio_state['battery_voltage']:.2f} V)")
        print(f"Members: {self.radio_state.get('members_count', 0)}")
        errors = self.radio_state.get('errors', [])
        print(f"Errors: {', '.join(errors) if errors else 'NONE'}")
        print("=" * 20 + "\n")


def interactive_mode():
    """Run interactive command mode with clarification handling."""
    parser = RadioCommandParser()
    pending_clarification = None  # Track if we're waiting for clarification

    print("=" * 60)
    print("RADIO COMMAND PARSER (with fuzzy inference)")
    print("=" * 60)
    parser.print_state()

    print("Examples:")
    print("  - get frequency")
    print("  - set frequency to 450 mhz")
    print("  - 400 megahertz          (infers: set frequency)")
    print("  - narrowband             (infers: set waveform)")
    print("  - change frequency to... (asks for clarification)")
    print("\nType 'state' to see current state, 'quit' to exit\n")

    while True:
        try:
            if pending_clarification:
                user_input = input("Clarify> ").strip()
            else:
                user_input = input("Command> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if user_input.lower() == 'state':
                parser.print_state()
                continue

            # Handle clarification response
            if pending_clarification:
                if user_input.lower() in ['no', 'nope', 'cancel', 'nevermind']:
                    print("-> Cancelled.\n")
                    pending_clarification = None
                    continue
                else:
                    # Try to process as value for the pending parameter
                    # Construct a proper command with the clarified value
                    param = pending_clarification
                    constructed_cmd = f"set {param} to {user_input}"
                    print(f"  [Interpreting as: {constructed_cmd}]")
                    response = parser.process_command(constructed_cmd)
                    pending_clarification = None

                    if parser.is_clarification(response):
                        print(f"-> {parser.get_clarification_message(response)}")
                        pending_clarification = parser.get_clarification_param(response)
                    else:
                        print(f"-> {response}\n")
                    continue

            # Normal command processing
            response = parser.process_command(user_input)

            # Check if clarification needed
            if parser.is_clarification(response):
                print(f"-> {parser.get_clarification_message(response)}")
                pending_clarification = parser.get_clarification_param(response)
            else:
                print(f"-> {response}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    interactive_mode()
