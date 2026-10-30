"""SFC: scans protected Windows files and replaces damaged ones (sfc /scannow)."""

from pathlib import Path
from typing import ClassVar

from pc_checkup.actions.command import system32, windows_dir
from pc_checkup.actions.repair import Outcome, RepairAction
from pc_checkup.models import Level


class SfcAction(RepairAction):
    prefix = "sfc"
    # Only 0 is encoded for now. The spec asks to record what a real run returns before
    # trusting more codes, so anything else is reported as "could not finish" plus the code.
    outcomes: ClassVar[dict[int, Outcome]] = {0: Outcome("sfc.done", Level.OK, succeeded=True)}
    unknown_outcome = Outcome("sfc.failed", Level.ERROR, succeeded=False)

    def command(self) -> list[str]:
        return [system32("sfc.exe"), "/scannow"]

    def log_path(self) -> Path:
        return windows_dir() / "Logs" / "CBS" / "CBS.log"
