"""FlowCheck MCP Server.

A local MCP safety layer that provides non-blocking flow health nudges.
"""

from typing import Any

from fastmcp import FastMCP

from .core.git_analyzer import analyze_repo, NotAGitRepositoryError
from .config.loader import load_config, update_config
from .rules.engine import build_flow_state, generate_recommendations


# Create the MCP server
mcp = FastMCP(
    name="FlowCheck",
    instructions="""
    FlowCheck is a local "safety layer" for developer workflow hygiene.
    It monitors Git repositories and provides gentle nudges about:
    - Time since last commit
    - Size of uncommitted changes
    - Overall flow health status
    
    Use get_flow_state to check a repository's health metrics.
    Use get_recommendations for actionable suggestions.
    """,
)


@mcp.tool
def get_flow_state(repo_path: str) -> dict[str, Any]:
    """Get the current flow state metrics for a Git repository.

    Returns metrics about the repository's health including:
    - minutes_since_last_commit: Time elapsed since last commit
    - uncommitted_lines: Total lines changed (additions + deletions)
    - uncommitted_files: Number of modified files
    - branch_name: Current Git branch
    - status: Health indicator (ok, warning, danger)

    Args:
        repo_path: Path to the Git repository (absolute or relative).

    Returns:
        Dictionary containing flow state metrics.
    """
    try:
        config = load_config()
        raw_metrics = analyze_repo(repo_path)
        flow_state = build_flow_state(raw_metrics, config)
        return flow_state.to_dict()
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
    """Get actionable recommendations for improving flow health.

    Analyzes the repository and returns human-readable suggestions
    based on configured thresholds for commit frequency and change size.

    Args:
        repo_path: Path to the Git repository (absolute or relative).

    Returns:
        Dictionary containing:
        - recommendations: Array of suggestion strings
        - status: Current flow health status
    """
    try:
        config = load_config()
        raw_metrics = analyze_repo(repo_path)
        flow_state = build_flow_state(raw_metrics, config)
        recommendations = generate_recommendations(flow_state, config)

        return {
            "recommendations": recommendations,
            "status": flow_state.status.value,
            "summary": {
                "minutes_since_last_commit": flow_state.minutes_since_last_commit,
                "uncommitted_lines": flow_state.uncommitted_lines,
                "uncommitted_files": flow_state.uncommitted_files,
                "branch_name": flow_state.branch_name,
            }
        }
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

    Allows dynamic adjustment of the thresholds that trigger warnings.
    Changes are persisted to the config file (~/.flowcheck/config.json).

    Supported configuration parameters:
    - max_minutes_without_commit: Minutes before suggesting a checkpoint (default: 60)
    - max_lines_uncommitted: Lines before suggesting to split changes (default: 500)

    Args:
        config: Dictionary of configuration values to update.

    Returns:
        Dictionary containing the updated configuration.
    """
    try:
        # Validate config keys
        valid_keys = {"max_minutes_without_commit", "max_lines_uncommitted"}
        filtered_config = {k: v for k, v in config.items() if k in valid_keys}

        if not filtered_config:
            return {
                "error": "No valid configuration keys provided.",
                "valid_keys": list(valid_keys),
            }

        # Validate values are positive integers
        for key, value in filtered_config.items():
            if not isinstance(value, int) or value <= 0:
                return {
                    "error": f"Invalid value for {key}: must be a positive integer.",
                }

        updated = update_config(filtered_config)
        return {
            "success": True,
            "config": updated,
            "message": f"Updated {len(filtered_config)} configuration value(s).",
        }
    except Exception as e:
        return {
            "error": f"Failed to update configuration: {str(e)}",
        }


def main():
    """Entry point for running the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
