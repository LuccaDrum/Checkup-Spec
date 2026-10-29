"""Administrator check and UAC relaunch (Windows only)."""

import ctypes
import logging
import subprocess
import sys
from collections.abc import Sequence

logger = logging.getLogger(__name__)

# ShellExecuteW returns a value greater than 32 on success.
SHELL_EXECUTE_SUCCESS_ABOVE = 32


def _user_is_admin() -> int:
    return ctypes.windll.shell32.IsUserAnAdmin()


def _shell_execute_runas(executable: str, params: str) -> int:
    return int(ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1))


def is_admin() -> bool:
    try:
        return bool(_user_is_admin())
    except (AttributeError, OSError):
        logger.exception("Could not determine admin status")
        return False


def relaunch_elevated(args: Sequence[str] | None = None) -> bool:
    """Start this program again with admin rights (shows the UAC prompt).

    Returns True if Windows launched the new process, False if the user
    declined the prompt or the launch failed.
    """
    extra = sys.argv[1:] if args is None else list(args)
    params = subprocess.list2cmdline(["-m", "pc_checkup", *extra])
    try:
        result = _shell_execute_runas(sys.executable, params)
    except (AttributeError, OSError):
        logger.exception("Could not relaunch with elevation")
        return False
    return result > SHELL_EXECUTE_SUCCESS_ABOVE
