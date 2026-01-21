"""
Ollama LLM provider implementation.

Provides integration with locally-running Ollama models via HTTP API.
"""

import json
import urllib.request
import urllib.error
from typing import List, Optional

from .base import LLMProvider, Message


class OllamaProvider(LLMProvider):
    """
    LLM provider using local Ollama instance.

    Communicates with Ollama via its HTTP API on localhost.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        temperature: float = 0.3,
        timeout_seconds: float = 60.0,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL.
            model: Model name to use.
            temperature: Sampling temperature (0.0-1.0).
            timeout_seconds: Request timeout.
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._timeout = timeout_seconds

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"

    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available."""
        try:
            url = f"{self._base_url}/api/tags"
            request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check if our model is available (with or without :latest tag)
                model_base = self._model.split(":")[0]
                return any(model_base in m for m in models)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return False

    def generate(self, messages: List[Message]) -> str:
        """
        Generate response using Ollama chat API.

        Args:
            messages: Conversation history including system prompt.

        Returns:
            Generated response text.

        Raises:
            ConnectionError: If Ollama server is unreachable.
            RuntimeError: If generation fails.
        """
        url = f"{self._base_url}/api/chat"

        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": self._temperature,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}") from e
        except TimeoutError as e:
            raise ConnectionError(f"Ollama request timed out: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Invalid response from Ollama: {e}") from e

    def ensure_model_available(self) -> bool:
        """
        Pull the model if not already available.

        Returns:
            True if model is now available, False if pull failed.
        """
        if self.is_available():
            return True

        # Try to pull the model
        url = f"{self._base_url}/api/pull"
        payload = {"name": self._model, "stream": False}

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            # Model pull can take a long time
            with urllib.request.urlopen(request, timeout=600) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError):
            return False
