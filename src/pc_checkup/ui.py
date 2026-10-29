"""Terminal look: bold options, separators and colored blocks (ANSI escape codes).

With color=False every helper returns the text unchanged, so output stays plain
when the terminal has no color support, output is redirected, or in tests.
"""

import ctypes
import os
import shutil
import sys
import textwrap
from typing import TextIO

from pc_checkup.models import Level

RESET = "\x1b[0m"
BOLD = "\x1b[1m"

# SGR codes: foreground;background (30-37 / 90-97 text, 40-47 / 100-107 background).
# None means plain text with no band.
LEVEL_STYLES: dict[Level, str | None] = {
    Level.INFO: None,
    Level.LOG: "30;47",
    Level.OK: "30;42",
    Level.ERROR: "1;97;41",
    Level.TECHNICAL: None,
}

MIN_WIDTH = 40
MAX_WIDTH = 100
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
STD_OUTPUT_HANDLE = -11


def _enable_windows_ansi() -> bool:
    """Turn on ANSI escape codes in the Windows console (off by default in older ones)."""
    if sys.platform != "win32":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except (AttributeError, OSError):
        return False


def supports_color(stream: TextIO | None = None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") or not stream.isatty():
        return False
    return _enable_windows_ansi()


class Ui:
    def __init__(self, color: bool = False, width: int | None = None) -> None:
        self.color = color
        # Leave one column free when detecting: filling the last one makes some consoles wrap.
        columns = width if width else shutil.get_terminal_size().columns - 1
        self.width = max(MIN_WIDTH, min(columns, MAX_WIDTH))

    def bold(self, text: str) -> str:
        return f"{BOLD}{text}{RESET}" if self.color else text

    def separator(self) -> str:
        return ("─" if self.color else "-") * self.width

    def option(self, choice: str, label: str) -> str:
        return f"{self.bold(choice + ')')} {label}"

    def block(self, text: str, level: Level = Level.INFO) -> str:
        """Text on a colored band as wide as the menu; long text wraps inside the band."""
        style = LEVEL_STYLES[level]
        if not self.color or style is None:
            return text
        inner = self.width - 2
        lines = textwrap.wrap(text, inner) or [""]
        return "\n".join(f"\x1b[{style}m {line.ljust(inner)} {RESET}" for line in lines)
