"""Tests for the Git analyzer module."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import Repo

from flowcheck.core.git_analyzer import (
    analyze_repo,
    get_current_branch,
    get_minutes_since_last_commit,
    get_uncommitted_stats,
    get_repo,
    NotAGitRepositoryError,
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary Git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)

        # Create initial commit
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Initial content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        yield tmpdir, repo


@pytest.fixture
def temp_non_git_dir():
    """Create a temporary directory that is not a Git repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestGetRepo:
    """Tests for get_repo function."""

    def test_valid_git_repo(self, temp_git_repo):
        """Test that a valid Git repo is returned."""
        tmpdir, _ = temp_git_repo
        repo = get_repo(tmpdir)
        assert repo is not None

    def test_non_git_directory_raises(self, temp_non_git_dir):
        """Test that non-Git directory raises error."""
        with pytest.raises(NotAGitRepositoryError):
            get_repo(temp_non_git_dir)

    def test_nonexistent_path_raises(self):
        """Test that nonexistent path raises error."""
        with pytest.raises(NotAGitRepositoryError):
            get_repo("/nonexistent/path/to/nowhere")


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_returns_main_branch(self, temp_git_repo):
        """Test that default branch is returned."""
        tmpdir, repo = temp_git_repo
        branch = get_current_branch(repo)
        # Git default branch could be 'main' or 'master'
        assert branch in ["main", "master"]

    def test_returns_feature_branch(self, temp_git_repo):
        """Test that feature branch name is returned."""
        tmpdir, repo = temp_git_repo
        repo.create_head("feature/test-branch")
        repo.heads["feature/test-branch"].checkout()

        branch = get_current_branch(repo)
        assert branch == "feature/test-branch"


class TestGetMinutesSinceLastCommit:
    """Tests for get_minutes_since_last_commit function."""

    def test_recent_commit(self, temp_git_repo):
        """Test that a recent commit returns low minutes."""
        _, repo = temp_git_repo
        minutes = get_minutes_since_last_commit(repo)
        # Should be very recent (less than 1 minute)
        assert minutes <= 1

    def test_empty_repo_returns_zero(self, temp_non_git_dir):
        """Test that empty repo returns 0."""
        # Create a new empty repo
        repo = Repo.init(temp_non_git_dir)
        minutes = get_minutes_since_last_commit(repo)
        assert minutes == 0


class TestGetUncommittedStats:
    """Tests for get_uncommitted_stats function."""

    def test_clean_repo(self, temp_git_repo):
        """Test that clean repo has no uncommitted changes."""
        _, repo = temp_git_repo
        files, lines = get_uncommitted_stats(repo)
        assert files == 0
        assert lines == 0

    def test_modified_file(self, temp_git_repo):
        """Test that modified files are counted."""
        tmpdir, repo = temp_git_repo

        # Modify the test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Modified content\nWith more lines")

        files, lines = get_uncommitted_stats(repo)
        assert files >= 1

    def test_new_untracked_file(self, temp_git_repo):
        """Test that untracked files are counted."""
        tmpdir, repo = temp_git_repo

        # Create a new untracked file
        new_file = Path(tmpdir) / "new_file.txt"
        new_file.write_text("New content")

        files, lines = get_uncommitted_stats(repo)
        assert files >= 1


class TestAnalyzeRepo:
    """Tests for analyze_repo function."""

    def test_returns_all_metrics(self, temp_git_repo):
        """Test that all expected metrics are returned."""
        tmpdir, _ = temp_git_repo
        result = analyze_repo(tmpdir)

        assert "branch_name" in result
        assert "minutes_since_last_commit" in result
        assert "uncommitted_files" in result
        assert "uncommitted_lines" in result

    def test_invalid_path_raises(self, temp_non_git_dir):
        """Test that invalid path raises error."""
        with pytest.raises(NotAGitRepositoryError):
            analyze_repo(temp_non_git_dir)
