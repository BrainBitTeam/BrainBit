"""
Radio command knowledge base.

Defines all supported commands, their capabilities, and valid ranges.
This information is used to constrain the LLM to only suggest valid commands.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CommandType(Enum):
    """Type of command operation."""
    QUERY = "query"
    CONTROL = "control"


@dataclass(frozen=True)
class ParameterInfo:
    """
    Information about a controllable radio parameter.

    Attributes:
        name: Parameter identifier.
        display_name: Human-readable name.
        queryable: Whether the parameter can be queried.
        controllable: Whether the parameter can be modified.
        value_type: Type of value (numeric, enum, boolean).
        valid_values: For enum types, list of valid values.
        valid_range: For numeric types, (min, max) tuple.
        unit: Unit of measurement if applicable.
        description: Brief description of the parameter.
    """
    name: str
    display_name: str
    queryable: bool
    controllable: bool
    value_type: str  # "numeric", "enum", "boolean", "action"
    valid_values: Optional[Tuple[str, ...]] = None
    valid_range: Optional[Tuple[float, float]] = None
    unit: Optional[str] = None
    description: str = ""


# All radio parameters supported by the embedded system
RADIO_PARAMETERS: Dict[str, ParameterInfo] = {
    "frequency": ParameterInfo(
        name="frequency",
        display_name="Frequency",
        queryable=True,
        controllable=True,
        value_type="numeric",
        valid_range=(30e6, 600e6),
        unit="MHz",
        description="Radio operating frequency. WB: 200-600 MHz, NB: 30-100 or 200-600 MHz",
    ),
    "bandwidth": ParameterInfo(
        name="bandwidth",
        display_name="Bandwidth",
        queryable=True,
        controllable=True,
        value_type="enum",
        valid_values=("25 kHz", "50 kHz", "0.5 MHz", "1 MHz", "2 MHz", "4 MHz"),
        description="Channel bandwidth. NB: 25/50 kHz, WB: 0.5/1/2/4 MHz",
    ),
    "modulation": ParameterInfo(
        name="modulation",
        display_name="Modulation",
        queryable=True,
        controllable=True,
        value_type="enum",
        valid_values=("8PSK", "QAM4", "QAM16", "QAM32", "QAM64"),
        description="Modulation scheme. NB: 8PSK/QAM16, WB: QAM4/16/32/64",
    ),
    "waveform": ParameterInfo(
        name="waveform",
        display_name="Waveform",
        queryable=True,
        controllable=True,
        value_type="enum",
        valid_values=("WB", "NB"),
        description="Waveform mode. WB=Wideband, NB=Narrowband",
    ),
    "power": ParameterInfo(
        name="power",
        display_name="Power Level",
        queryable=True,
        controllable=True,
        value_type="enum",
        valid_values=("low", "medium", "high"),
        description="Transmit power level",
    ),
    "channel": ParameterInfo(
        name="channel",
        display_name="Channel",
        queryable=True,
        controllable=True,
        value_type="numeric",
        valid_range=(1, 200),
        description="Channel number (1-200)",
    ),
    "volume": ParameterInfo(
        name="volume",
        display_name="Volume",
        queryable=True,
        controllable=True,
        value_type="numeric",
        valid_range=(1, 10),
        description="Audio volume level (1-10)",
    ),
    "rxonly": ParameterInfo(
        name="rxonly",
        display_name="Receive Only",
        queryable=True,
        controllable=True,
        value_type="boolean",
        description="Receive-only mode. When on, radio does not transmit",
    ),
    "led": ParameterInfo(
        name="led",
        display_name="LED",
        queryable=True,
        controllable=True,
        value_type="boolean",
        description="LED indicator status",
    ),
    "gps": ParameterInfo(
        name="gps",
        display_name="GPS",
        queryable=True,
        controllable=True,
        value_type="boolean",
        description="GPS receiver status",
    ),
    "battery": ParameterInfo(
        name="battery",
        display_name="Battery",
        queryable=True,
        controllable=False,
        value_type="numeric",
        description="Battery percentage and voltage (read-only)",
    ),
    "members": ParameterInfo(
        name="members",
        display_name="Network Members",
        queryable=True,
        controllable=False,
        value_type="numeric",
        description="Number of connected network members (read-only)",
    ),
    "errors": ParameterInfo(
        name="errors",
        display_name="Errors",
        queryable=True,
        controllable=False,
        value_type="numeric",
        description="Error count and list (read-only)",
    ),
    "status": ParameterInfo(
        name="status",
        display_name="Radio Status",
        queryable=True,
        controllable=False,
        value_type="action",
        description="Overall radio status summary (read-only)",
    ),
    "config": ParameterInfo(
        name="config",
        display_name="Configuration",
        queryable=True,
        controllable=False,
        value_type="action",
        description="Full radio configuration dump (read-only)",
    ),
    "bit": ParameterInfo(
        name="bit",
        display_name="Built-In Test",
        queryable=True,
        controllable=True,
        value_type="action",
        description="Run or query Built-In Test diagnostics",
    ),
}


def get_queryable_parameters() -> List[str]:
    """Return list of parameters that can be queried."""
    return [p.display_name for p in RADIO_PARAMETERS.values() if p.queryable]


def get_controllable_parameters() -> List[str]:
    """Return list of parameters that can be modified."""
    return [p.display_name for p in RADIO_PARAMETERS.values() if p.controllable]


def get_parameter_info(name: str) -> Optional[ParameterInfo]:
    """Get parameter info by name (case-insensitive)."""
    name_lower = name.lower()
    for key, info in RADIO_PARAMETERS.items():
        if key == name_lower or info.display_name.lower() == name_lower:
            return info
    return None


def build_system_prompt() -> str:
    """
    Build the system prompt that constrains the LLM to supported commands.

    Returns:
        System prompt string with all command knowledge embedded.
    """
    queryable = []
    controllable = []

    for param in RADIO_PARAMETERS.values():
        if param.queryable:
            queryable.append(f"  - {param.display_name}: {param.description}")

        if param.controllable:
            if param.value_type == "numeric" and param.valid_range:
                range_str = f"{param.valid_range[0]}-{param.valid_range[1]}"
                if param.unit:
                    range_str += f" {param.unit}"
                controllable.append(f"  - {param.display_name} ({range_str})")
            elif param.value_type == "enum" and param.valid_values:
                values_str = "/".join(param.valid_values)
                controllable.append(f"  - {param.display_name} ({values_str})")
            elif param.value_type == "boolean":
                controllable.append(f"  - {param.display_name} (on/off)")
            elif param.value_type == "action":
                controllable.append(f"  - {param.display_name} (perform)")

    return f"""You are a radio control assistant. You help users operate a radio system through natural language commands.

