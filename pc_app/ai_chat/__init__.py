"""
AI Chat module for radio control.

Provides an interactive chat interface for controlling the radio
through natural language commands.

Usage:
    python -m ai_chat [--simulate] [--claude]

Example:
    >>> from ai_chat import RadioChat, ChatConfig
    >>> config = ChatConfig.with_simulation()
    >>> chat = RadioChat(config)
    >>> chat.initialize()
    >>> result = chat.process_input("What's the frequency?")
    >>> print(result.response)
"""

from .chat import RadioChat, ChatResult, ChatState
from .config import ChatConfig, LLMProviderType

__all__ = [
    "RadioChat",
    "ChatResult",
    "ChatState",
    "ChatConfig",
    "LLMProviderType",
]

__version__ = "1.0.0"
