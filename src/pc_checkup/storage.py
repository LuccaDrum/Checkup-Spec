"""Small persistent state, kept next to the config in %APPDATA%\\pc_checkup\\state.json.

Right now it only remembers that a RAM test was started, so the next run knows
to look for its result.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from pc_checkup.config import default_config_path

logger = logging.getLogger(__name__)

PENDING_KEY = "ram_test_pending_since"


def default_state_path() -> Path:
    return default_config_path().with_name("state.json")


def load_pending_ram_test(path: Path | None = None) -> datetime | None:
    """When the pending RAM test was started, or None if there is none (or the file is unusable)."""
    path = path or default_state_path()
    try:
        when = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))[PENDING_KEY])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return when.astimezone() if when.tzinfo is None else when


def save_pending_ram_test(when: datetime, path: Path | None = None) -> None:
    path = path or default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({PENDING_KEY: when.isoformat()}, indent=2), encoding="utf-8")


def clear_pending_ram_test(path: Path | None = None) -> None:
    (path or default_state_path()).unlink(missing_ok=True)
