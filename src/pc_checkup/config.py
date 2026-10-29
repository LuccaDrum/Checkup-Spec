"""Persistent settings, stored as JSON in %APPDATA%\\pc_checkup\\config.json.

Only the UI language is stored for now. Functions take an optional `path` so
tests can use a temporary file instead of the real user profile.
"""

import json
import logging
import os
from pathlib import Path

from pc_checkup.messages import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)


def default_config_path() -> Path:
    """Return the config file location (falls back to the home folder if APPDATA is unset)."""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    return root / "pc_checkup" / "config.json"


def load_language(path: Path | None = None) -> str:
    """Return the saved language, or the default if missing, unreadable or unsupported."""
    path = path or default_config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        language = data["language"]
    except (OSError, ValueError, KeyError, TypeError):
        # First run, a damaged file or a missing key: the program must still start.
        logger.info("No usable config at %s, using default language", path)
        return DEFAULT_LANGUAGE
    if language not in SUPPORTED_LANGUAGES:
        logger.warning("Unsupported language %r in config, using default", language)
        return DEFAULT_LANGUAGE
    return str(language)


def save_language(language: str, path: Path | None = None) -> None:
    """Save the language, creating the config folder if needed."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language!r}")
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"language": language}, indent=2), encoding="utf-8")
