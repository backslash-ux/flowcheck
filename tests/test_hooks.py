"""Tests for FlowCheck git hooks (v0.3)."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowcheck.hooks.templates import get_pre_commit_hook, get_post_commit_hook
from flowcheck.hooks.installer import HookInstaller


class TestHookTemplates(unittest.TestCase):
    """Test hook template generation."""

    def test_pre_commit_hook_content(self):
        hook = get_pre_commit_hook()
        self.assertIn("#!/bin/sh", hook)
        self.assertIn("FlowCheck", hook)
        self.assertIn("flowcheck check --strict", hook)
        self.assertIn("FLOWCHECK_BYPASS", hook)

    def test_post_commit_hook_content(self):
        hook = get_post_commit_hook()
        self.assertIn("#!/bin/sh", hook)
        self.assertIn("FlowCheck", hook)
        self.assertIn("flowcheck index --incremental", hook)

    def test_pre_commit_bypass_logic(self):
        hook = get_pre_commit_hook()
        # Should check for bypass env var
        self.assertIn('FLOWCHECK_BYPASS', hook)
        self.assertIn('exit 0', hook)


class TestHookInstaller(unittest.TestCase):
    """Test hook installation."""

    def setUp(self):
        # Create a temp directory with a .git folder
        self.temp_dir = tempfile.mkdtemp()
        self.git_dir = Path(self.temp_dir) / ".git"
        self.git_dir.mkdir()
        self.hooks_dir = self.git_dir / "hooks"
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("flowcheck.hooks.installer.Repo")
    def test_installer_creates_hooks_dir(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        installer = HookInstaller(self.temp_dir)
        installer.install_pre_commit()

        self.assertTrue(self.hooks_dir.exists())

    @patch("flowcheck.hooks.installer.Repo")
    def test_install_pre_commit_creates_file(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        installer = HookInstaller(self.temp_dir)
        result = installer.install_pre_commit()

        self.assertTrue(result)
        hook_path = self.hooks_dir / "pre-commit"
        self.assertTrue(hook_path.exists())

    @patch("flowcheck.hooks.installer.Repo")
    def test_install_hook_is_executable(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        installer = HookInstaller(self.temp_dir)
        installer.install_pre_commit()

        hook_path = self.hooks_dir / "pre-commit"
        mode = hook_path.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)  # User execute

    @patch("flowcheck.hooks.installer.Repo")
    def test_install_all_hooks(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        installer = HookInstaller(self.temp_dir)
        results = installer.install_all()

        self.assertTrue(results["pre-commit"])
        self.assertTrue(results["post-commit"])

    @patch("flowcheck.hooks.installer.Repo")
    def test_is_installed_false_when_missing(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        installer = HookInstaller(self.temp_dir)
        
        self.assertFalse(installer.is_installed("pre-commit"))

    @patch("flowcheck.hooks.installer.Repo")
    def test_is_installed_true_after_install(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        installer = HookInstaller(self.temp_dir)
        installer.install_pre_commit()
        
        self.assertTrue(installer.is_installed("pre-commit"))

    @patch("flowcheck.hooks.installer.Repo")
    def test_backup_existing_hook(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo.git_dir = str(self.git_dir)
        mock_repo_class.return_value = mock_repo

        # Create hooks dir and existing hook
        self.hooks_dir.mkdir(exist_ok=True)
        existing_hook = self.hooks_dir / "pre-commit"
        existing_hook.write_text("#!/bin/sh\necho 'original'")

        installer = HookInstaller(self.temp_dir)
        installer.install_pre_commit()

        # Original should be backed up
        backup = self.hooks_dir / "pre-commit.backup"
        self.assertTrue(backup.exists())
        self.assertIn("original", backup.read_text())


if __name__ == "__main__":
    unittest.main()
