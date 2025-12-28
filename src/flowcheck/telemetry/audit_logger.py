"""Audit logger for immutable, structured logging.

Provides append-only audit trails for SOC 2 compliance, recording
every MCP tool invocation with trace context and risk scores.
"""

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""

    timestamp: datetime
    trace_id: str
    action: str
    agent_id: str
    risk_score: float = 0.0
    pii_detected: bool = False
    injection_detected: bool = False
    status: str = "ok"
    repo_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "action": self.action,
            "agent_id": self.agent_id,
            "risk_score": self.risk_score,
            "pii_detected": self.pii_detected,
            "injection_detected": self.injection_detected,
            "status": self.status,
            "repo_path": self.repo_path,
            "metadata": self.metadata,
        }

    def to_log_line(self) -> str:
        """Convert to single-line log format."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        """Create AuditEntry from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            trace_id=data["trace_id"],
            action=data["action"],
            agent_id=data["agent_id"],
            risk_score=data.get("risk_score", 0.0),
            pii_detected=data.get("pii_detected", False),
            injection_detected=data.get("injection_detected", False),
            status=data.get("status", "ok"),
            repo_path=data.get("repo_path"),
            metadata=data.get("metadata", {}),
        )


class AuditLogger:
    """Append-only audit logger for FlowCheck operations.

    Writes structured log entries to ~/.flowcheck/audit.log in JSON Lines format.
    Thread-safe and creates log file if it doesn't exist.
    """

    DEFAULT_LOG_PATH = Path.home() / ".flowcheck" / "audit.log"

    def __init__(
        self,
        log_path: Optional[Path] = None,
        agent_id: Optional[str] = None,
    ):
        """Initialize the audit logger.

        Args:
            log_path: Path to the audit log file.
            agent_id: Default agent ID for entries.
        """
        self.log_path = log_path or self.DEFAULT_LOG_PATH
        self.agent_id = agent_id or os.environ.get(
            "FLOWCHECK_AGENT_ID", "unknown")
        self._lock = threading.Lock()
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Ensure log file and parent directories exist."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def log(
        self,
        action: str,
        trace_id: Optional[str] = None,
        risk_score: float = 0.0,
        pii_detected: bool = False,
        injection_detected: bool = False,
        status: str = "ok",
        repo_path: Optional[str] = None,
        **metadata,
    ) -> AuditEntry:
        """Log an audit entry.

        Args:
            action: The action being logged (e.g., "get_flow_state").
            trace_id: Optional trace ID (generated if not provided).
            risk_score: Risk score from 0.0 to 1.0.
            pii_detected: Whether PII was detected.
            injection_detected: Whether injection patterns were detected.
            status: Flow health status.
            repo_path: Path to the repository.
            **metadata: Additional metadata to include.

        Returns:
            The created AuditEntry.
        """
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            trace_id=trace_id or uuid.uuid4().hex[:32],
            action=action,
            agent_id=self.agent_id,
            risk_score=risk_score,
            pii_detected=pii_detected,
            injection_detected=injection_detected,
            status=status,
            repo_path=repo_path,
            metadata=metadata,
        )

        self._write_entry(entry)
        return entry

    def _write_entry(self, entry: AuditEntry):
        """Write an entry to the log file (thread-safe, append-only)."""
        with self._lock:
            with open(self.log_path, "a") as f:
                f.write(entry.to_log_line() + "\n")

    def log_tool_call(
        self,
        tool_name: str,
        repo_path: str,
        result: dict,
        trace_id: Optional[str] = None,
    ) -> AuditEntry:
        """Convenience method for logging MCP tool calls.

        Args:
            tool_name: Name of the MCP tool.
            repo_path: Path to the repository.
            result: Result dictionary from the tool.
            trace_id: Optional trace ID.

        Returns:
            The created AuditEntry.
        """
        # Extract security info from result
        security_flags = result.get("security_flags", [])
        pii_detected = any(
            "PII" in flag or "EMAIL" in flag for flag in security_flags)
        injection_detected = any("injection" in flag.lower()
                                 for flag in security_flags)

        return self.log(
            action=f"tool:{tool_name}",
            trace_id=trace_id,
            risk_score=len(security_flags) * 0.2,  # Simple heuristic
            pii_detected=pii_detected,
            injection_detected=injection_detected,
            status=result.get("status", "ok"),
            repo_path=repo_path,
            security_flag_count=len(security_flags),
        )

    def get_recent_entries(self, limit: int = 100) -> list[AuditEntry]:
        """Read recent audit entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of AuditEntry objects (most recent last).
        """
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path, "r") as f:
            lines = f.readlines()

        # Get last N lines
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    entries.append(AuditEntry.from_dict(data))
                except json.JSONDecodeError:
                    continue

        return entries

    def get_entries_for_trace(self, trace_id: str) -> list[AuditEntry]:
        """Get all entries for a specific trace ID.

        Args:
            trace_id: The trace ID to search for.

        Returns:
            List of matching AuditEntry objects.
        """
        entries = []

        if not self.log_path.exists():
            return entries

        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and trace_id in line:
                    try:
                        data = json.loads(line)
                        if data.get("trace_id") == trace_id:
                            entries.append(AuditEntry.from_dict(data))
                    except json.JSONDecodeError:
                        continue

        return entries

    def get_security_incidents(self, limit: int = 50) -> list[AuditEntry]:
        """Get entries where security issues were detected.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of entries with security flags.
        """
        incidents = []

        if not self.log_path.exists():
            return incidents

        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("pii_detected") or data.get("injection_detected") or data.get("risk_score", 0) > 0.5:
                            incidents.append(AuditEntry.from_dict(data))
                            if len(incidents) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue

        return incidents


# Global logger instance
_global_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AuditLogger()
    return _global_logger


def configure_audit_logger(
    log_path: Optional[Path] = None,
    agent_id: Optional[str] = None,
):
    """Configure the global audit logger."""
    global _global_logger
    _global_logger = AuditLogger(log_path=log_path, agent_id=agent_id)
