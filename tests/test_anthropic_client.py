"""Tests for Anthropic LLM client (v0.3)."""

import json
import unittest
from unittest.mock import MagicMock, patch

from flowcheck.llm.anthropic_client import AnthropicClient
from flowcheck.llm.client import get_llm_client


class TestAnthropicClient(unittest.TestCase):
    """Test the AnthropicClient."""

    def test_init_defaults(self):
        client = AnthropicClient(api_key="test-key")
        
        self.assertEqual(client.model, "claude-sonnet-4-20250514")
        self.assertEqual(client.base_url, "https://api.anthropic.com/v1")
        self.assertEqual(client.max_tokens, 1024)

    def test_init_custom_model(self):
        client = AnthropicClient(
            api_key="test-key",
            model="claude-3-haiku-20240307",
        )
        
        self.assertEqual(client.model, "claude-3-haiku-20240307")

    @patch("flowcheck.llm.anthropic_client.urllib.request.urlopen")
    def test_complete_success(self, mock_urlopen):
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": [
                {"type": "text", "text": '{"aligned": true, "scope_creep": false, "reason": "OK"}'}
            ]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        result = client.complete("Test prompt", system_prompt="Be helpful")

        self.assertTrue(result["aligned"])
        self.assertFalse(result["scope_creep"])

    @patch("flowcheck.llm.anthropic_client.urllib.request.urlopen")
    def test_complete_handles_markdown_wrapped_json(self, mock_urlopen):
        # Mock response with markdown code block
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": [
                {"type": "text", "text": '```json\n{"aligned": true}\n```'}
            ]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        result = client.complete("Test prompt")

        self.assertTrue(result["aligned"])


class TestGetLLMClientFactory(unittest.TestCase):
    """Test the LLM client factory function."""

    def test_no_provider_returns_none(self):
        config = {}
        client = get_llm_client(config)
        self.assertIsNone(client)

    def test_unknown_provider_returns_none(self):
        config = {"intent": {"provider": "unknown"}}
        client = get_llm_client(config)
        self.assertIsNone(client)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_openai_provider(self):
        config = {"intent": {"provider": "openai"}}
        client = get_llm_client(config)
        
        self.assertIsNotNone(client)
        from flowcheck.llm.client import OpenAIClient
        self.assertIsInstance(client, OpenAIClient)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_anthropic_provider(self):
        config = {"intent": {"provider": "anthropic"}}
        client = get_llm_client(config)
        
        self.assertIsNotNone(client)
        self.assertIsInstance(client, AnthropicClient)

    @patch.dict("os.environ", {"MY_ANTHROPIC_KEY": "test-key"})
    def test_anthropic_custom_env_var(self):
        config = {
            "intent": {
                "provider": "anthropic",
                "api_key_env": "MY_ANTHROPIC_KEY",
                "model": "claude-3-haiku-20240307",
            }
        }
        client = get_llm_client(config)
        
        self.assertIsNotNone(client)
        self.assertEqual(client.model, "claude-3-haiku-20240307")

    def test_anthropic_no_key_returns_none(self):
        config = {"intent": {"provider": "anthropic"}}
        # No env var set
        with patch.dict("os.environ", {}, clear=True):
            client = get_llm_client(config)
            self.assertIsNone(client)


if __name__ == "__main__":
    unittest.main()
