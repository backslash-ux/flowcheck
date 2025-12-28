"""Unit tests for the Semantic Layer."""

import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from flowcheck.semantic.indexer import (
    CommitIndexer,
    IndexedCommit,
    SimpleVectorizer,
)
from flowcheck.semantic.search import SemanticSearch, SearchResult


class TestSimpleVectorizer:
    """Tests for the TF-IDF vectorizer."""

    def test_fit_builds_vocabulary(self):
        """Should build vocabulary from documents."""
        vectorizer = SimpleVectorizer(vocabulary_size=100)
        docs = [
            "fix bug in login authentication",
            "add new feature for user profile",
            "refactor database connection pool",
        ]

        vectorizer.fit(docs)

        assert vectorizer._fitted
        assert len(vectorizer.vocabulary) > 0
        assert "fix" in vectorizer.vocabulary or "bug" in vectorizer.vocabulary

    def test_transform_creates_vector(self):
        """Should transform text to vector."""
        vectorizer = SimpleVectorizer(vocabulary_size=50)
        docs = ["fix bug", "add feature", "update config"]
        vectorizer.fit(docs)

        vector = vectorizer.transform("fix bug in code")

        assert len(vector) == len(vectorizer.vocabulary)
        assert any(v > 0 for v in vector)

    def test_similar_documents_have_similar_vectors(self):
        """Similar documents should have similar vectors."""
        vectorizer = SimpleVectorizer(vocabulary_size=50)
        docs = [
            "fix authentication bug",
            "fix login error",
            "add new feature",
        ]
        vectorizer.fit(docs)

        vec1 = vectorizer.transform("fix auth bug")
        vec2 = vectorizer.transform("fix login bug")
        vec3 = vectorizer.transform("new feature added")

        # vec1 and vec2 should be more similar than vec1 and vec3
        sim12 = sum(a * b for a, b in zip(vec1, vec2))
        sim13 = sum(a * b for a, b in zip(vec1, vec3))

        assert sim12 > sim13

    def test_save_and_load_vocabulary(self):
        """Should save and load vocabulary."""
        vectorizer = SimpleVectorizer()
        vectorizer.fit(["test document", "another doc"])

        saved = vectorizer.save_vocabulary()

        new_vectorizer = SimpleVectorizer()
        new_vectorizer.load_vocabulary(saved)

        assert new_vectorizer._fitted
        assert new_vectorizer.vocabulary == vectorizer.vocabulary


class TestCommitIndexer:
    """Tests for commit indexer."""

    def test_creates_database(self):
        """Should create database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            indexer = CommitIndexer(db_path=db_path)

            assert db_path.exists()

    def test_get_indexed_count_empty(self):
        """Should return 0 for empty index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            indexer = CommitIndexer(db_path=db_path)

            count = indexer.get_indexed_count()

            assert count == 0


class TestIndexedCommit:
    """Tests for IndexedCommit."""

    def test_to_dict(self):
        """Should serialize correctly."""
        commit = IndexedCommit(
            commit_hash="abc123",
            message="Fix bug",
            author="Developer",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            files_changed=["file.py"],
        )

        data = commit.to_dict()

        assert data["commit_hash"] == "abc123"
        assert data["message"] == "Fix bug"
        assert data["author"] == "Developer"


class TestSemanticSearch:
    """Tests for semantic search."""

    def test_empty_search_returns_empty(self):
        """Should return empty list for empty index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            indexer = CommitIndexer(db_path=db_path)
            search = SemanticSearch(indexer)

            results = search.search("test query")

            assert results == []


class TestSearchResult:
    """Tests for SearchResult."""

    def test_to_dict(self):
        """Should serialize correctly."""
        commit = IndexedCommit(
            commit_hash="abc123",
            message="Fix bug",
            author="Dev",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        result = SearchResult(
            commit=commit,
            score=0.85,
            matched_terms=["fix", "bug"],
        )

        data = result.to_dict()

        assert data["commit_hash"] == "abc123"
        assert data["score"] == 0.85
        assert "fix" in data["matched_terms"]
