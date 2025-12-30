"""Intent Validation Layer - Ticket-to-diff alignment.

Validates that code changes align with the stated task requirements
by fetching issues from GitHub and comparing them semantically.
"""

import os
import re
import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Any
from git import Repo

from flowcheck.semantic.indexer import SimpleVectorizer
from flowcheck.llm import get_llm_client, INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT_TEMPLATE
from flowcheck.guardian.sanitizer import Sanitizer
from flowcheck.config.loader import load_config


@dataclass
class IntentValidationResult:
    """Result of validating diff against ticket intent."""

    alignment_score: float  # 0.0 to 1.0
    ticket_id: Optional[str] = None
    ticket_summary: str = ""
    missing_criteria: list[str] = field(default_factory=list)
    scope_creep_warnings: list[str] = field(default_factory=list)
    is_aligned: bool = True
    reasoning: str = ""  # New in v0.2 for LLM explanation

    def to_dict(self) -> dict:
        return {
            "alignment_score": round(self.alignment_score, 2),
            "ticket_id": self.ticket_id,
            "ticket_summary": self.ticket_summary,
            "missing_criteria": self.missing_criteria,
            "scope_creep_warnings": self.scope_creep_warnings,
            "is_aligned": self.is_aligned,
            "reasoning": self.reasoning,
        }


class IntentValidator:
    """Validates code changes against GitHub issues."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        config: dict[str, Any] = None,
    ):
        """Initialize intent validator.

        Args:
            github_token: GitHub Personal Access Token (defaults to GITHUB_TOKEN env var).
            config: FlowCheck configuration dictionary.
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.vectorizer = SimpleVectorizer()
        self.config = config or {}
        self.llm_client = get_llm_client(self.config)
        self.sanitizer = Sanitizer()

    def _get_github_repo(self, repo_path: str) -> Optional[str]:
        """Extract owner/repo from git remotes."""
        try:
            repo = Repo(repo_path, search_parent_directories=True)
            for remote in repo.remotes:
                url = remote.url
                # Matches patterns like git@github.com:owner/repo.git or https://github.com/owner/repo.git
                match = re.search(r"github\.com[:/](.+?/.+?)(\.git)?$", url)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None

    def _fetch_github_issue(self, repo_full_name: str, issue_id: str) -> Optional[dict]:
        """Fetch issue details from GitHub API."""
        url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_id}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FlowCheck-MCP",
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            # Silently fail for v0.1, returning None
            return None

    def _validate_with_llm(
        self,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        diff_content: str
    ) -> IntentValidationResult:
        """Validate intent using LLM."""
        # 1. Sanitize the diff to prevent PII/Secrets leaking to LLM
        sanitized_result = self.sanitizer.sanitize(diff_content)
        safe_diff = sanitized_result.sanitized_text

        # Truncate diff if too long (simple char limit for now ~12k chars)
        if len(safe_diff) > 12000:
            safe_diff = safe_diff[:12000] + "\n...[TRUNCATED]"

        # 2. Construct Prompt
        prompt = INTENT_USER_PROMPT_TEMPLATE.format(
            ticket_title=ticket_title,
            ticket_body=ticket_body,
            # Could be improved
            diff_stat="[Diff stats not available in this context]",
            diff_content=safe_diff
        )

        try:
            # 3. Call LLM
            response = self.llm_client.complete(
                prompt, system_prompt=INTENT_SYSTEM_PROMPT)

            # 4. Parse Response
            is_aligned = response.get("aligned", True)
            is_scope_creep = response.get("scope_creep", False)
            reason = response.get("reason", "No reason provided.")

            warnings = []
            if is_scope_creep:
                warnings.append("Scope Creep Detected by AI Judge")

            return IntentValidationResult(
                alignment_score=1.0 if is_aligned else 0.4,
                ticket_id=ticket_id,
                ticket_summary=ticket_title,
                scope_creep_warnings=warnings,
                is_aligned=is_aligned,
                reasoning=reason
            )
        except Exception as e:
            # Fallback to local heuristic if LLM fails
            return None

    def validate(
        self,
        ticket_id: str,
        diff_content: str,
        repo_path: str,
    ) -> IntentValidationResult:
        """Validate diff against GitHub issue.

        Args:
            ticket_id: The issue ID (e.g., "42").
            diff_content: The current git diff.
            repo_path: Path to the local repository.

        Returns:
            IntentValidationResult with alignment analysis.
        """
        if not ticket_id:
            return IntentValidationResult(
                alignment_score=0.0,
                is_aligned=False,
                missing_criteria=["No ticket ID provided"],
            )

        # 1. Discover repo
        repo_name = self._get_github_repo(repo_path)
        issue_data = None
        if repo_name:
            issue_data = self._fetch_github_issue(repo_name, ticket_id)

        if not issue_data:
            return IntentValidationResult(
                alignment_score=0.5,  # Uncertain
                ticket_id=ticket_id,
                ticket_summary=f"Issue #{ticket_id} (Data not fetched)",
                scope_creep_warnings=[
                    "Could not fetch GitHub issue data. Check GITHUB_TOKEN."],
                is_aligned=True,
            )

        # 2. Extract context
        issue_body = issue_data.get("body") or ""
        issue_title = issue_data.get("title") or ""

        # --- LLM PATH ---
        if self.llm_client:
            llm_result = self._validate_with_llm(
                ticket_id, issue_title, issue_body, diff_content)
            if llm_result:
                return llm_result
        # ----------------

        # --- LOCAL FALLBACK PATH (TF-IDF) ---
        combined_context = f"{issue_title} {issue_body}"

        # 3. Semantic comparison
        self.vectorizer.fit([combined_context, diff_content])
        v1 = self.vectorizer.transform(combined_context)
        v2 = self.vectorizer.transform(diff_content)

        # Cosine similarity
        score = sum(a * b for a, b in zip(v1, v2))

        # Basic pattern matching for scope creep
        warnings = []
        scope_patterns = [
            ("refactor", "Refactoring detected - ensure this is in scope"),
            ("cleanup", "Code cleanup - confirm this is approved work"),
        ]
        diff_lower = diff_content.lower()
        for pattern, warning in scope_patterns:
            if pattern in diff_lower and pattern not in combined_context.lower():
                warnings.append(warning)

        return IntentValidationResult(
            alignment_score=score,
            ticket_id=ticket_id,
            ticket_summary=issue_title,
            scope_creep_warnings=warnings,
            is_aligned=score >= 0.3 or not warnings,  # Lower threshold for v0.1
        )


def verify_intent(
    ticket_id: str,
    repo_path: str,
    diff_content: Optional[str] = None,
) -> dict:
    """Convenience function for MCP tool.

    Args:
        ticket_id: The ticket/issue ID.
        repo_path: Path to the repository.
        diff_content: Optional diff override.

    Returns:
        Dictionary with alignment analysis.
    """
    if not diff_content:
        try:
            repo = Repo(repo_path, search_parent_directories=True)
            diff_content = repo.git.diff()
        except Exception:
            diff_content = ""

    # Load config for this repo (allows project-level LLM overrides)
    config = load_config(repo_path=repo_path)

    validator = IntentValidator(config=config)
    result = validator.validate(ticket_id, diff_content, repo_path)
    return result.to_dict()
