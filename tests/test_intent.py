"""Unit tests for Intent Validation with GitHub integration."""

import unittest
from unittest.mock import patch, MagicMock
from flowcheck.intent import IntentValidator, verify_intent


class TestIntentValidator(unittest.TestCase):
    """Tests for the IntentValidator class."""

    def setUp(self):
        self.validator = IntentValidator(github_token="fake_token")

    @patch("flowcheck.intent.Repo")
    def test_get_github_repo(self, mock_repo_class):
        """Should extract owner/repo from remote URL."""
        mock_repo = MagicMock()
        mock_remote = MagicMock()
        mock_remote.url = "https://github.com/owner/repo.git"
        mock_repo.remotes = [mock_remote]
        mock_repo_class.return_value = mock_repo

        repo_name = self.validator._get_github_repo("/some/path")
        self.assertEqual(repo_name, "owner/repo")

    @patch("urllib.request.urlopen")
    def test_fetch_github_issue(self, mock_urlopen):
        """Should fetch issue JSON from GitHub API."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"title": "Test Issue", "body": "Fix the bug"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        issue_data = self.validator._fetch_github_issue("owner/repo", "42")
        self.assertEqual(issue_data["title"], "Test Issue")

    @patch.object(IntentValidator, "_fetch_github_issue")
    @patch.object(IntentValidator, "_get_github_repo")
    def test_validate_alignment(self, mock_get_repo, mock_fetch_issue):
        """Should calculate alignment score correctly."""
        mock_get_repo.return_value = "owner/repo"
        mock_fetch_issue.return_value = {
            "title": "Add auth",
            "body": "Implement login flow using OAuth2"
        }

        diff = "Added login endpoint and OAuth2 handlers"
        result = self.validator.validate("42", diff, "/path/to/repo")

        self.assertGreater(result.alignment_score, 0.1)
        self.assertEqual(result.ticket_summary, "Add auth")

    @patch.object(IntentValidator, "_fetch_github_issue")
    @patch.object(IntentValidator, "_get_github_repo")
    def test_validate_scope_creep(self, mock_get_repo, mock_fetch_issue):
        """Should flag scope creep items not in original issue."""
        mock_get_repo.return_value = "owner/repo"
        mock_fetch_issue.return_value = {
            "title": "Fix crash",
            "body": "Fix null pointer in user parsing"
        }

        # Diff contains "refactor" which isn't in the issue body
        diff = "Fix null pointer. Also refactor the whole database layer."
        result = self.validator.validate("42", diff, "/path/to/repo")

        self.assertTrue(
            any("Refactoring" in w for w in result.scope_creep_warnings))


if __name__ == "__main__":
    unittest.main()
