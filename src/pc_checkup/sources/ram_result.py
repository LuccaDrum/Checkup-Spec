"""Reads the latest Windows Memory Diagnostic result from the System log."""

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from pc_checkup.models import RamOutcome, RamSnapshot, RamTestResult
from pc_checkup.sources.base import Source, SourceError
from pc_checkup.sources.powershell import run_powershell

# Provider Microsoft-Windows-MemoryDiagnostics-Results: 1101/1201 no errors, 1102/1202 errors.
OUTCOMES = {
    1101: RamOutcome.NO_ERRORS,
    1201: RamOutcome.NO_ERRORS,
    1102: RamOutcome.ERRORS_FOUND,
    1202: RamOutcome.ERRORS_FOUND,
}

RESULTS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$events = @(Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-MemoryDiagnostics-Results'; Id=1101,1102,1201,1202} -MaxEvents 10 |
  ForEach-Object {
    [pscustomobject]@{
      Time = $_.TimeCreated.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
      Id = $_.Id
    }
  })
ConvertTo-Json -InputObject $events -Depth 3
"""


def _parse_result(raw: dict[str, Any]) -> RamTestResult | None:
    event_id = int(raw["Id"])
    outcome = OUTCOMES.get(event_id)
    if outcome is None:
        return None
    return RamTestResult(time=datetime.fromisoformat(raw["Time"]), outcome=outcome, event_id=event_id)


def parse_results(output: str) -> tuple[RamTestResult, ...]:
    try:
        data = json.loads(output) if output.strip() else []
        if isinstance(data, dict):
            data = [data]
        results = (_parse_result(raw) for raw in data)
        return tuple(result for result in results if result is not None)
    except (ValueError, KeyError, TypeError) as error:
        raise SourceError("Unexpected memory diagnostic data") from error


class RamResultSource(Source[RamSnapshot]):
    """`since` keeps only results newer than a moment, used to ignore results of older tests."""

    def __init__(
        self,
        run_fn: Callable[[str], str] = run_powershell,
        since: datetime | None = None,
    ) -> None:
        self._run = run_fn
        self._since = since.astimezone() if since and since.tzinfo is None else since

    def fetch(self) -> RamSnapshot:
        results = parse_results(self._run(RESULTS_SCRIPT))
        if self._since is not None:
            results = tuple(result for result in results if result.time >= self._since)
        latest = max(results, key=lambda result: result.time, default=None)
        return RamSnapshot(latest=latest)
