"""
AI Chat orchestrator for radio control.

Manages conversation flow, LLM interaction, and command execution.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

from .config import ChatConfig, LLMProviderType
from .llm import LLMProvider, OllamaProvider, ClaudeProvider, Message, Role
from .command_knowledge import (
    build_system_prompt,
    extract_command_from_response,
    is_control_command,
)
from .radio_client import RadioClient, RadioResponse


class ChatState(Enum):
    """Current state of the chat interaction."""
    READY = auto()
    AWAITING_CONFIRMATION = auto()
    ERROR = auto()


@dataclass
class PendingCommand:
    """A command awaiting user confirmation."""
    command: str
    llm_response: str


@dataclass
class ChatResult:
    """
    Result of processing user input.

    Attributes:
        response: The response text to show the user.
        needs_confirmation: Whether user confirmation is needed.
        pending_command: The command awaiting confirmation, if any.
        radio_response: Response from radio if command was executed.
    """
    response: str
    needs_confirmation: bool = False
    pending_command: Optional[PendingCommand] = None
    radio_response: Optional[RadioResponse] = None


class RadioChat:
    """
    Interactive AI chat for radio control.

    Orchestrates conversation between user, LLM, and radio target.
    """

    def __init__(self, config: Optional[ChatConfig] = None):
        """
        Initialize chat with given configuration.

        Args:
            config: Chat configuration. Uses defaults if None.
        """
        self._config = config or ChatConfig()
        self._llm: Optional[LLMProvider] = None
        self._radio: Optional[RadioClient] = None
        self._history: List[Message] = []
        self._state = ChatState.READY
        self._pending_command: Optional[PendingCommand] = None
        self._system_prompt = build_system_prompt()

    def initialize(self) -> Tuple[bool, str]:
        """
        Initialize LLM provider and radio client.

        Returns:
            Tuple of (success, status_message).
        """
        # Initialize LLM provider
        if self._config.provider == LLMProviderType.OLLAMA:
            self._llm = OllamaProvider(
                base_url=self._config.ollama.base_url,
                model=self._config.ollama.model,
                temperature=self._config.ollama.temperature,
                timeout_seconds=self._config.ollama.timeout_seconds,
            )
        else:
            self._llm = ClaudeProvider(
                model=self._config.claude.model,
                max_tokens=self._config.claude.max_tokens,
                temperature=self._config.claude.temperature,
            )

        # Check LLM availability
        if not self._llm.is_available():
            if self._config.provider == LLMProviderType.OLLAMA:
                return False, (
                    "Ollama not available. Please ensure:\n"
                    "  1. Ollama is installed: curl -fsSL https://ollama.com/install.sh | sh\n"
                    "  2. Ollama is running: ollama serve\n"
                    f"  3. Model is pulled: ollama pull {self._config.ollama.model}"
                )
            else:
                return False, (
                    "Claude API not available. Please set ANTHROPIC_API_KEY environment variable."
                )

        # Initialize radio client
        self._radio = RadioClient(
            host=self._config.network.host,
            port=self._config.network.port,
            timeout=self._config.network.timeout_seconds,
            simulation_mode=self._config.simulation_mode,
        )

        if not self._radio.connect():
            if not self._config.simulation_mode:
                return False, (
                    f"Cannot connect to radio at {self._config.network.host}:{self._config.network.port}"
                )

        mode_str = "SIMULATION" if self._config.simulation_mode else "LIVE"
        return True, f"Initialized with {self._llm.name} [{mode_str}]"

    def _build_messages(self, user_input: str) -> List[Message]:
        """Build message list for LLM including history."""
        messages = [Message(Role.SYSTEM, self._system_prompt)]

        # Add conversation history (limited by config)
        max_history = self._config.conversation.max_history_messages
        if len(self._history) > max_history:
            self._history = self._history[-max_history:]

        messages.extend(self._history)
        messages.append(Message(Role.USER, user_input))

        return messages

    def _add_to_history(self, role: Role, content: str):
        """Add a message to conversation history."""
        self._history.append(Message(role, content))

        # Trim if needed
        max_history = self._config.conversation.max_history_messages
        if len(self._history) > max_history:
            self._history = self._history[-max_history:]

    def process_input(self, user_input: str) -> ChatResult:
        """
        Process user input and return result.

        Handles conversation flow including confirmation for control commands.

        Args:
            user_input: The user's input text.

        Returns:
            ChatResult with response and any pending actions.
        """
        user_input = user_input.strip()

        if not user_input:
            return ChatResult(response="Please enter a command or question.")

        # Handle confirmation responses
        if self._state == ChatState.AWAITING_CONFIRMATION:
            return self._handle_confirmation(user_input)

        # Get LLM response
        try:
            messages = self._build_messages(user_input)
            llm_response = self._llm.generate(messages)
        except (ConnectionError, RuntimeError) as e:
            self._state = ChatState.ERROR
            return ChatResult(response=f"LLM error: {e}")

        # Extract command from response
        command = extract_command_from_response(llm_response)

        if not command:
            # No command - just conversation
            self._add_to_history(Role.USER, user_input)
            self._add_to_history(Role.ASSISTANT, llm_response)
            return ChatResult(response=llm_response)

        # Check if confirmation needed for control commands
        requires_confirmation = (
            self._config.conversation.require_confirmation_for_control
            and is_control_command(command)
        )

        if requires_confirmation:
            self._state = ChatState.AWAITING_CONFIRMATION
            self._pending_command = PendingCommand(
                command=command,
                llm_response=llm_response,
            )
            # Remove the [COMMAND: ...] part from display
            display_response = llm_response.replace(f"[COMMAND: {command}]", "").strip()
            if not display_response:
                display_response = f"Execute: {command}"
            return ChatResult(
                response=f"{display_response}\n\nConfirm? [y/n]",
                needs_confirmation=True,
                pending_command=self._pending_command,
            )

        # Execute command immediately (query commands)
        return self._execute_command(command, user_input, llm_response)

    def _handle_confirmation(self, user_input: str) -> ChatResult:
        """Handle user confirmation response."""
        response_lower = user_input.lower().strip()

        if response_lower in ("y", "yes", "ok", "confirm", "proceed"):
            if self._pending_command:
                result = self._execute_command(
                    self._pending_command.command,
                    "",  # Original input not needed
                    self._pending_command.llm_response,
                )
                self._state = ChatState.READY
                self._pending_command = None
                return result

        # User declined or gave other input
        self._state = ChatState.READY
        self._pending_command = None
        return ChatResult(response="Command cancelled.")

    def _execute_command(
        self,
        command: str,
        user_input: str,
        llm_response: str,
    ) -> ChatResult:
        """Execute a command on the radio."""
        try:
            radio_response = self._radio.send_command(command)
        except Exception as e:
            return ChatResult(response=f"Radio error: {e}")

        # Add to history
        if user_input:
            self._add_to_history(Role.USER, user_input)

        # Build response
        if radio_response.success:
            response_text = radio_response.message
            if radio_response.is_simulated:
                response_text += " [simulated]"
        else:
            response_text = f"Failed: {radio_response.message}"

        self._add_to_history(Role.ASSISTANT, response_text)

        return ChatResult(
            response=response_text,
            radio_response=radio_response,
        )

    def reset(self):
        """Reset conversation history and state."""
        self._history.clear()
        self._state = ChatState.READY
        self._pending_command = None

    def shutdown(self):
        """Clean up resources."""
        if self._radio:
            self._radio.disconnect()

    @property
    def is_ready(self) -> bool:
        """Return True if chat is ready for input."""
        return self._state == ChatState.READY

    @property
    def awaiting_confirmation(self) -> bool:
        """Return True if waiting for user confirmation."""
        return self._state == ChatState.AWAITING_CONFIRMATION

    @property
    def llm_name(self) -> str:
        """Return the name of the active LLM provider."""
        return self._llm.name if self._llm else "Not initialized"

    @property
    def is_simulation(self) -> bool:
        """Return True if running in simulation mode."""
        return self._config.simulation_mode
