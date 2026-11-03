"""Sends technical logs to a file, so the terminal only shows friendly messages.

Without a handler, Python prints logged errors (with their tracebacks) straight to the
terminal. This installs a file handler on the package logger, which also keeps that from
happening. The file is %APPDATA%\\pc_checkup\\checkup.log and is rotated when it grows.
"""

import logging
import logging.handlers
import os
from pathlib import Path

from pc_checkup.config import default_config_path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
MAX_LOG_BYTES = 500_000
KEPT_OLD_LOGS = 2
DEBUG_VARIABLE = "PC_CHECKUP_DEBUG"
HANDLER_MARK = "_pc_checkup_handler"


def default_log_path() -> Path:
    return default_config_path().with_name("checkup.log")


def setup_logging(path: Path | None = None) -> Path | None:
    """Start logging to a file and return its path, or None if the file cannot be used.

    Calling it again replaces the previous handler instead of adding a second one.
    """
    path = path or default_log_path()
    logger = logging.getLogger("pc_checkup")
    logger.setLevel(logging.DEBUG if os.environ.get(DEBUG_VARIABLE) else logging.INFO)

    for old in [h for h in logger.handlers if getattr(h, HANDLER_MARK, False)]:
        logger.removeHandler(old)
        old.close()

    handler: logging.Handler
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=MAX_LOG_BYTES, backupCount=KEPT_OLD_LOGS, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        usable_path: Path | None = path
    except OSError:
        # No log file is better than a crash, and a handler still keeps errors off the screen.
        handler = logging.NullHandler()
        usable_path = None

    setattr(handler, HANDLER_MARK, True)
    logger.addHandler(handler)
    return usable_path
