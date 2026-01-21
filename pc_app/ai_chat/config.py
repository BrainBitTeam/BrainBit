"""
Configuration for the AI Chat module.

This module contains all configurable parameters for the chat system,
including network settings, LLM provider configuration, and conversation limits.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LLMProviderType(Enum):
    """Supported LLM provider types."""
    OLLAMA = "ollama"
    CLAUDE = "claude"


@dataclass(frozen=True)
class NetworkConfig:
    """TCP connection configuration for the ZCU102 target."""
    host: str = "192.168.1.11"
    port: int = 5000
    timeout_seconds: float = 5.0
    reconnect_attempts: int = 3


@dataclass(frozen=True)
class OllamaConfig:
    """Ollama-specific configuration."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    temperature: float = 0.3
    timeout_seconds: float = 120.0


@dataclass(frozen=True)
class ClaudeConfig:
    """Claude API configuration."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    temperature: float = 0.3


@dataclass(frozen=True)
class ConversationConfig:
    """Conversation management settings."""
    max_history_messages: int = 10
    require_confirmation_for_control: bool = True


@dataclass
class ChatConfig:
    """
    Main configuration container for the AI Chat module.

    Attributes:
        provider: The LLM provider to use (ollama or claude).
        simulation_mode: If True, operates without target connection.
        network: TCP connection settings for the target.
        ollama: Ollama-specific settings.
        claude: Claude API settings.
        conversation: Conversation management settings.
    """
    provider: LLMProviderType = LLMProviderType.OLLAMA
    simulation_mode: bool = False
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)

    @classmethod
    def with_simulation(cls) -> "ChatConfig":
        """Create a configuration with simulation mode enabled."""
        return cls(simulation_mode=True)

    @classmethod
    def with_claude(cls, api_key: Optional[str] = None) -> "ChatConfig":
        """Create a configuration using Claude as the LLM provider."""
        return cls(provider=LLMProviderType.CLAUDE)
