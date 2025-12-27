"""Data models for FlowCheck flow state."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Status(str, Enum):
    """Flow health status indicator."""

    OK = "ok"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class FlowState:
    """Represents the flow health of a repository at a given moment.

    Attributes:
        minutes_since_last_commit: Minutes elapsed since the HEAD commit.
        uncommitted_lines: Sum of additions and deletions in the working tree.
        uncommitted_files: Count of modified/staged files.
        branch_name: Active Git branch.
        status: Qualitative health indicator (ok, warning, danger).
    """

    minutes_since_last_commit: int
    uncommitted_lines: int
    uncommitted_files: int
    branch_name: str
    status: Status

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "minutes_since_last_commit": self.minutes_since_last_commit,
            "uncommitted_lines": self.uncommitted_lines,
            "uncommitted_files": self.uncommitted_files,
            "branch_name": self.branch_name,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FlowState":
        """Create FlowState from dictionary."""
        return cls(
            minutes_since_last_commit=data["minutes_since_last_commit"],
            uncommitted_lines=data["uncommitted_lines"],
            uncommitted_files=data["uncommitted_files"],
            branch_name=data["branch_name"],
            status=Status(data["status"]),
        )
