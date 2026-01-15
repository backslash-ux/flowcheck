"""Git hook installer for FlowCheck."""

import os
import stat
from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError

from .templates import get_pre_commit_hook, get_post_commit_hook


class HookInstaller:
    """Installs FlowCheck git hooks into a repository."""

    HOOK_MARKER = "# FlowCheck"

    def __init__(self, repo_path: str = "."):
        """Initialize hook installer.
        
        Args:
            repo_path: Path to the git repository.
        """
        self.repo_path = Path(repo_path).resolve()
        self._validate_repo()
        
    def _validate_repo(self):
        """Validate that repo_path is a valid git repository."""
        try:
            self.repo = Repo(self.repo_path, search_parent_directories=True)
            self.git_dir = Path(self.repo.git_dir)
            self.hooks_dir = self.git_dir / "hooks"
        except InvalidGitRepositoryError:
            raise ValueError(f"Not a valid git repository: {self.repo_path}")

    def _ensure_hooks_dir(self):
        """Ensure the hooks directory exists."""
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

    def _backup_existing_hook(self, hook_name: str) -> Optional[Path]:
        """Backup an existing hook if it exists and isn't ours.
        
        Returns:
            Path to backup file, or None if no backup needed.
        """
        hook_path = self.hooks_dir / hook_name
        
        if not hook_path.exists():
            return None
            
        # Check if it's our hook
        content = hook_path.read_text()
        if self.HOOK_MARKER in content:
            return None  # It's our hook, will be overwritten
            
        # Backup the existing hook
        backup_path = hook_path.with_suffix(".backup")
        counter = 1
        while backup_path.exists():
            backup_path = hook_path.with_suffix(f".backup.{counter}")
            counter += 1
            
        hook_path.rename(backup_path)
        return backup_path

    def _write_hook(self, hook_name: str, content: str) -> bool:
        """Write a hook script.
        
        Returns:
            True if successful, False otherwise.
        """
        self._ensure_hooks_dir()
        hook_path = self.hooks_dir / hook_name
        
        try:
            # Backup existing hook if needed
            backup = self._backup_existing_hook(hook_name)
            if backup:
                print(f"   📦 Backed up existing {hook_name} to {backup.name}")
            
            # Write the new hook
            hook_path.write_text(content)
            
            # Make executable
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            
            return True
        except Exception as e:
            print(f"   ❌ Failed to install {hook_name}: {e}")
            return False

    def install_pre_commit(self) -> bool:
        """Install the pre-commit hook.
        
        Returns:
            True if successful.
        """
        return self._write_hook("pre-commit", get_pre_commit_hook())

    def install_post_commit(self) -> bool:
        """Install the post-commit hook.
        
        Returns:
            True if successful.
        """
        return self._write_hook("post-commit", get_post_commit_hook())

    def install_all(self) -> dict[str, bool]:
        """Install all FlowCheck hooks.
        
        Returns:
            Dictionary of hook names to success status.
        """
        return {
            "pre-commit": self.install_pre_commit(),
            "post-commit": self.install_post_commit(),
        }

    def uninstall(self, hook_name: str) -> bool:
        """Uninstall a FlowCheck hook.
        
        Args:
            hook_name: Name of the hook to uninstall.
            
        Returns:
            True if successful.
        """
        hook_path = self.hooks_dir / hook_name
        
        if not hook_path.exists():
            return True
            
        # Only remove if it's our hook
        content = hook_path.read_text()
        if self.HOOK_MARKER not in content:
            print(f"   ⚠️ {hook_name} is not a FlowCheck hook, skipping")
            return False
            
        try:
            hook_path.unlink()
            
            # Restore backup if exists
            backup_path = hook_path.with_suffix(".backup")
            if backup_path.exists():
                backup_path.rename(hook_path)
                print(f"   📦 Restored original {hook_name} from backup")
                
            return True
        except Exception as e:
            print(f"   ❌ Failed to uninstall {hook_name}: {e}")
            return False

    def uninstall_all(self) -> dict[str, bool]:
        """Uninstall all FlowCheck hooks.
        
        Returns:
            Dictionary of hook names to success status.
        """
        return {
            "pre-commit": self.uninstall("pre-commit"),
            "post-commit": self.uninstall("post-commit"),
        }

    def is_installed(self, hook_name: str) -> bool:
        """Check if a FlowCheck hook is installed.
        
        Args:
            hook_name: Name of the hook to check.
            
        Returns:
            True if the hook is installed and is a FlowCheck hook.
        """
        hook_path = self.hooks_dir / hook_name
        
        if not hook_path.exists():
            return False
            
        content = hook_path.read_text()
        return self.HOOK_MARKER in content
