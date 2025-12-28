"""Intent Validation Layer - Ticket-to-diff alignment.

This module validates that code changes align with the stated
ticket/task requirements. Currently a stub for v0.1 - will integrate
with Jira/Linear APIs in future versions.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IntentValidationResult:
    """Result of validating diff against ticket intent."""

    alignment_score: float  # 0.0 to 1.0
    ticket_id: Optional[str] = None
    ticket_summary: str = ""
    missing_criteria: list[str] = field(default_factory=list)
    scope_creep_warnings: list[str] = field(default_factory=list)
    is_aligned: bool = True

    def to_dict(self) -> dict:
        return {
            "alignment_score": round(self.alignment_score, 2),
            "ticket_id": self.ticket_id,
            "ticket_summary": self.ticket_summary,
            "missing_criteria": self.missing_criteria,
            "scope_creep_warnings": self.scope_creep_warnings,
            "is_aligned": self.is_aligned,
        }


class IntentValidator:
    """Validates code changes against ticket requirements.

    This is a stub implementation for v0.1. Future versions will:
    - Integrate with Jira API
    - Integrate with Linear API
    - Use embeddings to compare ticket description with diff
    """

    def __init__(
        self,
        jira_url: Optional[str] = None,
        linear_api_key: Optional[str] = None,
    ):
        """Initialize intent validator.

        Args:
            jira_url: Base URL for Jira instance (future).
            linear_api_key: API key for Linear (future).
        """
        self.jira_url = jira_url
        self.linear_api_key = linear_api_key
        self._enabled = bool(jira_url or linear_api_key)

    @property
    def enabled(self) -> bool:
        """Check if external integration is configured."""
        return self._enabled

    def validate(
        self,
        ticket_id: str,
        diff_content: str,
        context: Optional[str] = None,
    ) -> IntentValidationResult:
        """Validate diff against ticket requirements.

        v0.1 Stub: Returns a placeholder result. Full implementation
        will fetch ticket details and compare semantically.

        Args:
            ticket_id: The ticket/issue ID (e.g., "PROJ-123").
            diff_content: The diff or description of changes.
            context: Optional additional context.

        Returns:
            IntentValidationResult with alignment analysis.
        """
        # Stub implementation for v0.1
        # In production, this would:
        # 1. Fetch ticket from Jira/Linear
        # 2. Extract requirements/acceptance criteria
        # 3. Embed both ticket and diff
        # 4. Calculate semantic similarity
        # 5. Identify missing criteria

        if not ticket_id:
            return IntentValidationResult(
                alignment_score=0.0,
                is_aligned=False,
                missing_criteria=["No ticket ID provided"],
            )

        # Basic keyword-based heuristics for v0.1
        warnings = []
        missing = []

        # Check for common patterns that might indicate scope creep
        scope_patterns = [
            ("refactor", "Refactoring detected - ensure this is in scope"),
            ("optimization", "Optimization work - verify this is part of the ticket"),
            ("cleanup", "Code cleanup - confirm this is approved work"),
        ]

        diff_lower = (diff_content or "").lower()
        for pattern, warning in scope_patterns:
            if pattern in diff_lower:
                warnings.append(warning)

        # Calculate a simple score based on warnings
        # This is a placeholder - real implementation would use embeddings
        base_score = 0.75  # Optimistic default
        penalty = len(warnings) * 0.1
        score = max(0.0, min(1.0, base_score - penalty))

        return IntentValidationResult(
            alignment_score=score,
            ticket_id=ticket_id,
            ticket_summary=f"[Stub] Ticket {ticket_id} - Integration pending",
            missing_criteria=missing,
            scope_creep_warnings=warnings,
            is_aligned=score >= 0.5,
        )

    def get_ticket_summary(self, ticket_id: str) -> str:
        """Fetch ticket summary from external system.

        Stub for v0.1 - returns placeholder.
        """
        if not self._enabled:
            return f"[Integration not configured] {ticket_id}"

        # Future: API calls to Jira/Linear
        return f"[Stub] {ticket_id}"


def verify_intent(
    ticket_id: str,
    diff_content: str,
    context: Optional[str] = None,
) -> dict:
    """Convenience function for MCP tool.

    Args:
        ticket_id: The ticket/issue ID.
        diff_content: Description or content of changes.
        context: Optional additional context.

    Returns:
        Dictionary with alignment analysis.
    """
    validator = IntentValidator()
    result = validator.validate(ticket_id, diff_content, context)
    return result.to_dict()
