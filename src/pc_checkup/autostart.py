"""Opens the program once after the next login, using the Windows RunOnce registry key.

Windows runs a RunOnce entry a single time and deletes it by itself. The entry
lives in the current user's registry (HKCU), so it needs no extra rights.
"""

import subprocess
import sys
import winreg
from collections.abc import Sequence

RUN_ONCE_KEY = r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
VALUE_NAME = "PcCheckupAfterRamTest"


def build_command(args: Sequence[str]) -> str:
    """Command line that starts this program again, with the given arguments."""
    return subprocess.list2cmdline([sys.executable, "-m", "pc_checkup", *args])


def register_after_reboot(command: str) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_ONCE_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)


def unregister() -> None:
    """Remove the entry if it is still there (it is gone once Windows has run it)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_ONCE_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass
