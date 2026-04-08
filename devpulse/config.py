import os
import yaml
from pathlib import Path

class Config:
    def __init__(self):
        self.home_dir = Path.home() / ".devpulse"
        self.config_path = self.home_dir / "config.yaml"
        self.db_path = self.home_dir / "devpulse.db"
        self.save_dir = self.home_dir / "saved"
        
        self._ensure_dirs()
        self.data = self._load_config()

    def _ensure_dirs(self):
        self.home_dir.mkdir(exist_ok=True)
        self.save_dir.mkdir(exist_ok=True)
        if not self.config_path.exists():
            default_config = Path(__file__).parent / "config.yaml"
            if default_config.exists():
                with open(default_config, "r") as f:
                    content = f.read()
                with open(self.config_path, "w") as f:
                    f.write(content)

    def _load_config(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def get(self, key, default=None):
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

config = Config()
