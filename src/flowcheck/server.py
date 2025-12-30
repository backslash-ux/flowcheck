"""FlowCheck MCP Server.

A production-grade MCP safety layer for AI-first development with:
- Git hygiene monitoring and nudges
- Security scanning (PII/secrets, injection detection)
- Semantic history search
- Intent validation
- Full observability (OTel traces, audit logs)
"""

from typing import Any, Optional

from fastmcp import FastMCP

from flowcheck.core.git_analyzer import analyze_repo, NotAGitRepositoryError
from flowcheck.config.loader import load_config, update_config
from flowcheck.rules.engine import build_flow_state, generate_recommendations
from flowcheck.guardian.sanitizer import Sanitizer
from flowcheck.guardian.injection_filter import InjectionFilter
from flowcheck.telemetry.audit_logger import get_audit_logger
from flowcheck.semantic.search import search_history_semantically
from flowcheck.intent import verify_intent as _verify_intent


# Initialize components
sanitizer = Sanitizer()
injection_filter = InjectionFilter()
audit_logger = get_audit_logger()


# Create the MCP server
mcp = FastMCP(
    name="FlowCheck",
    instructions="""
    FlowCheck is a production-grade "safety layer" for AI-first development.
    
    Core capabilities:
    - Git hygiene monitoring (commit frequency, change size)
    - Security scanning (PII/secrets detection, prompt injection filtering)
    - Semantic history search (find commits by meaning, not just keywords)
    - Intent validation (ticket-to-diff alignment)
    
    REQUIRED Usage:
    1. Call get_flow_state BEFORE starting any task
    2. If status is 'warning' or 'danger', address hygiene issues first
    3. NEVER include data flagged in security_flags in outputs
    4. Use search_history_semantically for historical context
    """,
)


def _apply_security_scan(diff_content: str) -> list[str]:
    """Apply security scans and return security flags."""
    flags = []

    # Check for secrets/PII
    if sanitizer.quick_check(diff_content):
        result = sanitizer.sanitize(diff_content)
        if result.secrets_detected:
            flags.append("⚠️ SECRETS: Potential secrets detected in diff")
        if result.pii_detected:
            flags.append("⚠️ PII: Personal information detected in diff")

    # Check for injection patterns
    injection_flags = injection_filter.get_security_flags(diff_content)
    flags.extend(injection_flags)

    return flags


@mcp.tool
def get_flow_state(repo_path: str) -> dict[str, Any]:
    """Get current flow state metrics with security scanning.

    Returns metrics about repository health including:
    - minutes_since_last_commit: Time elapsed since last commit
    - uncommitted_lines: Total lines changed
    - uncommitted_files: Number of modified files
    - branch_name: Current Git branch
    - status: Health indicator (ok, warning, danger)
    - security_flags: Any detected security issues

    Args:
        repo_path: Path to the Git repository.

    Returns:
        Dictionary containing flow state metrics.
    """
    try:
        config = load_config(repo_path=repo_path)
        raw_metrics = analyze_repo(repo_path)
        flow_state = build_flow_state(raw_metrics, config)

        # Apply security scanning to diff content
        try:
            from git import Repo
            repo = Repo(repo_path, search_parent_directories=True)
            diff_content = repo.git.diff()
            security_flags = _apply_security_scan(diff_content)
            flow_state.security_flags = security_flags
        except Exception:
            pass

        result = flow_state.to_dict()

        # Log to audit trail
        audit_logger.log_tool_call("get_flow_state", repo_path, result)

        return result
    except NotAGitRepositoryError as e:
        return {
            "error": str(e),
            "status": "error",
        }
    except Exception as e:
        return {
            "error": f"Failed to analyze repository: {str(e)}",
            "status": "error",
        }


@mcp.tool
def get_recommendations(repo_path: str) -> dict[str, Any]:
    """Get actionable recommendations with security awareness.

    Analyzes repository and returns suggestions based on:
    - Commit frequency and change size thresholds
    - Branch age and main-branch synchronization
    - Security scan results

    Args:
        repo_path: Path to the Git repository.

    Returns:
        Dictionary containing recommendations and status.
    """
    try:
        config = load_config(repo_path=repo_path)
        raw_metrics = analyze_repo(repo_path)
        flow_state = build_flow_state(raw_metrics, config)
        recommendations = generate_recommendations(flow_state, config)

        # Add security-related recommendations
        try:
            from git import Repo
            repo = Repo(repo_path, search_parent_directories=True)
            diff_content = repo.git.diff()
            security_flags = _apply_security_scan(diff_content)

            if security_flags:
                recommendations.insert(0,
                                       "🔒 SECURITY: Review security flags before committing. "
                                       "Sensitive data or injection patterns detected."
                                       )
                flow_state.security_flags = security_flags
        except Exception:
            pass

        result = {
            "recommendations": recommendations,
            "status": flow_state.status.value,
            "security_flags": flow_state.security_flags,
            "summary": {
                "minutes_since_last_commit": flow_state.minutes_since_last_commit,
                "uncommitted_lines": flow_state.uncommitted_lines,
                "uncommitted_files": flow_state.uncommitted_files,
                "branch_name": flow_state.branch_name,
            }
        }

        audit_logger.log_tool_call("get_recommendations", repo_path, result)
        return result

    except NotAGitRepositoryError as e:
        return {
            "error": str(e),
            "recommendations": ["Unable to analyze - not a valid Git repository."],
        }
    except Exception as e:
        return {
            "error": f"Failed to get recommendations: {str(e)}",
            "recommendations": [],
        }


