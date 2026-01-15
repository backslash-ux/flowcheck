"""Tests for Smart Intent Verification logic (v0.2)."""

import unittest
from unittest.mock import MagicMock, patch

from flowcheck.intent import IntentValidator, IntentValidationResult


class TestSmartIntent(unittest.TestCase):
    def setUp(self):
        self.config = {
            "intent": {
                "provider": "openai",
                "api_key_env": "FAKE_KEY"
            }
        }

    @patch("flowcheck.intent.get_llm_client")
    @patch("flowcheck.intent.Sanitizer")
    @patch.object(IntentValidator, "_fetch_github_issue")
    @patch.object(IntentValidator, "_get_github_repo")
    def test_smart_intent_flow(self, mock_get_repo, mock_fetch_issue, mock_sanitizer_cls, mock_get_client):
        """Test the LLM-based verification flow."""

        # Mock LLM Client
        mock_client = MagicMock()
        mock_client.complete.return_value = {
            "aligned": True,
            "scope_creep": False,
            "reason": "Perfect match."
        }
        mock_get_client.return_value = mock_client

        # Mock Git/Issue data
        mock_get_repo.return_value = "owner/repo"
        mock_fetch_issue.return_value = {"title": "Task A", "body": "Do X"}

        # Mock Sanitizer
        mock_sanitizer = mock_sanitizer_cls.return_value
        mock_sanitized_result = MagicMock()
        mock_sanitized_result.sanitized_text = "Sanitized Diff"
        mock_sanitizer.sanitize.return_value = mock_sanitized_result

        # Initialize Validator
        validator = IntentValidator(config=self.config)

        # Run validate
        result = validator.validate("42", "Raw Diff Content", "/tmp/repo")

        # Asserts
        self.assertTrue(result.is_aligned)
        self.assertEqual(result.reasoning, "Perfect match.")

        # Verify LLM was called with sanitized text
        self.assertTrue(mock_client.complete.called)
        args, _ = mock_client.complete.call_args
        self.assertIn("Sanitized Diff", args[0])
        self.assertNotIn("Raw Diff Content", args[0])  # Should be sanitized

        # Verify Sanitizer was called
        mock_sanitizer.sanitize.assert_called_with("Raw Diff Content")

    @patch("flowcheck.intent.get_llm_client")
    @patch.object(IntentValidator, "_fetch_github_issue")
    @patch.object(IntentValidator, "_get_github_repo")
    def test_smart_intent_fallback(self, mock_get_repo, mock_fetch_issue, mock_get_client):
        """Test fallback to TF-IDF when LLM fails."""

        # Mock LLM Client that crashes
        mock_client = MagicMock()
        mock_client.complete.side_effect = RuntimeError("API Down")
        mock_get_client.return_value = mock_client

        # Mock Git/Issue
        mock_get_repo.return_value = "owner/repo"
        mock_fetch_issue.return_value = {"title": "Task A", "body": "Do X"}

        validator = IntentValidator(config=self.config)

        # Run validate
        # We need a diff that matches somewhat for TF-IDF to score > 0
        result = validator.validate(
            "42", "Task A Do X implementation", "/tmp/repo")

        # Should return a result (not None) from fallback path
        self.assertIsNotNone(result)
        # Fallback now includes reasoning
        self.assertIn("Fallback to TF-IDF", result.reasoning)
        self.assertGreater(result.alignment_score, 0)


if __name__ == "__main__":
    unittest.main()
