"""Tests for FlowCheck session management (v0.3)."""

import unittest
from datetime import datetime, timezone

from flowcheck.session.manager import SessionManager, Session, get_session_manager


class TestSession(unittest.TestCase):
    """Test the Session dataclass."""

    def test_session_creation(self):
        session = Session(
            session_id="abc123",
            agent_id="test-agent",
            started_at=datetime.now(timezone.utc),
        )
        self.assertEqual(session.session_id, "abc123")
        self.assertEqual(session.agent_id, "test-agent")
        self.assertEqual(session.tool_calls, 0)

    def test_record_tool_call(self):
        session = Session(
            session_id="abc123",
            agent_id="test-agent",
            started_at=datetime.now(timezone.utc),
        )
        session.record_tool_call()
        session.record_tool_call()
        
        self.assertEqual(session.tool_calls, 2)

    def test_to_dict(self):
        session = Session(
            session_id="abc123",
            agent_id="test-agent",
            started_at=datetime.now(timezone.utc),
        )
        data = session.to_dict()
        
        self.assertEqual(data["session_id"], "abc123")
        self.assertEqual(data["agent_id"], "test-agent")
        self.assertIn("started_at", data)
        self.assertIn("duration_seconds", data)


class TestSessionManager(unittest.TestCase):
    """Test the SessionManager."""

    def setUp(self):
        # Reset the singleton for testing
        SessionManager._instance = None
        self.manager = get_session_manager()

    def tearDown(self):
        self.manager.end_session()
        SessionManager._instance = None

    def test_singleton_pattern(self):
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        self.assertIs(manager1, manager2)

    def test_start_session(self):
        session = self.manager.start_session(agent_id="claude")
        
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.agent_id, "claude")
        self.assertEqual(session.tool_calls, 0)

    def test_get_current_session(self):
        self.assertIsNone(self.manager.get_current_session())
        
        self.manager.start_session()
        
        self.assertIsNotNone(self.manager.get_current_session())

    def test_get_or_create_session(self):
        # Should create if none exists
        session1 = self.manager.get_or_create_session()
        self.assertIsNotNone(session1)
        
        # Should return same session
        session2 = self.manager.get_or_create_session()
        self.assertEqual(session1.session_id, session2.session_id)

    def test_record_tool_call(self):
        self.manager.start_session()
        
        session_id = self.manager.record_tool_call()
        
        self.assertIsNotNone(session_id)
        session = self.manager.get_current_session()
        self.assertEqual(session.tool_calls, 1)

    def test_record_tool_call_no_session(self):
        result = self.manager.record_tool_call()
        self.assertIsNone(result)

    def test_get_session_id(self):
        self.assertIsNone(self.manager.get_session_id())
        
        self.manager.start_session()
        session_id = self.manager.get_session_id()
        
        self.assertIsNotNone(session_id)
        self.assertEqual(len(session_id), 16)

    def test_end_session(self):
        self.manager.start_session()
        
        ended = self.manager.end_session()
        
        self.assertIsNotNone(ended)
        self.assertIsNone(self.manager.get_current_session())

    def test_end_session_no_active(self):
        ended = self.manager.end_session()
        self.assertIsNone(ended)

    def test_get_session_info_no_session(self):
        info = self.manager.get_session_info()
        
        self.assertIsNone(info.get("session_id"))
        self.assertFalse(info.get("active", True))

    def test_get_session_info_with_session(self):
        self.manager.start_session(agent_id="cursor")
        
        info = self.manager.get_session_info()
        
        self.assertIsNotNone(info["session_id"])
        self.assertEqual(info["agent_id"], "cursor")


if __name__ == "__main__":
    unittest.main()