@mcp.tool
def set_rules(config: dict[str, Any]) -> dict[str, Any]:
    """Update FlowCheck configuration thresholds.

    Supported parameters:
    - max_minutes_without_commit: Minutes before suggesting checkpoint (default: 60)
    - max_lines_uncommitted: Lines before suggesting split (default: 500)

    Args:
        config: Configuration values to update.

    Returns:
        Dictionary with updated configuration.
    """
    try:
        valid_keys = {"max_minutes_without_commit", "max_lines_uncommitted"}
        filtered_config = {k: v for k, v in config.items() if k in valid_keys}

        if not filtered_config:
            return {
                "error": "No valid configuration keys provided.",
                "valid_keys": list(valid_keys),
            }

        for key, value in filtered_config.items():
            if not isinstance(value, int) or value <= 0:
                return {
                    "error": f"Invalid value for {key}: must be a positive integer.",
                }

        updated = update_config(filtered_config)

        audit_logger.log(
            action="tool:set_rules",
            status="ok",
            config_updated=list(filtered_config.keys()),
        )

        return {
            "success": True,
            "config": updated,
            "message": f"Updated {len(filtered_config)} configuration value(s).",
        }
    except Exception as e:
        return {
            "error": f"Failed to update configuration: {str(e)}",
        }


@mcp.tool
def search_history(query: str, repo_path: str, top_k: int = 5) -> dict[str, Any]:
    """Search commit history semantically.

    Find commits by meaning rather than exact keyword matching.
    Example: "authentication changes" finds commits about OAuth, login, tokens.

    Args:
        query: Natural language search query.
        repo_path: Path to the Git repository.
        top_k: Maximum number of results (default: 5).

    Returns:
        Dictionary with matching commits and scores.
    """
    try:
        results = search_history_semantically(query, repo_path, top_k)

        response = {
            "query": query,
            "results": results,
            "count": len(results),
        }

        audit_logger.log(
            action="tool:search_history",
            repo_path=repo_path,
            query=query,
            result_count=len(results),
        )

        return response
    except Exception as e:
        return {
            "error": f"Failed to search history: {str(e)}",
            "results": [],
        }


@mcp.tool
def verify_intent(ticket_id: str, repo_path: str, context: str = "") -> dict[str, Any]:
    """Validate current work against ticket requirements.

    Checks if code changes align with the stated ticket/task.
    Flags scope creep using GitHub Issues integration.

    Args:
        ticket_id: The issue ID or ticket ID (e.g., "42").
        repo_path: Path to the local repository.
        context: Optional description of current changes.

    Returns:
        Dictionary with alignment score and warnings.
    """
    try:
        result = _verify_intent(ticket_id, repo_path, context)

        audit_logger.log(
            action="tool:verify_intent",
            ticket_id=ticket_id,
            repo_path=repo_path,
            alignment_score=result.get("alignment_score", 0),
            reasoning=result.get("reasoning", ""),
        )

        return result
    except Exception as e:
        return {
            "error": f"Failed to verify intent: {str(e)}",
            "alignment_score": 0,
        }


@mcp.tool
def sanitize_content(content: str) -> dict[str, Any]:
    """Sanitize content by redacting secrets and PII.

    Use this before including file contents in prompts or outputs.
    Replaces sensitive data with [REDACTED_TYPE] tokens.

    Args:
        content: Text content to sanitize.

    Returns:
        Dictionary with sanitized content and metadata.
    """
    try:
        result = sanitizer.sanitize(content)

        response = {
            "sanitized_text": result.sanitized_text,
            "pii_detected": result.pii_detected,
            "secrets_detected": result.secrets_detected,
            "redacted_count": len(result.redacted_items),
        }

        audit_logger.log(
            action="tool:sanitize_content",
            pii_detected=result.pii_detected,
            secrets_detected=result.secrets_detected,
            redacted_count=len(result.redacted_items),
        )

        return response
    except Exception as e:
        return {
            "error": f"Failed to sanitize content: {str(e)}",
        }


def main():
    """Entry point for running the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
