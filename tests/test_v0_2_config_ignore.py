"""Tests for v0.2 Configuration and Ignore features."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git import Repo

from flowcheck.config.loader import load_config
from flowcheck.core.git_analyzer import analyze_repo


class TestConfigurationAndIgnore(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the repo
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir)

        # Initialize git repo
        self.repo = Repo.init(self.test_dir)

        # Configure git user
        self.repo.config_writer().set_value("user", "name", "Test User").release()
        self.repo.config_writer().set_value("user", "email", "test@example.com").release()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_project_level_config_override(self):
        """Test that project-level config overrides global config."""

        # Create project config
        project_config = {
            "max_minutes_without_commit": 999,
            "max_lines_uncommitted": 1234
        }
        with open(self.repo_path / ".flowcheck.json", "w") as f:
            json.dump(project_config, f)

        # Mock global config to be different
        with patch("flowcheck.config.loader.get_default_config") as mock_defaults:
            mock_defaults.return_value = {
                "max_minutes_without_commit": 60,
                "max_lines_uncommitted": 500
            }

            # Load config pointing to this repo
            config = load_config(repo_path=self.repo_path)

            self.assertEqual(config["max_minutes_without_commit"], 999)
            self.assertEqual(config["max_lines_uncommitted"], 1234)

    def test_ignore_patterns(self):
        """Test that .flowcheckignore patterns affect invalidation."""

        # Create .flowcheckignore
        with open(self.repo_path / ".flowcheckignore", "w") as f:
            f.write("ignored_file.txt\n")
            f.write("ignored_dir/\n")

        # Commit the ignore file so it's clean
        self.repo.index.add([".flowcheckignore"])
        self.repo.index.commit("Add ignore file")

        # Create a regular file (should be counted)
        with open(self.repo_path / "regular_file.txt", "w") as f:
            f.write("Some content")

        # Create an ignored file (should NOT be counted)
        with open(self.repo_path / "ignored_file.txt", "w") as f:
            f.write("Should be ignored\n" * 100)  # Many lines

        # Create an ignored directory and file (should NOT be counted)
        (self.repo_path / "ignored_dir").mkdir()
        with open(self.repo_path / "ignored_dir" / "nested.txt", "w") as f:
            f.write("Nested ignored")

        # Analyze repo
        metrics = analyze_repo(str(self.repo_path))

        # We expect:
        # uncommitted_files = 1 (regular_file.txt)
        # ignore_file.txt and ignored_dir/nested.txt should be excluded
        self.assertEqual(metrics["uncommitted_files"], 1)

        # Ensure we didn't count lines from ignored files
        # regular_file.txt has 0 lines (it's untracked/added but no newlines? "Some content" is 1 line if no newline?)
        # git diff --shortstat on untracked might act weirdly if not added?
        # Wait, git status --porcelain counts untracked files.
        # git diff --shortstat ignores untracked files until they are staged.

        # Update: get_uncommitted_stats logic:
        # Files: git status --porcelain (includes untracked)
        # Lines: git diff --shortstat (only tracked changes)

        # So ignored_file.txt is untracked. If we didn't exclude it, it would show up in files count.
        # But for lines count, we need to modify a tracked file to verify lines exclusion.

        # Let's commit regular file first
        self.repo.index.add(["regular_file.txt"])
        self.repo.index.commit("Add regular file")

        # Now modify it
        with open(self.repo_path / "regular_file.txt", "a") as f:
            f.write("\nNew line")

        # Modify ignored file (it's untracked so lines won't count anyway unless we stage it? No, if it's ignored via our mechanism, even if staged it should be ignored?)
        # Let's test that IgnoreManager passes exclude args to git status

        metrics = analyze_repo(str(self.repo_path))

        # uncommitted_files should be 1 (regular_file.txt modified).
        # ignored_file.txt is untracked AND ignored by .flowcheckignore.
        # If .flowcheckignore wasn't working, 'ignored_file.txt' would appear in `git status --porcelain`?
        # Wait, `ignored_file.txt` is NOT in `.gitignore`. So git sees it as untracked.
        # FlowCheck logic: git status --porcelain --untracked-files=all -- . :!ignored_file.txt
        # Should exclude it.

        self.assertEqual(metrics["uncommitted_files"], 1)


if __name__ == "__main__":
    unittest.main()
