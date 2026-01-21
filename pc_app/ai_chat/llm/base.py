"""
Abstract base class for LLM providers.

Defines the interface that all LLM implementations must follow,
ensuring consistent behavior across different backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Role(Enum):
    """Message role in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """
    A single message in a conversation.

    Attributes:
        role: The role of the message sender.
        content: The text content of the message.
    """
    role: Role
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary format for API calls."""
        return {"role": self.role.value, "content": self.content}


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Implementations must provide the generate method to produce
    responses from conversation history.
    """

    @abstractmethod
    def generate(self, messages: List[Message]) -> str:
        """
        Generate a response from the given conversation history.

        Args:
            messages: List of messages representing the conversation.
                     Should include the system prompt as the first message.

        Returns:
            The generated response text.

        Raises:
            ConnectionError: If the LLM service is unavailable.
            RuntimeError: If generation fails for other reasons.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM provider is available and ready.

        Returns:
            True if the provider can accept requests, False otherwise.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name for display purposes."""
        pass
