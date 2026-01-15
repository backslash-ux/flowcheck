"""Tests for FlowCheck CLI (v0.3)."""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from flowcheck.cli import (
    create_parser,
    cmd_check,
    cmd_index,
    main,
    EXIT_OK,
    EXIT_WARNING,
    EXIT_SECURITY,
    EXIT_ERROR,
)


class TestCLIParser(unittest.TestCase):
    """Test CLI argument parsing."""

    def test_check_command_default(self):
        parser = create_parser()
        args = parser.parse_args(["check"])
        self.assertEqual(args.command, "check")
        self.assertIsNone(args.repo_path)
        self.assertFalse(args.strict)

    def test_check_command_with_path(self):
        parser = create_parser()
        args = parser.parse_args(["check", "/path/to/repo"])
        self.assertEqual(args.repo_path, "/path/to/repo")

    def test_check_command_strict(self):
        parser = create_parser()
        args = parser.parse_args(["check", "--strict"])
        self.assertTrue(args.strict)

    def test_check_command_strict_short(self):
        parser = create_parser()
        args = parser.parse_args(["check", "-s"])
        self.assertTrue(args.strict)

    def test_index_command_default(self):
        parser = create_parser()
        args = parser.parse_args(["index"])
        self.assertEqual(args.command, "index")
        self.assertFalse(args.incremental)

    def test_index_command_incremental(self):
        parser = create_parser()
        args = parser.parse_args(["index", "--incremental"])
        self.assertTrue(args.incremental)

    def test_install_hooks_command(self):
        parser = create_parser()
        args = parser.parse_args(["install-hooks"])
        self.assertEqual(args.command, "install-hooks")

    def test_no_command_returns_none(self):
        parser = create_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)


class TestCheckCommand(unittest.TestCase):
    """Test the check command."""

    @patch("flowcheck.cli.analyze_repo")
    @patch("flowcheck.cli.load_config")
    @patch("flowcheck.cli.get_audit_logger")
    @patch("git.Repo")
    def test_check_ok_status(self, mock_repo, mock_logger, mock_config, mock_analyze):
        mock_config.return_value = {"max_minutes_without_commit": 60, "max_lines_uncommitted": 500}
        mock_analyze.return_value = {
            "minutes_since_last_commit": 10,
            "uncommitted_lines": 50,
            "uncommitted_files": 2,
            "branch_name": "main",
            "branch_age_days": 0,
            "behind_main_by_commits": 0,
        }
        mock_logger.return_value = MagicMock()

        parser = create_parser()
        args = parser.parse_args(["check", "."])
        
        exit_code = cmd_check(args)
        
        self.assertEqual(exit_code, EXIT_OK)

    @patch("flowcheck.cli.analyze_repo")
    @patch("flowcheck.cli.load_config")
    @patch("flowcheck.cli.get_audit_logger")
    @patch("git.Repo")
    def test_check_warning_status(self, mock_repo, mock_logger, mock_config, mock_analyze):
        mock_config.return_value = {"max_minutes_without_commit": 60, "max_lines_uncommitted": 500}
        mock_analyze.return_value = {
            "minutes_since_last_commit": 120,  # Exceeds threshold
            "uncommitted_lines": 50,
            "uncommitted_files": 2,
            "branch_name": "feature",
            "branch_age_days": 0,
            "behind_main_by_commits": 0,
        }
        mock_logger.return_value = MagicMock()

        parser = create_parser()
        args = parser.parse_args(["check", "."])
        
        exit_code = cmd_check(args)
        
        self.assertEqual(exit_code, EXIT_WARNING)


class TestMain(unittest.TestCase):
    """Test the main entry point."""

    def test_main_no_args_returns_ok(self):
        exit_code = main([])
        self.assertEqual(exit_code, EXIT_OK)

    @patch("flowcheck.cli.cmd_check")
    def test_main_routes_check_command(self, mock_cmd):
        mock_cmd.return_value = EXIT_OK
        exit_code = main(["check"])
        mock_cmd.assert_called_once()
        self.assertEqual(exit_code, EXIT_OK)


if __name__ == "__main__":
    unittest.main()
