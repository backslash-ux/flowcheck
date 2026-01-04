"""Commit history indexer for semantic search.

Indexes git commit messages and diffs for semantic search using
simple TF-IDF vectorization (no external ML dependencies required).
"""

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from collections import Counter
import math


@dataclass
class IndexedCommit:
    """Represents an indexed commit."""

    commit_hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: list[str] = field(default_factory=list)
    diff_summary: str = ""
    vector: Optional[list[float]] = None

    def to_dict(self) -> dict:
        return {
            "commit_hash": self.commit_hash,
            "message": self.message,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "files_changed": self.files_changed,
            "diff_summary": self.diff_summary,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "IndexedCommit":
        """Create from database row."""
        return cls(
            commit_hash=row[0],
            message=row[1],
            author=row[2],
            timestamp=datetime.fromisoformat(row[3]),
            files_changed=json.loads(row[4]) if row[4] else [],
            diff_summary=row[5] or "",
            vector=json.loads(row[6]) if row[6] else None,
        )


class SimpleVectorizer:
    """Simple TF-IDF vectorizer for text.

    Uses a vocabulary-based approach that works without external ML libraries.
    This provides reasonable semantic matching for commit messages.
    """

    # Common technical terms to boost
    TECH_TERMS = {
        "fix", "bug", "feature", "refactor", "update", "add", "remove",
        "api", "test", "config", "security", "performance", "database",
        "auth", "login", "error", "exception", "cache", "async", "sync",
    }

    def __init__(self, vocabulary_size: int = 500):
        self.vocabulary_size = vocabulary_size
        self.vocabulary: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self._fitted = False

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        text = text.lower()
        # Split on non-alphanumeric, keep meaningful tokens
        tokens = re.findall(r'\b[a-z][a-z0-9_]{1,20}\b', text)
        return tokens

    def fit(self, documents: list[str]):
        """Fit vectorizer on documents to build vocabulary."""
        # Count term frequencies across all documents
        term_doc_count: Counter = Counter()
        all_terms: Counter = Counter()

        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                term_doc_count[token] += 1
            all_terms.update(self._tokenize(doc))

        # Build vocabulary from most common terms, prioritizing tech terms
        sorted_terms = sorted(
            all_terms.keys(),
            key=lambda t: (
                -3 if t in self.TECH_TERMS else 0,  # Boost tech terms
                -all_terms[t]  # Then by frequency
            )
        )

        self.vocabulary = {
            term: idx
            for idx, term in enumerate(sorted_terms[:self.vocabulary_size])
        }

        # Calculate IDF
        n_docs = len(documents)
        for term, count in term_doc_count.items():
            if term in self.vocabulary:
                self.idf[term] = math.log((n_docs + 1) / (count + 1)) + 1

        self._fitted = True

    def transform(self, text: str) -> list[float]:
        """Transform text to vector."""
        if not self._fitted:
            # Return empty vector if not fitted
            return [0.0] * self.vocabulary_size

        tokens = self._tokenize(text)
        tf: Counter = Counter(tokens)

        vector = [0.0] * len(self.vocabulary)
        for term, idx in self.vocabulary.items():
            if term in tf:
                # TF-IDF score
                vector[idx] = tf[term] * self.idf.get(term, 1.0)

        # Normalize
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector

    def save_vocabulary(self) -> dict:
        """Save vocabulary and IDF for persistence."""
        return {
            "vocabulary": self.vocabulary,
            "idf": self.idf,
            "fitted": self._fitted,
        }

    def load_vocabulary(self, data: dict):
        """Load vocabulary from saved data."""
        self.vocabulary = data.get("vocabulary", {})
        self.idf = data.get("idf", {})
        self._fitted = data.get("fitted", False)


class CommitIndexer:
    """Indexes git commits for semantic search.

    Stores indexed commits in SQLite for efficient retrieval.
    Uses TF-IDF vectorization for semantic matching.
    """

    DEFAULT_DB_PATH = Path.home() / ".flowcheck" / "semantic_index.db"

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the indexer.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.vectorizer = SimpleVectorizer()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    commit_hash TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    author TEXT,
                    timestamp TEXT NOT NULL,
                    files_changed TEXT,
                    diff_summary TEXT,
                    vector TEXT,
                    repo_path TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vectorizer_state (
                    id INTEGER PRIMARY KEY,
                    state TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON commits(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_repo ON commits(repo_path)
            """)
            conn.commit()

        # Load vectorizer state if exists
        self._load_vectorizer_state()

    def _load_vectorizer_state(self):
        """Load vectorizer state from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT state FROM vectorizer_state WHERE id = 1"
                ).fetchone()
                if row:
                    state = json.loads(row[0])
                    self.vectorizer.load_vocabulary(state)
        except Exception:
            pass

    def _save_vectorizer_state(self):
        """Save vectorizer state to database."""
        state = json.dumps(self.vectorizer.save_vocabulary())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vectorizer_state (id, state) VALUES (1, ?)",
                (state,)
            )
            conn.commit()

    def index_repo(self, repo_path: str, max_commits: int = 500) -> int:
        """Index commits from a git repository.

        Args:
            repo_path: Path to the git repository.
            max_commits: Maximum number of commits to index.

        Returns:
            Number of commits indexed.
        """
        from git import Repo

        repo = Repo(repo_path, search_parent_directories=True)
        commits_to_index: list[IndexedCommit] = []

        # Collect commits
        for commit in repo.iter_commits(max_count=max_commits):
            # Get files changed
            try:
                files = list(commit.stats.files.keys())[:20]  # Limit files
            except Exception:
                files = []

            # Get diff summary
            try:
                diff_stat = commit.stats.total
                diff_summary = f"+{diff_stat.get('insertions', 0)}/-{diff_stat.get('deletions', 0)}"
            except Exception:
                diff_summary = ""

            indexed = IndexedCommit(
                commit_hash=commit.hexsha[:12],
                message=commit.message.strip()[:500],  # Limit message length
                author=commit.author.name if commit.author else "Unknown",
                timestamp=datetime.fromtimestamp(
                    commit.committed_date, tz=timezone.utc),
                files_changed=files,
                diff_summary=diff_summary,
            )
            commits_to_index.append(indexed)

        if not commits_to_index:
            return 0

        # Fit vectorizer on commit messages
        messages = [c.message + " " +
                    " ".join(c.files_changed) for c in commits_to_index]
        self.vectorizer.fit(messages)

        # Vectorize commits
        for commit in commits_to_index:
            text = commit.message + " " + " ".join(commit.files_changed)
            commit.vector = self.vectorizer.transform(text)

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            for commit in commits_to_index:
                conn.execute("""
                    INSERT OR REPLACE INTO commits 
                    (commit_hash, message, author, timestamp, files_changed, diff_summary, vector, repo_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    commit.commit_hash,
                    commit.message,
                    commit.author,
                    commit.timestamp.isoformat(),
                    json.dumps(commit.files_changed),
                    commit.diff_summary,
                    json.dumps(commit.vector) if commit.vector else None,
                    str(repo_path),
                ))
            conn.commit()

        # Save vectorizer state
        self._save_vectorizer_state()

        return len(commits_to_index)

    def get_all_commits(self, repo_path: Optional[str] = None, limit: int = 100) -> list[IndexedCommit]:
        """Get all indexed commits.

        Args:
            repo_path: Optional filter by repo path.
            limit: Maximum number to return.

        Returns:
            List of indexed commits.
        """
        with sqlite3.connect(self.db_path) as conn:
            if repo_path:
                rows = conn.execute(
                    "SELECT commit_hash, message, author, timestamp, files_changed, diff_summary, vector FROM commits WHERE repo_path = ? ORDER BY timestamp DESC LIMIT ?",
                    (str(repo_path), limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT commit_hash, message, author, timestamp, files_changed, diff_summary, vector FROM commits ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()

        return [IndexedCommit.from_row(row) for row in rows]

    def get_indexed_count(self, repo_path: Optional[str] = None) -> int:
        """Get count of indexed commits."""
        with sqlite3.connect(self.db_path) as conn:
            if repo_path:
                row = conn.execute(
                    "SELECT COUNT(*) FROM commits WHERE repo_path = ?",
                    (str(repo_path),)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM commits").fetchone()
        return row[0] if row else 0

    def get_last_indexed_hash(self, repo_path: str) -> Optional[str]:
        """Get the hash of the most recently indexed commit for a repo.
        
        Args:
            repo_path: Path to the repository.
            
        Returns:
            Commit hash or None if no commits indexed.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT commit_hash FROM commits WHERE repo_path = ? ORDER BY timestamp DESC LIMIT 1",
                (str(repo_path),)
            ).fetchone()
        return row[0] if row else None

    def is_commit_indexed(self, commit_hash: str) -> bool:
        """Check if a commit is already indexed.
        
        Args:
            commit_hash: The commit hash (or prefix).
            
        Returns:
            True if the commit is indexed.
        """
        with sqlite3.connect(self.db_path) as conn:
            # Match by prefix (first 12 chars)
            short_hash = commit_hash[:12]
            row = conn.execute(
                "SELECT 1 FROM commits WHERE commit_hash = ?",
                (short_hash,)
            ).fetchone()
        return row is not None

    def index_single_commit(self, repo_path: str, commit_hash: str) -> bool:
        """Index a single commit.
        
        Args:
            repo_path: Path to the repository.
            commit_hash: The commit hash to index.
            
        Returns:
            True if indexed successfully.
        """
        from git import Repo

        if self.is_commit_indexed(commit_hash):
            return False  # Already indexed

        repo = Repo(repo_path, search_parent_directories=True)
        
        try:
            commit = repo.commit(commit_hash)
        except Exception:
            return False
            
        # Get files changed
        try:
            files = list(commit.stats.files.keys())[:20]
        except Exception:
            files = []

        # Get diff summary
        try:
            diff_stat = commit.stats.total
            diff_summary = f"+{diff_stat.get('insertions', 0)}/-{diff_stat.get('deletions', 0)}"
        except Exception:
            diff_summary = ""

        indexed = IndexedCommit(
            commit_hash=commit.hexsha[:12],
            message=commit.message.strip()[:500],
            author=commit.author.name if commit.author else "Unknown",
            timestamp=datetime.fromtimestamp(commit.committed_date, tz=timezone.utc),
            files_changed=files,
            diff_summary=diff_summary,
        )

        # Vectorize using existing vocabulary (if fitted)
        text = indexed.message + " " + " ".join(indexed.files_changed)
        if self.vectorizer._fitted:
            indexed.vector = self.vectorizer.transform(text)
        else:
            indexed.vector = None

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO commits 
                (commit_hash, message, author, timestamp, files_changed, diff_summary, vector, repo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                indexed.commit_hash,
                indexed.message,
                indexed.author,
                indexed.timestamp.isoformat(),
                json.dumps(indexed.files_changed),
                indexed.diff_summary,
                json.dumps(indexed.vector) if indexed.vector else None,
                str(repo_path),
            ))
            conn.commit()

        return True

    def index_incremental(self, repo_path: str, max_commits: int = 100) -> dict:
        """Index only new commits since last indexing.
        
        Args:
            repo_path: Path to the repository.
            max_commits: Maximum new commits to index.
            
        Returns:
            Dictionary with indexing statistics.
        """
        from git import Repo

        repo = Repo(repo_path, search_parent_directories=True)
        last_hash = self.get_last_indexed_hash(repo_path)
        
        indexed_count = 0
        skipped_count = 0
        commits_to_process = []

        # Collect new commits
        for commit in repo.iter_commits(max_count=max_commits):
            short_hash = commit.hexsha[:12]
            
            if self.is_commit_indexed(short_hash):
                skipped_count += 1
                continue
                
            commits_to_process.append(commit)

        if not commits_to_process:
            return {
                "indexed_count": 0,
                "skipped_count": skipped_count,
            }

        # Index new commits
        for commit in commits_to_process:
            if self.index_single_commit(repo_path, commit.hexsha):
                indexed_count += 1

        return {
            "indexed_count": indexed_count,
            "skipped_count": skipped_count,
        }

    def index_repository(self, repo_path: str, max_commits: int = 500) -> dict:
        """Index all commits from a repository (full reindex).
        
        This is an alias for index_repo that returns stats.
        
        Args:
            repo_path: Path to the repository.
            max_commits: Maximum commits to index.
            
        Returns:
            Dictionary with indexing statistics.
        """
        count = self.index_repo(repo_path, max_commits)
        return {
            "indexed_count": count,
            "skipped_count": 0,
        }

