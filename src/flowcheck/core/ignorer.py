"""Module for handling file ignore patterns (.flowcheckignore)."""

from pathlib import Path
from typing import List


class IgnoreManager:
    """Manages ignore patterns for FlowCheck."""

    IGNORE_FILE = ".flowcheckignore"

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.ignore_patterns = self._load_patterns()

    def _load_patterns(self) -> List[str]:
        """Load patterns from .flowcheckignore file."""
        ignore_file = self.repo_path / self.IGNORE_FILE
        patterns = []

        if ignore_file.exists():
            try:
                with open(ignore_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
            except IOError:
                pass

        return patterns

    def get_git_exclude_args(self) -> List[str]:
        """Convert patterns to git exclude arguments (pathspec).

        Returns:
            List of strings like ':!pattern', ':!dir/**'
        """
        # Git pathspec magic signatures for exclusion
        return [f":!{p}" for p in self.ignore_patterns]
