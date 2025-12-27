"""Git repository analyzer for extracting flow metrics."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError, NoSuchPathError
from git.exc import GitCommandError


class GitAnalyzerError(Exception):
    """Base exception for Git analyzer errors."""
    pass


class NotAGitRepositoryError(GitAnalyzerError):
    """Raised when the path is not a valid Git repository."""
    pass


def get_repo(repo_path: str) -> Repo:
    """Get a Git repository object from a path.

    Args:
        repo_path: Path to the Git repository.

    Returns:
        Git Repo object.

    Raises:
        NotAGitRepositoryError: If path is not a valid Git repository.
    """
    try:
        # Expand user home directory
        expanded_path = os.path.expanduser(repo_path)
        return Repo(expanded_path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        raise NotAGitRepositoryError(
            f"Not a valid Git repository: {repo_path}") from e


def get_current_branch(repo: Repo) -> str:
    """Get the name of the current Git branch.

    Args:
        repo: Git repository object.

    Returns:
        Current branch name, or 'HEAD' if in detached HEAD state.
    """
    try:
        return repo.active_branch.name
    except TypeError:
        # Detached HEAD state
        return "HEAD"


def get_minutes_since_last_commit(repo: Repo) -> int:
    """Calculate minutes elapsed since the last commit.

    Args:
        repo: Git repository object.

    Returns:
        Minutes since last commit, or 0 if no commits exist.
    """
    try:
        if not repo.head.is_valid():
            return 0

        last_commit = repo.head.commit
        commit_time = datetime.fromtimestamp(
            last_commit.committed_date, tz=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta = now - commit_time
        return int(delta.total_seconds() / 60)
    except (ValueError, GitCommandError, AttributeError):
        # No commits or detached HEAD with no history
        return 0


def get_branch_age_days(repo: Repo) -> int:
    """Calculate the age of the current branch in days.

    Age is measured from the first commit that is only in this branch.
    """
    try:
        # Get the timestamp of the very first commit in this branch
        commits = list(repo.iter_commits(
            rev=repo.active_branch.name, reverse=True, max_count=1))
        if not commits:
            return 0
        first_commit_date = commits[0].committed_date
        dt = datetime.fromtimestamp(first_commit_date, tz=timezone.utc)
        delta = datetime.now(tz=timezone.utc) - dt
        return max(0, delta.days)
    except Exception:
        return 0


def get_commits_behind_main(repo: Repo) -> int:
    """Check how many commits the current branch is behind 'main' or 'master'."""
    try:
        main_name = "main" if "main" in repo.heads else "master" if "master" in repo.heads else None
        if not main_name or repo.active_branch.name == main_name:
            return 0

        # Get merge-base
        base = repo.merge_base(repo.active_branch, repo.heads[main_name])
        if not base:
            return 0

        # Count commits on main after base
        behind = list(repo.iter_commits(f"{base[0]}..{main_name}"))
        return len(behind)
    except Exception:
        return 0


def get_uncommitted_stats(repo: Repo) -> tuple[int, int]:
    """Get statistics about uncommitted changes.

    Args:
        repo: Git repository object.

    Returns:
        Tuple of (uncommitted_files, uncommitted_lines).
    """
    try:
        # Get diff stats for working tree changes
        diff_index = repo.index.diff(None)  # Changes not staged
        diff_staged = repo.index.diff("HEAD")  # Staged changes

        # Count files
        changed_files = set()
        for diff in diff_index:
            changed_files.add(diff.a_path or diff.b_path)
        for diff in diff_staged:
            changed_files.add(diff.a_path or diff.b_path)

        # Add untracked files
        untracked = repo.untracked_files
        changed_files.update(untracked)

        uncommitted_files = len(changed_files)

        # Get line counts using git diff --shortstat
        try:
            # Staged changes
            staged_stat = repo.git.diff("--cached", "--shortstat")
            # Unstaged changes
            unstaged_stat = repo.git.diff("--shortstat")

            total_lines = 0
            for stat in [staged_stat, unstaged_stat]:
                if stat:
                    # Parse "X files changed, Y insertions(+), Z deletions(-)"
                    parts = stat.split(",")
                    for part in parts:
                        part = part.strip()
                        if "insertion" in part:
                            total_lines += int(part.split()[0])
                        elif "deletion" in part:
                            total_lines += int(part.split()[0])

            uncommitted_lines = total_lines
        except GitCommandError:
            uncommitted_lines = 0

        return uncommitted_files, uncommitted_lines

    except GitCommandError:
        return 0, 0


def analyze_repo(repo_path: str) -> dict:
    """Analyze a Git repository and return raw metrics.

    Args:
        repo_path: Path to the Git repository.

    Returns:
        Dictionary containing:
        - branch_name: Current branch name
        - minutes_since_last_commit: Minutes since last commit
        - uncommitted_files: Count of changed files
        - uncommitted_lines: Total lines changed
        - branch_age_days: Age of branch in days
        - behind_main_by_commits: Count of commits behind main

    Raises:
        NotAGitRepositoryError: If path is not a valid Git repository.
    """
    repo = get_repo(repo_path)

    branch_name = get_current_branch(repo)
    minutes_since_last_commit = get_minutes_since_last_commit(repo)
    uncommitted_files, uncommitted_lines = get_uncommitted_stats(repo)
    branch_age_days = get_branch_age_days(repo)
    behind_main_by_commits = get_commits_behind_main(repo)

    return {
        "branch_name": branch_name,
        "minutes_since_last_commit": minutes_since_last_commit,
        "uncommitted_files": uncommitted_files,
        "uncommitted_lines": uncommitted_lines,
        "branch_age_days": branch_age_days,
        "behind_main_by_commits": behind_main_by_commits,
    }
