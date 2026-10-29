"""Runs a PowerShell script and returns its text output."""

import logging
import subprocess

from pc_checkup.sources.base import SourceError

logger = logging.getLogger(__name__)

# Forces UTF-8 output so accents survive whatever the console code page is.
UTF8_PREFIX = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"


def run_powershell(script: str, timeout: int = 60) -> str:
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", UTF8_PREFIX + script]
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        raise SourceError(f"PowerShell did not finish within {timeout}s") from error
    except OSError as error:
        raise SourceError("PowerShell could not be started") from error
    if result.returncode != 0:
        logger.error("PowerShell stderr: %s", result.stderr.decode("utf-8", errors="replace"))
        raise SourceError(f"PowerShell exited with code {result.returncode}")
    return result.stdout.decode("utf-8-sig", errors="replace")
