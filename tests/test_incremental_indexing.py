"""Tests for incremental commit indexing (v0.3)."""

import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowcheck.semantic.indexer import CommitIndexer, IndexedCommit


class TestIncrementalIndexing(unittest.TestCase):
    """Test incremental commit indexing."""

    def setUp(self):
        # Use a temp database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        self.indexer = CommitIndexer(db_path=self.db_path)

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_get_last_indexed_hash_empty(self):
        result = self.indexer.get_last_indexed_hash("/some/repo")
        self.assertIsNone(result)

    def test_is_commit_indexed_false(self):
        result = self.indexer.is_commit_indexed("abc123def456")
        self.assertFalse(result)

    def test_is_commit_indexed_true_after_insert(self):
        # Manually insert a commit
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO commits 
                (commit_hash, message, author, timestamp, files_changed, diff_summary, vector, repo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "abc123def456",
                "Test commit",
                "Author",
                datetime.now(timezone.utc).isoformat(),
                "[]",
                "+10/-5",
                None,
                "/some/repo",
            ))
            conn.commit()

        result = self.indexer.is_commit_indexed("abc123def456")
        self.assertTrue(result)

    @patch("git.Repo")
    def test_index_single_commit(self, mock_repo_class):
        # Mock the Repo and commit
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123def456789"
        mock_commit.message = "Test commit message"
        mock_commit.author.name = "Test Author"
        mock_commit.committed_date = datetime.now(timezone.utc).timestamp()
        mock_commit.stats.files.keys.return_value = ["file1.py", "file2.py"]
        mock_commit.stats.total = {"insertions": 10, "deletions": 5}

        mock_repo = MagicMock()
        mock_repo.commit.return_value = mock_commit
        mock_repo_class.return_value = mock_repo

        # Index the commit
        result = self.indexer.index_single_commit("/some/repo", "abc123def456789")

        self.assertTrue(result)
        self.assertTrue(self.indexer.is_commit_indexed("abc123def456789"))

    @patch("git.Repo")
    def test_index_single_commit_already_indexed(self, mock_repo_class):
        # Manually insert a commit
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO commits 
                (commit_hash, message, author, timestamp, files_changed, diff_summary, vector, repo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "abc123def456",
                "Test commit",
                "Author",
                datetime.now(timezone.utc).isoformat(),
                "[]",
                "+10/-5",
                None,
                "/some/repo",
            ))
            conn.commit()

        # Try to index again
        result = self.indexer.index_single_commit("/some/repo", "abc123def456789")

        self.assertFalse(result)  # Should skip

    @patch("git.Repo")
    def test_index_incremental(self, mock_repo_class):
        # Mock commits
        mock_commit1 = MagicMock()
        mock_commit1.hexsha = "aaa111222333"
        mock_commit1.message = "First commit"
        mock_commit1.author.name = "Author"
        mock_commit1.committed_date = datetime.now(timezone.utc).timestamp()
        mock_commit1.stats.files.keys.return_value = ["file.py"]
        mock_commit1.stats.total = {"insertions": 5, "deletions": 0}

        mock_commit2 = MagicMock()
        mock_commit2.hexsha = "bbb222333444"
        mock_commit2.message = "Second commit"
        mock_commit2.author.name = "Author"
        mock_commit2.committed_date = datetime.now(timezone.utc).timestamp()
        mock_commit2.stats.files.keys.return_value = ["other.py"]
        mock_commit2.stats.total = {"insertions": 3, "deletions": 2}

        mock_repo = MagicMock()
        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]
        mock_repo.commit.side_effect = lambda h: mock_commit1 if "aaa" in h else mock_commit2
        mock_repo_class.return_value = mock_repo

        # First indexing
        stats = self.indexer.index_incremental("/some/repo", max_commits=10)

        self.assertEqual(stats["indexed_count"], 2)
        self.assertEqual(stats["skipped_count"], 0)

        # Second indexing - should skip already indexed
        stats = self.indexer.index_incremental("/some/repo", max_commits=10)

        self.assertEqual(stats["indexed_count"], 0)
        self.assertEqual(stats["skipped_count"], 2)


class TestIndexRepository(unittest.TestCase):
    """Test full repository indexing."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        self.indexer = CommitIndexer(db_path=self.db_path)

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_index_repository_returns_stats(self):
        with patch.object(self.indexer, "index_repo", return_value=10):
            stats = self.indexer.index_repository("/some/repo")

        self.assertEqual(stats["indexed_count"], 10)
        self.assertEqual(stats["skipped_count"], 0)


if __name__ == "__main__":
    unittest.main()
