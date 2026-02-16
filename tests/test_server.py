"""Tests for FlowCheck MCP server tool functions.

These tests exercise the MCP tool functions directly (not over the wire)
against real temporary Git repositories.

The ``@mcp.tool`` decorator wraps each function in a ``FunctionTool``
object.  The underlying callable is available via the ``.fn`` attribute.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git import Repo

from flowcheck.server import (
    get_flow_state as _get_flow_state_tool,
    get_recommendations as _get_recommendations_tool,
    set_rules as _set_rules_tool,
    search_history as _search_history_tool,
    sanitize_content as _sanitize_content_tool,
    start_session as _start_session_tool,
    get_session_info as _get_session_info_tool,
    end_session as _end_session_tool,
)

# Unwrap FunctionTool → original callable
get_flow_state = _get_flow_state_tool.fn
get_recommendations = _get_recommendations_tool.fn
set_rules = _set_rules_tool.fn
search_history = _search_history_tool.fn
sanitize_content = _sanitize_content_tool.fn
start_session = _start_session_tool.fn
get_session_info = _get_session_info_tool.fn
end_session = _end_session_tool.fn


def _make_repo(tmp: str) -> Repo:
    """Create a minimal Git repo with one commit inside *tmp*."""
    repo = Repo.init(tmp)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "t@t.com").release()
    readme = Path(tmp) / "README.md"
    readme.write_text("# test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return repo


class TestGetFlowState(unittest.TestCase):
    """Tests for the get_flow_state MCP tool."""

    def test_returns_status_for_clean_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_repo(tmp)
            result = get_flow_state(tmp)
            self.assertIn("status", result)
            self.assertIn(result["status"], ("ok", "warning", "danger"))
            self.assertIn("branch_name", result)
            self.assertIn("uncommitted_lines", result)
            self.assertIn("uncommitted_files", result)
            self.assertIn("minutes_since_last_commit", result)
            self.assertIsInstance(result["security_flags"], list)

    def test_dirty_repo_has_uncommitted_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_repo(tmp)
            (Path(tmp) / "new.txt").write_text("hello world\n")
            result = get_flow_state(tmp)
            self.assertGreaterEqual(result["uncommitted_lines"], 0)

    def test_invalid_path_returns_error(self):
        result = get_flow_state("/nonexistent/repo/path")
        self.assertIn("error", result)
        self.assertEqual(result["status"], "error")


class TestGetRecommendations(unittest.TestCase):
    """Tests for the get_recommendations MCP tool."""

    def test_returns_recommendations_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_repo(tmp)
            result = get_recommendations(tmp)
            self.assertIn("recommendations", result)
            self.assertIsInstance(result["recommendations"], list)
            self.assertIn("status", result)
            self.assertIn("summary", result)

    def test_invalid_path_returns_error(self):
        result = get_recommendations("/nonexistent/repo/path")
        self.assertIn("error", result)


class TestSetRules(unittest.TestCase):
    """Tests for the set_rules MCP tool."""

    def test_valid_config_update(self):
        result = set_rules({"max_minutes_without_commit": 30})
        self.assertTrue(result.get("success"))
        self.assertIn("config", result)

    def test_invalid_key_rejected(self):
        result = set_rules({"not_a_real_key": 42})
        self.assertIn("error", result)

    def test_negative_value_rejected(self):
        result = set_rules({"max_minutes_without_commit": -5})
        self.assertIn("error", result)

    def test_non_int_value_rejected(self):
        result = set_rules({"max_lines_uncommitted": "big"})
        self.assertIn("error", result)


class TestSearchHistory(unittest.TestCase):
    """Tests for the search_history MCP tool."""

    def test_search_returns_results_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_repo(tmp)
            result = search_history("initial", tmp)
            self.assertIn("results", result)
            self.assertIsInstance(result["results"], list)
            self.assertIn("count", result)

    def test_invalid_path_returns_error(self):
        result = search_history("anything", "/nonexistent/repo/path")
        self.assertIn("error", result)


class TestSanitizeContent(unittest.TestCase):
    """Tests for the sanitize_content MCP tool."""

    def test_clean_text_passes_through(self):
        result = sanitize_content("Hello, this is normal text.")
        self.assertEqual(result["sanitized_text"],
                         "Hello, this is normal text.")
        self.assertFalse(result["pii_detected"])
        self.assertFalse(result["secrets_detected"])
        self.assertEqual(result["redacted_count"], 0)

    def test_email_is_redacted(self):
        result = sanitize_content("Contact me at user@example.com for info.")
        self.assertTrue(result["pii_detected"])
        self.assertGreater(result["redacted_count"], 0)
        self.assertNotIn("user@example.com", result["sanitized_text"])

    def test_api_key_is_redacted(self):
        result = sanitize_content('api_key="AKIAIOSFODNN7EXAMPLE1234567890"')
        self.assertTrue(result["secrets_detected"])
        self.assertGreater(result["redacted_count"], 0)


class TestSessionLifecycle(unittest.TestCase):
    """Tests for session start / info / end tools."""

    def setUp(self):
        from flowcheck.session.manager import SessionManager
        SessionManager._instance = None

    def tearDown(self):
        from flowcheck.session.manager import SessionManager
        SessionManager._instance = None

    def test_full_lifecycle(self):
        start = start_session(agent_id="test-agent")
        self.assertIn("session_id", start)
        self.assertEqual(start["agent_id"], "test-agent")

        info = get_session_info()
        self.assertIn("session_id", info)

        done = end_session()
        self.assertIn("session_id", done)
        self.assertIn("message", done)

    def test_end_without_start(self):
        result = end_session()
        self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
