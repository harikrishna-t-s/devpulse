"""Configuration management module for DevPulse.

This module handles loading and accessing configuration from YAML files.
It supports:
- Hierarchical configuration access via dot notation
- Automatic directory creation
- Default configuration copying

Example:
    from devpulse.config import config
    timeout = config.get('timeout', 10)
    weights = config.get('scoring.weights', {})
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional


class Config:
    """Configuration manager for DevPulse.
    
    Manages configuration loading from YAML files and provides
    hierarchical access via dot notation. Automatically creates
    required directories and copies default configuration.
    
    Attributes:
        home_dir: Path to DevPulse home directory (~/.devpulse)
        config_path: Path to configuration file
        db_path: Path to SQLite database
        save_dir: Path to saved articles directory
        data: Loaded configuration dictionary
    
    Example:
        >>> config = Config()
        >>> timeout = config.get('timeout', 10)
        >>> print(timeout)
        10
    """
    
    def __init__(self) -> None:
        """Initialize configuration manager.
        
        Sets up paths, ensures directories exist, and loads
        configuration from YAML file.
        """
        self.home_dir = Path.home() / ".devpulse"
        self.config_path = self.home_dir / "config.yaml"
        self.db_path = self.home_dir / "devpulse.db"
        self.save_dir = self.home_dir / "saved"
        
        self._ensure_dirs()
        self.data = self._load_config()

    def _ensure_dirs(self) -> None:
        """Ensure required directories exist.
        
        Creates home and saved directories if they don't exist.
        Copies default config.yaml from package if user config
        doesn't exist.
        """
        self.home_dir.mkdir(exist_ok=True)
        self.save_dir.mkdir(exist_ok=True)
        if not self.config_path.exists():
            default_config = Path(__file__).parent / "config.yaml"
            if default_config.exists():
                with open(default_config, "r") as f:
                    content = f.read()
                with open(self.config_path, "w") as f:
                    f.write(content)

    def _load_config(self) -> dict:
        """Load configuration from YAML file.
        
        Returns:
            Configuration dictionary, or empty dict if file doesn't exist.
        """
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get nested configuration value by dot-notation key.
        
        Args:
            key: Dot-separated key path (e.g., 'scoring.threshold')
            default: Default value if key not found
        
        Returns:
            Configuration value or default if not found.
        
        Example:
            >>> config.get('scoring.threshold', 50)
            50
            >>> config.get('nlp.enabled', True)
            True
        """
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default


# Global configuration instance
config = Config()
