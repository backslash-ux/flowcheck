"""Data models for FlowCheck flow state."""

from dataclasses import dataclass, field
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
    branch_age_days: int = 0
    behind_main_by_commits: int = 0
    # v0.1 additions
    security_flags: list[str] = field(default_factory=list)
    ticket_alignment: float = 0.0  # 0.0-1.0, stub for v0.1
    rework_rate: float = 0.0  # 0.0-1.0, stub for v0.1

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "minutes_since_last_commit": self.minutes_since_last_commit,
            "uncommitted_lines": self.uncommitted_lines,
            "uncommitted_files": self.uncommitted_files,
            "branch_name": self.branch_name,
            "status": self.status.value,
            "branch_age_days": self.branch_age_days,
            "behind_main_by_commits": self.behind_main_by_commits,
            "security_flags": self.security_flags,
            "ticket_alignment": self.ticket_alignment,
            "rework_rate": self.rework_rate,
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
            branch_age_days=data.get("branch_age_days", 0),
            behind_main_by_commits=data.get("behind_main_by_commits", 0),
            security_flags=data.get("security_flags", []),
            ticket_alignment=data.get("ticket_alignment", 0.0),
            rework_rate=data.get("rework_rate", 0.0),
        )
