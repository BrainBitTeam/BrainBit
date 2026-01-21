"""
Claude API LLM provider implementation.

Provides integration with Anthropic's Claude API.
"""

import json
import os
import urllib.request
import urllib.error
from typing import List, Optional

from .base import LLMProvider, Message, Role


class ClaudeProvider(LLMProvider):
    """
    LLM provider using Anthropic's Claude API.

    Requires ANTHROPIC_API_KEY environment variable to be set.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0-1.0).
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    @property
    def name(self) -> str:
        return f"Claude ({self._model})"

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)

    def generate(self, messages: List[Message]) -> str:
        """
        Generate response using Claude API.

        Args:
            messages: Conversation history including system prompt.

        Returns:
            Generated response text.

        Raises:
            ConnectionError: If API is unreachable.
            RuntimeError: If generation fails or API key is missing.
        """
        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. "
                "Set it via environment variable or pass api_key to constructor."
            )

        # Separate system message from conversation
        system_content = ""
        conversation = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_content = msg.content
            else:
                conversation.append(msg.to_dict())

        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": conversation,
        }

        if system_content:
            payload["system"] = system_content

        request = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": self.API_VERSION,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                content_blocks = data.get("content", [])
                if content_blocks and content_blocks[0].get("type") == "text":
                    return content_blocks[0].get("text", "")
                return ""
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Claude API error ({e.code}): {error_body}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot connect to Claude API: {e}") from e
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid response from Claude API: {e}") from e
