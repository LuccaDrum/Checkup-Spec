"""DISM: repairs the Windows component store (DISM /Online /Cleanup-Image /RestoreHealth)."""

from pathlib import Path
from typing import ClassVar

from pc_checkup.actions.command import system32, windows_dir
from pc_checkup.actions.repair import Outcome, RepairAction
from pc_checkup.models import Level

ERROR_ACCESS_DENIED = 5
ERROR_ELEVATION_REQUIRED = 740
ERROR_SUCCESS_REBOOT_REQUIRED = 3010
CBS_E_SOURCE_MISSING = 0x800F081F
CBS_E_DOWNLOAD_FAILED = 0x800F0906
CBS_E_DOWNLOAD_BLOCKED_BY_POLICY = 0x800F0907

DENIED = Outcome("dism.access_denied", Level.ERROR, succeeded=False)


class DismAction(RepairAction):
    prefix = "dism"
    # Documented DISM and servicing error codes; anything else is a generic failure.
    outcomes: ClassVar[dict[int, Outcome]] = {
        0: Outcome("dism.ok", Level.OK, succeeded=True),
        ERROR_SUCCESS_REBOOT_REQUIRED: Outcome("dism.ok_reboot", Level.LOG, succeeded=True),
        CBS_E_SOURCE_MISSING: Outcome("dism.source_missing", Level.ERROR, succeeded=False),
        CBS_E_DOWNLOAD_FAILED: Outcome("dism.download_failed", Level.ERROR, succeeded=False),
        CBS_E_DOWNLOAD_BLOCKED_BY_POLICY: Outcome("dism.policy_blocked", Level.ERROR, succeeded=False),
        ERROR_ACCESS_DENIED: DENIED,
        ERROR_ELEVATION_REQUIRED: DENIED,
    }
    unknown_outcome = Outcome("dism.failed", Level.ERROR, succeeded=False)

    def command(self) -> list[str]:
        return [system32("dism.exe"), "/Online", "/Cleanup-Image", "/RestoreHealth"]

    def log_path(self) -> Path:
        return windows_dir() / "Logs" / "DISM" / "dism.log"
