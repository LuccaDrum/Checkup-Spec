"""Helpers to run Windows tools: no shell, a timeout, careful decoding of their output."""

import ctypes
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

EXIT_CODE_MASK = 0xFFFFFFFF


def system32(name: str) -> str:
    return str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / name)


def _console_encoding() -> str:
    """The code page console tools write in (for example cp850 on Brazilian Windows)."""
    try:
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except (AttributeError, OSError):
        return "cp437"


def decode_output(data: bytes) -> str:
    """Decode tool output. SFC writes UTF-16, which shows up as bytes with nulls in them."""
    if b"\x00" in data:
        return data.decode("utf-16-le", errors="replace")
    try:
        return data.decode(_console_encoding())
    except (LookupError, UnicodeDecodeError):
        return data.decode("utf-8", errors="replace")


def run_tool(command: list[str], timeout: int) -> int:
    """Run a tool and return its exit code as an unsigned 32-bit number.

    Windows reports HRESULT failures as negative numbers in some places and as large
    positive ones in others; masking makes 0x800F081F look the same everywhere.
    The output is only logged: results are decided by the exit code, never by the text,
    because the text changes with the Windows language.
    """
    result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    logger.debug("%s output:\n%s", command[0], decode_output(result.stdout))
    return result.returncode & EXIT_CODE_MASK
