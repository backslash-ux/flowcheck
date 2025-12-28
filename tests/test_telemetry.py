"""Unit tests for the Telemetry Layer."""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from flowcheck.telemetry.otel_emitter import OTelEmitter, TraceContext
from flowcheck.telemetry.audit_logger import AuditLogger, AuditEntry


class TestOTelEmitter:
    """Tests for OpenTelemetry emitter."""

    def test_emitter_creates_trace_context(self):
        """Should create trace context with IDs."""
        emitter = OTelEmitter()

        with emitter.trace_tool_call("test_tool") as ctx:
            assert ctx.trace_id is not None
            assert ctx.span_id is not None
            assert len(ctx.trace_id) == 32
            assert len(ctx.span_id) == 16

    def test_trace_context_has_agent_id(self):
        """Should include agent ID in context."""
        emitter = OTelEmitter(agent_id="test-agent")

        with emitter.trace_tool_call("test_tool") as ctx:
            assert ctx.agent_id == "test-agent"

    def test_trace_context_has_action_type(self):
        """Should set action type to tool_call."""
        emitter = OTelEmitter()

        with emitter.trace_tool_call("test_tool") as ctx:
            assert ctx.action_type == "tool_call"

    def test_trace_context_serializable(self):
        """Context should serialize to dict."""
        ctx = TraceContext(
            trace_id="abc123",
            span_id="def456",
            agent_id="test",
            action_type="tool_call",
        )

        data = ctx.to_dict()

        assert data["trace_id"] == "abc123"
        assert data["span_id"] == "def456"
        assert data["agent_id"] == "test"

    def test_decorator_wraps_function(self):
        """@traced decorator should wrap functions."""
        emitter = OTelEmitter()

        @emitter.traced()
        def my_tool(repo_path: str):
            return {"status": "ok"}

        result = my_tool("/path/to/repo")

        assert result["status"] == "ok"


class TestAuditLogger:
    """Tests for audit logger."""

    def test_creates_log_file(self):
        """Should create log file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            assert log_path.exists()

    def test_logs_entry(self):
        """Should write entry to log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            entry = logger.log(
                action="test_action",
                risk_score=0.5,
                status="warning",
            )

            assert entry.action == "test_action"
            assert entry.risk_score == 0.5

            # Verify written to file
            with open(log_path) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["action"] == "test_action"

    def test_get_recent_entries(self):
        """Should return recent log entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            # Log multiple entries
            logger.log(action="action1")
            logger.log(action="action2")
            logger.log(action="action3")

            entries = logger.get_recent_entries(limit=2)

            assert len(entries) == 2
            assert entries[1].action == "action3"  # Most recent last

    def test_get_entries_for_trace(self):
        """Should find entries by trace ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            # Log with specific trace ID
            trace_id = "abc123def456"
            logger.log(action="traced_action", trace_id=trace_id)
            logger.log(action="other_action")

            entries = logger.get_entries_for_trace(trace_id)

            assert len(entries) == 1
            assert entries[0].action == "traced_action"

    def test_get_security_incidents(self):
        """Should find entries with security flags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            logger.log(action="normal", risk_score=0.1)
            logger.log(action="pii_found", pii_detected=True)
            logger.log(action="injection", injection_detected=True)

            incidents = logger.get_security_incidents()

            assert len(incidents) == 2
            assert any(e.action == "pii_found" for e in incidents)
            assert any(e.action == "injection" for e in incidents)


class TestAuditEntry:
    """Tests for AuditEntry."""

    def test_to_dict(self):
        """Should serialize to dictionary."""
        entry = AuditEntry(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            trace_id="abc123",
            action="test",
            agent_id="agent",
            risk_score=0.5,
        )

        data = entry.to_dict()

        assert data["trace_id"] == "abc123"
        assert data["action"] == "test"
        assert data["risk_score"] == 0.5

    def test_to_log_line(self):
        """Should serialize to JSON line."""
        entry = AuditEntry(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            trace_id="abc123",
            action="test",
            agent_id="agent",
        )

        line = entry.to_log_line()

        assert '"trace_id":"abc123"' in line
        assert "\n" not in line  # Single line

    def test_from_dict(self):
        """Should deserialize from dictionary."""
        data = {
            "timestamp": "2024-01-01T00:00:00+00:00",
            "trace_id": "abc123",
            "action": "test",
            "agent_id": "agent",
        }

        entry = AuditEntry.from_dict(data)

        assert entry.trace_id == "abc123"
        assert entry.action == "test"
