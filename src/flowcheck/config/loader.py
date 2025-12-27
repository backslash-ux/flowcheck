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


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load configuration from file.

    If the config file doesn't exist, creates it with default values.

    Args:
        config_path: Optional custom path to config file.

    Returns:
        Dictionary with configuration values.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        # Create default config
        config = get_default_config()
        save_config(config, path)
        return config

    try:
        with open(path, "r") as f:
            user_config = json.load(f)

        # Merge with defaults to ensure all keys exist
        config = get_default_config()
        config.update(user_config)
        return config

    except (json.JSONDecodeError, IOError) as e:
        # Return defaults on error
        return get_default_config()


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