CAPABILITIES - You can ONLY help with these radio parameters:

QUERYABLE (can ask about):
{chr(10).join(queryable)}

CONTROLLABLE (can modify):
{chr(10).join(controllable)}

RESPONSE FORMAT:
There are TWO types of responses:

1. CONVERSATION (no command needed):
   For greetings, questions about YOUR capabilities, or general chat - respond WITHOUT any [COMMAND: ...] tag.
   Examples:
   - "hi" -> "Hello! I'm your radio control assistant. How can I help?"
   - "what can you do?" -> "I can query and control radio parameters like frequency, volume, battery status, etc."
   - "thanks" -> "You're welcome!"

2. RADIO COMMAND (action needed):
   When user wants to query or change ANY radio parameter, you MUST output ONLY:
   [COMMAND: <natural language command>]

   Do NOT add any other text. Do NOT make up values. Just output the command tag.
   Examples:
   - "what's the frequency?" -> [COMMAND: what is the frequency]
   - "set frequency to 450 MHz" -> [COMMAND: set frequency to 450 MHz]
   - "turn on GPS" -> [COMMAND: enable GPS]
   - "check battery" -> [COMMAND: what is the battery]

CRITICAL RULES:
- You do NOT know the current radio state. NEVER make up or guess values.
- When user asks about ANY radio parameter (frequency, battery, volume, etc.), output [COMMAND: ...] and NOTHING ELSE.
- The radio system will execute the command and return the actual value.
- Only respond without [COMMAND: ...] for pure conversation about your capabilities or greetings.

RULES:
1. Only suggest commands from the supported parameters above
2. For control commands, validate values are within allowed ranges
3. If the user asks for something outside your capabilities, politely explain what you CAN do
4. Keep responses concise and technical
5. Do not make up features or pretend to have capabilities you don't have

BOUNDARIES:
- You CANNOT send messages, make calls, or communicate with other radios
- You CANNOT access the internet, files, or external systems
- You CANNOT remember information across different conversations
- You can ONLY query and control the radio parameters listed above"""


def is_control_command(user_input: str) -> bool:
    """
    Determine if the user input appears to be a control (modify) command.

    Args:
        user_input: The user's natural language input.

    Returns:
        True if the command appears to modify radio state.
    """
    control_keywords = [
        "set", "change", "adjust", "switch", "modify", "configure",
        "increase", "decrease", "raise", "lower", "turn on", "turn off",
        "enable", "disable", "activate", "deactivate", "toggle",
        "perform", "run", "execute", "go to", "tune to",
    ]
    input_lower = user_input.lower()
    return any(kw in input_lower for kw in control_keywords)


def extract_command_from_response(response: str) -> Optional[str]:
    """
    Extract the command from an LLM response.

    Args:
        response: The LLM's response text.

    Returns:
        The extracted command, or None if no command found.
    """
    import re
    match = re.search(r'\[COMMAND:\s*(.+?)\]', response, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
