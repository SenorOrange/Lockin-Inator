"""
Configuration management for Lockin-Inator PC.
"""
import json
import os
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".lockininator" / "pc_config.json"

DEFAULT_CONFIG = {
    "study_duration_minutes": 50,
    "break_duration_minutes": 10,
    "blocked_processes": [
        "claude.exe",
        "antigravity.exe",
        "code.exe"
    ],
    "blocked_sites": [
        "instagram.com",
        "youtube.com",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "reddit.com",
        "twitch.tv",
        "facebook.com",
        "netflix.com"
    ],
    "sound_enabled": True,
    "notifications_enabled": True,
    "auto_cycle": True,
    "emergency_delay_seconds": 10
}


class ConfigManager:
    def __init__(self, config_path=None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = dict(DEFAULT_CONFIG)
                    merged.update(data)
                    return merged
            except Exception:
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
