"""Reads crash-related events and dump files from the last few days."""

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pc_checkup.models import BsodSnapshot, EventKind, SystemEvent
from pc_checkup.sources.base import Source, SourceError
from pc_checkup.sources.powershell import run_powershell

logger = logging.getLogger(__name__)

MINIDUMP_DIR = Path(r"C:\Windows\Minidump")
MEMORY_DUMP = Path(r"C:\Windows\MEMORY.DMP")

# Provider name suffix + event id -> kind. None as id means any id from that provider.
EVENT_KINDS: list[tuple[str, int | None, EventKind]] = [
    ("WER-SystemErrorReporting", 1001, EventKind.BUGCHECK),
    ("Kernel-Power", 41, EventKind.UNEXPECTED_SHUTDOWN),
    ("WHEA-Logger", None, EventKind.HARDWARE_ERROR),
]

EVENTS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$start = (Get-Date).AddDays(-$days)
$providers = 'Microsoft-Windows-WER-SystemErrorReporting', 'Microsoft-Windows-Kernel-Power', 'Microsoft-Windows-WHEA-Logger'
$events = @(Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$start; ProviderName=$providers} |
  Where-Object {
    ($_.ProviderName -like '*WER-SystemErrorReporting' -and $_.Id -eq 1001) -or
    ($_.ProviderName -like '*Kernel-Power' -and $_.Id -eq 41) -or
    ($_.ProviderName -like '*WHEA-Logger')
  } |
  ForEach-Object {
    [pscustomobject]@{
      Time = $_.TimeCreated.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
      Id = $_.Id
      Provider = $_.ProviderName
      Props = @($_.Properties | ForEach-Object { "$($_.Value)" })
    }
  })
ConvertTo-Json -InputObject $events -Depth 4
"""


def build_events_script(days: int) -> str:
    return f"$days = {int(days)}\n{EVENTS_SCRIPT}"


def _kind_of(provider: str, event_id: int) -> EventKind | None:
    for suffix, wanted_id, kind in EVENT_KINDS:
        if provider.endswith(suffix) and wanted_id in (None, event_id):
            return kind
    return None


def _parse_event(raw: dict[str, Any]) -> SystemEvent | None:
    event_id = int(raw["Id"])
    kind = _kind_of(str(raw["Provider"]), event_id)
    if kind is None:
        return None
    props = [str(prop) for prop in raw.get("Props", [])]
    bugcheck_code = None
    if kind is EventKind.BUGCHECK and props:
        match = re.search(r"0x[0-9a-fA-F]+", props[0])
        if match:
            bugcheck_code = int(match.group(), 16)
    elif kind is EventKind.UNEXPECTED_SHUTDOWN and props and props[0].isdigit():
        # Kernel-Power 41 stores the bugcheck code in decimal; 0 means a power loss.
        bugcheck_code = int(props[0]) or None
    return SystemEvent(
        time=datetime.fromisoformat(raw["Time"]),
        kind=kind,
        event_id=event_id,
        bugcheck_code=bugcheck_code,
        details=" | ".join(props),
    )


def parse_events(output: str) -> tuple[SystemEvent, ...]:
    try:
        data = json.loads(output) if output.strip() else []
        events = (_parse_event(raw) for raw in data)
        return tuple(event for event in events if event is not None)
    except (ValueError, KeyError, TypeError) as error:
        raise SourceError("Unexpected event log data") from error


class BsodSource(Source[BsodSnapshot]):
    def __init__(
        self,
        days: int = 15,
        run_fn: Callable[[str], str] = run_powershell,
        minidump_dir: Path = MINIDUMP_DIR,
        memory_dump: Path = MEMORY_DUMP,
        now_fn: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._days = days
        self._run = run_fn
        self._minidump_dir = minidump_dir
        self._memory_dump = memory_dump
        self._now = now_fn

    def fetch(self) -> BsodSnapshot:
        output = self._run(build_events_script(self._days))
        return BsodSnapshot(
            days=self._days,
            events=parse_events(output),
            dump_files=self._recent_dump_files(),
        )

    def _recent_dump_files(self) -> tuple[str, ...]:
        cutoff = self._now() - timedelta(days=self._days)
        candidates: list[Path] = []
        if self._minidump_dir.is_dir():
            candidates.extend(sorted(self._minidump_dir.glob("*.dmp")))
        if self._memory_dump.is_file():
            candidates.append(self._memory_dump)
        recent = []
        for path in candidates:
            try:
                if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
                    recent.append(str(path))
            except OSError:
                logger.warning("Could not read dump file %s", path)
        return tuple(recent)
