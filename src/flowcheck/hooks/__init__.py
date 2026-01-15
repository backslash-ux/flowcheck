"""FlowCheck Git Hooks - Automatic enforcement of hygiene and security."""

from .installer import HookInstaller
from .templates import get_pre_commit_hook, get_post_commit_hook

__all__ = [
    "HookInstaller",
    "get_pre_commit_hook",
    "get_post_commit_hook",
]
