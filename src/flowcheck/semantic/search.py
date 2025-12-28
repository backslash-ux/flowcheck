"""Semantic search for commit history.

Provides semantic search over indexed commits using vector similarity.
"""

import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .indexer import CommitIndexer, IndexedCommit, SimpleVectorizer


@dataclass
class SearchResult:
    """A single search result with similarity score."""

    commit: IndexedCommit
    score: float  # 0.0 to 1.0 similarity
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "commit_hash": self.commit.commit_hash,
            "message": self.commit.message,
            "author": self.commit.author,
            "timestamp": self.commit.timestamp.isoformat(),
            "files_changed": self.commit.files_changed,
            "score": round(self.score, 3),
            "matched_terms": self.matched_terms,
        }


class SemanticSearch:
    """Semantic search engine for commit history.

    Uses cosine similarity between query vectors and indexed commit vectors
    to find semantically similar commits.
    """

    def __init__(self, indexer: Optional[CommitIndexer] = None):
        """Initialize semantic search.

        Args:
            indexer: CommitIndexer instance (creates default if not provided).
        """
        self.indexer = indexer or CommitIndexer()

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _get_matched_terms(self, query: str, commit: IndexedCommit) -> list[str]:
        """Find terms that appear in both query and commit."""
        query_terms = set(query.lower().split())
        commit_text = (commit.message + " " +
                       " ".join(commit.files_changed)).lower()

        matched = []
        for term in query_terms:
            if len(term) > 2 and term in commit_text:
                matched.append(term)

        return matched[:5]  # Limit to top 5

    def search(
        self,
        query: str,
        repo_path: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.1,
    ) -> list[SearchResult]:
        """Search for semantically similar commits.

        Args:
            query: Natural language search query.
            repo_path: Optional filter by repository path.
            top_k: Maximum number of results to return.
            min_score: Minimum similarity score threshold.

        Returns:
            List of SearchResult objects sorted by score (highest first).
        """
        # Get all indexed commits
        commits = self.indexer.get_all_commits(repo_path=repo_path, limit=1000)

        if not commits:
            return []

        # Vectorize query
        query_vector = self.indexer.vectorizer.transform(query)

        # Calculate similarities
        results: list[SearchResult] = []
        for commit in commits:
            if commit.vector:
                score = self._cosine_similarity(query_vector, commit.vector)

                # Boost score for exact term matches
                matched_terms = self._get_matched_terms(query, commit)
                if matched_terms:
                    score = min(1.0, score + len(matched_terms) * 0.1)

                if score >= min_score:
                    results.append(SearchResult(
                        commit=commit,
                        score=score,
                        matched_terms=matched_terms,
                    ))

        # Sort by score and return top-k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def find_similar_to_commit(
        self,
        commit_hash: str,
        repo_path: Optional[str] = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Find commits similar to a given commit.

        Args:
            commit_hash: Hash of the commit to find similar ones for.
            repo_path: Optional filter by repository.
            top_k: Maximum results to return.

        Returns:
            List of similar commits.
        """
        # Find the source commit
        commits = self.indexer.get_all_commits(repo_path=repo_path, limit=1000)
        source_commit = None

        for commit in commits:
            if commit.commit_hash.startswith(commit_hash[:7]):
                source_commit = commit
                break

        if not source_commit or not source_commit.vector:
            return []

        # Find similar commits
        results: list[SearchResult] = []
        for commit in commits:
            if commit.commit_hash == source_commit.commit_hash:
                continue  # Skip self

            if commit.vector:
                score = self._cosine_similarity(
                    source_commit.vector, commit.vector)
                if score > 0.1:
                    results.append(SearchResult(
                        commit=commit,
                        score=score,
                        matched_terms=[],
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def search_by_files(
        self,
        file_patterns: list[str],
        repo_path: Optional[str] = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Search for commits that modified specific files.

        Args:
            file_patterns: List of file name patterns to match.
            repo_path: Optional filter by repository.
            top_k: Maximum results.

        Returns:
            List of matching commits.
        """
        commits = self.indexer.get_all_commits(repo_path=repo_path, limit=1000)

        results: list[SearchResult] = []
        for commit in commits:
            matched_files = []
            for pattern in file_patterns:
                pattern_lower = pattern.lower()
                for file in commit.files_changed:
                    if pattern_lower in file.lower():
                        matched_files.append(file)

            if matched_files:
                # Score based on number of matched files
                score = min(1.0, len(matched_files) * 0.2)
                results.append(SearchResult(
                    commit=commit,
                    score=score,
                    matched_terms=matched_files[:5],
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


def search_history_semantically(
    query: str,
    repo_path: str,
    top_k: int = 5,
) -> list[dict]:
    """Convenience function for semantic history search.

    This is the main entry point for the MCP tool.

    Args:
        query: Natural language search query.
        repo_path: Path to the repository.
        top_k: Maximum results.

    Returns:
        List of result dictionaries.
    """
    indexer = CommitIndexer()

    # Check if repo is indexed, if not, index it
    if indexer.get_indexed_count(repo_path) == 0:
        indexer.index_repo(repo_path, max_commits=200)

    search = SemanticSearch(indexer)
    results = search.search(query, repo_path=repo_path, top_k=top_k)

    return [r.to_dict() for r in results]
