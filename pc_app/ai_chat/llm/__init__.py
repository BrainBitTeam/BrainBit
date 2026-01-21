"""
LLM provider abstraction layer.

This package provides a unified interface for different LLM backends,
allowing easy switching between Ollama (local) and Claude (cloud).
"""

from .base import LLMProvider, Message, Role
from .ollama_provider import OllamaProvider
from .claude_provider import ClaudeProvider

__all__ = [
    "LLMProvider",
    "Message",
    "Role",
    "OllamaProvider",
    "ClaudeProvider",
]
