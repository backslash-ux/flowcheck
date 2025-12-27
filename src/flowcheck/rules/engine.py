"""Rules engine for generating flow health recommendations."""

from typing import Any

from ..core.models import FlowState, Status


def calculate_status(
    minutes_since_commit: int,
    uncommitted_lines: int,
    config: dict[str, Any],
) -> Status:
    """Calculate the overall flow health status.

    Args:
        minutes_since_commit: Minutes since the last commit.
        uncommitted_lines: Total lines changed but uncommitted.
        config: Configuration with threshold values.

    Returns:
        Status enum value (ok, warning, or danger).
    """
    max_minutes = config.get("max_minutes_without_commit", 60)
    max_lines = config.get("max_lines_uncommitted", 500)

    # Danger thresholds are 1.5x the warning thresholds
    danger_minutes = max_minutes * 1.5
    danger_lines = max_lines * 1.5

    # Check for danger conditions first
    if minutes_since_commit > danger_minutes or uncommitted_lines > danger_lines:
        return Status.DANGER

    # Check for warning conditions
    if minutes_since_commit > max_minutes or uncommitted_lines > max_lines:
        return Status.WARNING

    return Status.OK


def generate_recommendations(
    flow_state: FlowState,
    config: dict[str, Any],
) -> list[str]:
    """Generate human-readable recommendations based on flow state.

    Args:
        flow_state: Current flow state object.
        config: Configuration with threshold values.

    Returns:
        List of recommendation strings.
    """
    recommendations = []

    max_minutes = config.get("max_minutes_without_commit", 60)
    max_lines = config.get("max_lines_uncommitted", 500)

    # Time-based nudge
    if flow_state.minutes_since_last_commit > max_minutes:
        hours = flow_state.minutes_since_last_commit // 60
        mins = flow_state.minutes_since_last_commit % 60

        if hours > 0:
            time_str = f"{hours}h {mins}m"
        else:
            time_str = f"{mins} minutes"

        recommendations.append(
            f"⏰ You've been working for {time_str} without a commit. "
            f"Consider making a checkpoint commit to save your progress."
        )

    # Diff-size nudge
    if flow_state.uncommitted_lines > max_lines:
        recommendations.append(
            f"📊 You have {flow_state.uncommitted_lines} uncommitted lines. "
            f"Consider splitting your work into smaller, focused commits to ease future review."
        )

        # Additional tip for very large diffs
        if flow_state.uncommitted_lines > max_lines * 2:
            recommendations.append(
                "💡 Tip: Large changesets can be split by domain (e.g., backend vs. frontend) "
                "or by feature to create a more readable git history."
            )

    # File count warning
    if flow_state.uncommitted_files > 10:
        recommendations.append(
            f"📁 You have changes in {flow_state.uncommitted_files} files. "
            f"Consider grouping related changes into separate commits."
        )

    # Branch age recommendation
    if flow_state.branch_age_days > 7:
        recommendations.append(
            f"🌿 This branch is {flow_state.branch_age_days} days old. "
            f"Consider finishing up or merging to avoid long-lived branches."
        )

    # Main branch sync recommendation
    if flow_state.behind_main_by_commits > 10:
        recommendations.append(
            f"🔄 You are behind main by {flow_state.behind_main_by_commits} commits. "
            f"Consider merging main into your branch to stay up to date and avoid conflicts."
        )

    # All good message
    if not recommendations:
        recommendations.append(
            "✅ Your flow state looks healthy! Keep up the good work."
        )

    return recommendations


def build_flow_state(
    raw_metrics: dict[str, Any],
    config: dict[str, Any],
) -> FlowState:
    """Build a FlowState object from raw metrics and config.

    Args:
        raw_metrics: Raw metrics from the git analyzer.
        config: Configuration with threshold values.

    Returns:
        Complete FlowState object with status calculated.
    """
    status = calculate_status(
        minutes_since_commit=raw_metrics["minutes_since_last_commit"],
        uncommitted_lines=raw_metrics["uncommitted_lines"],
        config=config,
    )

    return FlowState(
        minutes_since_last_commit=raw_metrics["minutes_since_last_commit"],
        uncommitted_lines=raw_metrics["uncommitted_lines"],
        uncommitted_files=raw_metrics["uncommitted_files"],
        branch_name=raw_metrics["branch_name"],
        status=status,
        branch_age_days=raw_metrics.get("branch_age_days", 0),
        behind_main_by_commits=raw_metrics.get("behind_main_by_commits", 0),
    )
