"""LLM Client for FlowCheck Smart Intent Verification."""

import json
import os
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = "") -> dict[str, Any]:
        """Send a completion request to the LLM.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instructions.

        Returns:
            Dictionary containing the response (e.g., parsed JSON).
        """
        pass


class OpenAIClient(LLMClient):
    """Client for OpenAI-compatible APIs."""

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def complete(self, prompt: str, system_prompt: str = "") -> dict[str, Any]:
        """Call OpenAI Chat Completions API."""
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            # Enforce JSON if supported
            "response_format": {"type": "json_object"}
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"LLM API Error {e.code}: {error_body}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")


def get_llm_client(config: dict[str, Any]) -> Optional[LLMClient]:
    """Factory to create LLM client from config."""
    intent_config = config.get("intent", {})
    provider = intent_config.get("provider")

    if not provider:
        return None

    if provider == "openai":
        api_key = os.environ.get(intent_config.get(
            "api_key_env", "OPENAI_API_KEY"))
        if not api_key:
            return None  # Fallback to local

        return OpenAIClient(
            api_key=api_key,
            model=intent_config.get("model", "gpt-4o"),
            base_url=intent_config.get("base_url", "https://api.openai.com/v1")
        )

    # We can add 'anthropic' here later as requested in roadmap

    return None
