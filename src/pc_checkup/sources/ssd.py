"""Reads disk health and reliability counters (needs admin for the counters)."""

import json
import logging
from collections.abc import Callable
from typing import Any

from pc_checkup.models import DiskInfo, SsdSnapshot
from pc_checkup.sources.base import Source, SourceError
from pc_checkup.sources.powershell import run_powershell

logger = logging.getLogger(__name__)

DISKS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$disks = @(Get-PhysicalDisk | ForEach-Object {
  $counter = $_ | Get-StorageReliabilityCounter
  [pscustomobject]@{
    DeviceId = "$($_.DeviceId)"
    Name = "$($_.FriendlyName)"
    MediaType = "$($_.MediaType)"
    BusType = "$($_.BusType)"
    Health = "$($_.HealthStatus)"
    SizeBytes = $_.Size
    Wear = $counter.Wear
    Temperature = $counter.Temperature
    PowerOnHours = $counter.PowerOnHours
    ReadErrorsUncorrected = $counter.ReadErrorsUncorrected
    WriteErrorsUncorrected = $counter.WriteErrorsUncorrected
  }
})
ConvertTo-Json -InputObject $disks -Depth 3
"""


def _number(value: Any) -> int | None:
    """Counters come as numbers or null; anything else counts as not readable."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)


def _parse_disk(raw: dict[str, Any]) -> DiskInfo:
    return DiskInfo(
        device_id=str(raw["DeviceId"]),
        name=str(raw["Name"]),
        media_type=str(raw["MediaType"]),
        bus_type=str(raw["BusType"]),
        health=str(raw["Health"]),
        size_bytes=_number(raw.get("SizeBytes")),
        wear_percent=_number(raw.get("Wear")),
        temperature_c=_number(raw.get("Temperature")),
        power_on_hours=_number(raw.get("PowerOnHours")),
        read_errors_uncorrected=_number(raw.get("ReadErrorsUncorrected")),
        write_errors_uncorrected=_number(raw.get("WriteErrorsUncorrected")),
    )


def parse_disks(output: str) -> tuple[DiskInfo, ...]:
    try:
        data = json.loads(output) if output.strip() else []
        if isinstance(data, dict):
            data = [data]
        return tuple(_parse_disk(raw) for raw in data)
    except (ValueError, KeyError, TypeError) as error:
        raise SourceError("Unexpected disk data") from error


class SsdSource(Source[SsdSnapshot]):
    def __init__(self, run_fn: Callable[[str], str] = run_powershell) -> None:
        self._run = run_fn

    def fetch(self) -> SsdSnapshot:
        return SsdSnapshot(disks=parse_disks(self._run(DISKS_SCRIPT)))
