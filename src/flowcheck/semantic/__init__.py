"""Semantic Layer - Vector indexing and search for FlowCheck.

This module provides semantic search capabilities for commit history
using local embeddings and vector storage.
"""

from .indexer import CommitIndexer, IndexedCommit
from .search import SemanticSearch, SearchResult

__all__ = [
    "CommitIndexer",
    "IndexedCommit",
    "SemanticSearch",
    "SearchResult",
]
