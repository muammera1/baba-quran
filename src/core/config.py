"""Configuration management for Baba Quran with zero-dependency fallback."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_env_file(filepath: str = ".env") -> None:
    """Simple .env parser using standard library."""
    p = Path(filepath)
    if not p.exists():
        return
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key not in os.environ:
                os.environ[key] = val


# Load .env file into environment
_load_env_file(".env")


@dataclass
class Settings:
    # WhatsApp Config
    WHATSAPP_GROUP_JID: str = field(default_factory=lambda: os.getenv("WHATSAPP_GROUP_JID", ""))
    WHATSAPP_SESSION_PATH: str = field(default_factory=lambda: os.getenv("WHATSAPP_SESSION_PATH", "data/session"))

    # Reading Config
    PAGES_PER_DAY: int = field(default_factory=lambda: int(os.getenv("PAGES_PER_DAY", "2")))
    POST_TIME: str = field(default_factory=lambda: os.getenv("POST_TIME", "07:00"))
    REMINDER_HOURS_AFTER_POST: int = field(default_factory=lambda: int(os.getenv("REMINDER_HOURS_AFTER_POST", "12")))
    TIMEZONE: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Asia/Riyadh"))

    # Paths
    DATABASE_PATH: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "data/db/baba_quran.db"))
    QURAN_PAGES_DIR: str = field(default_factory=lambda: os.getenv("QURAN_PAGES_DIR", "data/pages"))
    CONFIG_YAML_PATH: str = field(default_factory=lambda: os.getenv("CONFIG_YAML_PATH", "config/settings.yaml"))


def load_yaml_settings(yaml_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Loads YAML configuration file if PyYAML is available, or returns basic defaults."""
    path = Path(yaml_path)
    if not path.exists():
        return {}

    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Simple built-in fallback for Friday Surah Al-Kahf
        return {
            "special_schedules": [
                {
                    "id": "friday_kahf",
                    "enabled": True,
                    "trigger": "friday",
                    "surah_name": "Al-Kahf",
                    "surah_arabic": "سورة الكهف",
                    "page_start": 293,
                    "page_end": 304,
                    "advance_khatmah": False,
                }
            ],
            "templates": {}
        }


# Singleton instance
settings = Settings()
yaml_config = load_yaml_settings(settings.CONFIG_YAML_PATH)
