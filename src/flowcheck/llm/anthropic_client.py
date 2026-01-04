"""Anthropic LLM Client for FlowCheck Smart Intent Verification."""

import json
import urllib.request
import urllib.error
from typing import Any

from .client import LLMClient


class AnthropicClient(LLMClient):
    """Client for Anthropic Claude API."""

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str = DEFAULT_BASE_URL,
        max_tokens: int = 1024,
    ):
        """Initialize Anthropic client.
        
        Args:
            api_key: Anthropic API key.
            model: Model name (e.g., "claude-sonnet-4-20250514", "claude-3-haiku-20240307").
            base_url: API base URL.
            max_tokens: Maximum tokens in response.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens

    def complete(self, prompt: str, system_prompt: str = "") -> dict[str, Any]:
        """Call Anthropic Messages API.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system instructions.
            
        Returns:
            Dictionary containing the parsed response.
        """
        url = f"{self.base_url}/messages"

        # Build request body
        data: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }
        
        if system_prompt:
            data["system"] = system_prompt

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                # Extract text from response
                content = result.get("content", [])
                if not content:
                    raise RuntimeError("Empty response from Anthropic API")
                
                # Get the text block
                text_content = ""
                for block in content:
                    if block.get("type") == "text":
                        text_content = block.get("text", "")
                        break
                
                if not text_content:
                    raise RuntimeError("No text content in Anthropic response")
                
                # Parse as JSON
                # Handle case where response might be wrapped in markdown code blocks
                cleaned = text_content.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                return json.loads(cleaned)
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"Anthropic API Error {e.code}: {error_body}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Anthropic response as JSON: {str(e)}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error calling Anthropic API: {str(e)}")
