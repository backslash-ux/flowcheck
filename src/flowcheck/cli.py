"""FlowCheck CLI - Command-line interface for Git hygiene and security checks.

Usage:
    flowcheck check [repo_path] [--strict]  # Run health check
    flowcheck index [repo_path] [--incremental]  # Index commit history
    flowcheck install-hooks [repo_path]  # Install git hooks
    flowcheck --version  # Show version
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from flowcheck.core.git_analyzer import analyze_repo, NotAGitRepositoryError
from flowcheck.config.loader import load_config
from flowcheck.rules.engine import build_flow_state, generate_recommendations
from flowcheck.guardian import apply_security_scan
from flowcheck.telemetry.audit_logger import get_audit_logger


# Exit codes
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_SECURITY = 2
EXIT_ERROR = 3


def get_version() -> str:
    """Get FlowCheck version."""
    try:
        from importlib.metadata import version
        return version("flowcheck")
    except Exception:
        from flowcheck import __version__
        return __version__


def cmd_check(args: argparse.Namespace) -> int:
    """Run health check on a repository.

    Returns:
        Exit code (0=ok, 1=warning, 2=security issue, 3=error)
    """
    repo_path = args.repo_path or "."
    strict = args.strict

    try:
        # Analyze repository
        config = load_config(repo_path=repo_path)
        raw_metrics = analyze_repo(repo_path)
        flow_state = build_flow_state(raw_metrics, config)
        recommendations = generate_recommendations(flow_state, config)

        # Security scan
        security_flags = []
        try:
            from git import Repo
            repo = Repo(repo_path, search_parent_directories=True)
            diff_content = repo.git.diff()
            if diff_content:
                security_flags = apply_security_scan(diff_content)
        except Exception:
            pass

        # Print results
        print(f"\n{'='*50}")
        print(f"FlowCheck Health Report")
        print(f"{'='*50}\n")

        status_icons = {"ok": "✅", "warning": "⚠️", "danger": "🚨"}
        status_icon = status_icons.get(flow_state.status.value, "❓")

        print(f"Status: {status_icon} {flow_state.status.value.upper()}")
        print(f"Branch: {flow_state.branch_name}")
        print(
            f"Time since commit: {flow_state.minutes_since_last_commit} minutes")
        print(f"Uncommitted lines: {flow_state.uncommitted_lines}")
        print(f"Uncommitted files: {flow_state.uncommitted_files}")

        if flow_state.branch_age_days > 0:
            print(f"Branch age: {flow_state.branch_age_days} days")
        if flow_state.behind_main_by_commits > 0:
            print(f"Behind main: {flow_state.behind_main_by_commits} commits")

        # Security section
        if security_flags:
            print(f"\n{'='*50}")
            print("🔒 SECURITY FLAGS")
            print(f"{'='*50}")
            for flag in security_flags:
                print(f"  {flag}")

        # Recommendations
        if recommendations:
            print(f"\n{'='*50}")
            print("📋 RECOMMENDATIONS")
            print(f"{'='*50}")
            for rec in recommendations:
                print(f"  {rec}")

        print()

        # Log the check
        audit_logger = get_audit_logger()
        audit_logger.log(
            action="cli:check",
            repo_path=str(repo_path),
            status=flow_state.status.value,
            security_flags=len(security_flags),
        )

        # Determine exit code
        if security_flags:
            if strict:
                print("❌ BLOCKED: Security issues detected (--strict mode)")
            return EXIT_SECURITY

        if flow_state.status.value in ("warning", "danger"):
            if strict:
                print(f"⚠️ WARNING: Flow health is {flow_state.status.value}")
            return EXIT_WARNING

        return EXIT_OK

    except NotAGitRepositoryError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return EXIT_ERROR


def cmd_index(args: argparse.Namespace) -> int:
    """Index commit history for semantic search."""
    repo_path = args.repo_path or "."
    incremental = args.incremental

    try:
        from flowcheck.semantic.indexer import CommitIndexer

        print(f"📚 Indexing commits in {repo_path}...")

        indexer = CommitIndexer()

        if incremental:
            stats = indexer.index_incremental(repo_path)
        else:
            stats = indexer.index_repository(repo_path)

        print(f"✅ Indexed {stats.get('indexed_count', 0)} commits")
        if stats.get('skipped_count', 0) > 0:
            print(f"   Skipped {stats['skipped_count']} (already indexed)")

        # Log the indexing
        audit_logger = get_audit_logger()
        audit_logger.log(
            action="cli:index",
            repo_path=str(repo_path),
            indexed_count=stats.get('indexed_count', 0),
            incremental=incremental,
        )

        return EXIT_OK

    except NotAGitRepositoryError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return EXIT_ERROR


def cmd_install_hooks(args: argparse.Namespace) -> int:
    """Install git hooks for FlowCheck."""
    repo_path = args.repo_path or "."

    try:
        from flowcheck.hooks.installer import HookInstaller

        installer = HookInstaller(repo_path)

        print(f"🔧 Installing FlowCheck hooks in {repo_path}...")

        results = installer.install_all()

        for hook_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {hook_name}")

        if all(results.values()):
            print("\n✅ All hooks installed successfully!")
            print("   Commits will now be checked for security issues.")
        else:
            print("\n⚠️ Some hooks failed to install")
            return EXIT_WARNING

        # Log the installation
        audit_logger = get_audit_logger()
        audit_logger.log(
            action="cli:install-hooks",
            repo_path=str(repo_path),
            hooks_installed=list(results.keys()),
        )

        return EXIT_OK

    except NotAGitRepositoryError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return EXIT_ERROR


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="flowcheck",
        description="FlowCheck - Git hygiene and security for AI-first development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  flowcheck check                   # Check current directory
  flowcheck check /path/to/repo     # Check specific repo
  flowcheck check --strict          # Block on any issues
  flowcheck index                   # Full index of commit history
  flowcheck index --incremental     # Index only new commits
  flowcheck install-hooks           # Install pre-commit hooks
        """,
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"FlowCheck {get_version()}",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # check command
    check_parser = subparsers.add_parser(
        "check",
        help="Run health check and security scan",
    )
    check_parser.add_argument(
        "repo_path",
        nargs="?",
        default=None,
        help="Path to repository (default: current directory)",
    )
    check_parser.add_argument(
        "--strict", "-s",
        action="store_true",
        help="Exit with non-zero code on warnings",
    )

    # index command
    index_parser = subparsers.add_parser(
        "index",
        help="Index commit history for semantic search",
    )
    index_parser.add_argument(
        "repo_path",
        nargs="?",
        default=None,
        help="Path to repository (default: current directory)",
    )
    index_parser.add_argument(
        "--incremental", "-i",
        action="store_true",
        help="Only index new commits since last run",
    )

    # install-hooks command
    hooks_parser = subparsers.add_parser(
        "install-hooks",
        help="Install git hooks for automatic checks",
    )
    hooks_parser.add_argument(
        "repo_path",
        nargs="?",
        default=None,
        help="Path to repository (default: current directory)",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return EXIT_OK

    if args.command == "check":
        return cmd_check(args)
    elif args.command == "index":
        return cmd_index(args)
    elif args.command == "install-hooks":
        return cmd_install_hooks(args)
    else:
        parser.print_help()
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
