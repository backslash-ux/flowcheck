"""Configuration loader for FlowCheck settings."""

import json
import os
from pathlib import Path
from typing import Any


# Default configuration path
DEFAULT_CONFIG_DIR = Path.home() / ".flowcheck"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"


def get_default_config() -> dict[str, Any]:
    """Get the default configuration values.

    Returns:
        Dictionary with default configuration.
    """
    return {
        "max_minutes_without_commit": 60,
        "max_lines_uncommitted": 500,
    }


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists.

    Returns:
        Path to the configuration directory.
    """
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def load_config_with_warnings(config_path: Path | str | None = None, repo_path: Path | str | None = None) -> tuple[dict[str, Any], list[str]]:
    """Load configuration with warnings for malformed files.

    Returns:
        Tuple of (config_dict, list_of_warning_strings)
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    warnings = []

    # 1. Defaults
    config = get_default_config()

    # 2. Global Config
    if not path.exists():
        save_config(config, path)
    else:
        try:
            with open(path, "r") as f:
                global_config = json.load(f)
                config.update(global_config)
        except json.JSONDecodeError as e:
            warnings.append(f"Global config malformed ({path}): {str(e)}")
        except IOError as e:
            warnings.append(f"Global config unreadable ({path}): {str(e)}")

    # 3. Repo Config
    if repo_path:
        repo_config_path = Path(repo_path) / ".flowcheck.json"
        if repo_config_path.exists():
            try:
                with open(repo_config_path, "r") as f:
                    repo_config = json.load(f)
                    config.update(repo_config)
            except json.JSONDecodeError as e:
                warnings.append(
                    f"Repo config malformed ({repo_config_path}): {str(e)}")
            except IOError as e:
                warnings.append(
                    f"Repo config unreadable ({repo_config_path}): {str(e)}")

    return config, warnings


def load_config(config_path: Path | str | None = None, repo_path: Path | str | None = None) -> dict[str, Any]:
    """Load configuration from file (Backwards compatibility wrapper)."""
    config, _ = load_config_with_warnings(config_path, repo_path)
    return config


def save_config(config: dict[str, Any], config_path: Path | str | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save.
        config_path: Optional custom path to config file.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def update_config(updates: dict[str, Any], config_path: Path | str | None = None) -> dict[str, Any]:
    """Update specific configuration values.

    Args:
        updates: Dictionary of configuration values to update.
        config_path: Optional custom path to config file.

    Returns:
        Updated configuration dictionary.
    """
    config = load_config(config_path)
    config.update(updates)
    save_config(config, config_path)
    return config
