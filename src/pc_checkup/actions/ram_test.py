"""RAM test: schedules the Windows Memory Diagnostic, restarts the PC and reopens afterwards.

The test runs before Windows starts, so it has two phases. This action is phase
one: it records the start, sets the program to reopen after the restart,
schedules the test for the next boot and restarts the PC after a short delay.
The menu handles phase two by reading the result newer than the recorded start.
"""

import logging
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pc_checkup import autostart
from pc_checkup.actions.base import Action, ActionError
from pc_checkup.actions.command import system32
from pc_checkup.messages import get_message
from pc_checkup.models import Level, Line
from pc_checkup.storage import (
    clear_pending_ram_test,
    load_pending_ram_test,
    save_pending_ram_test,
)

logger = logging.getLogger(__name__)

# Seconds Windows waits before restarting; `shutdown /a` cancels it in that time.
RESTART_DELAY_SECONDS = 15
COMMAND_TIMEOUT_SECONDS = 30
REOPEN_ARGUMENT = "--show-ram-result"


def _run_checked(command: list[str]) -> None:
    """Run a Windows tool without a shell; a failure of any kind becomes an OSError."""
    try:
        result = subprocess.run(
            command, capture_output=True, timeout=COMMAND_TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired as error:
        raise OSError(f"{command[0]} did not finish in time") from error
    if result.returncode != 0:
        raise OSError(f"{command[0]} exited with code {result.returncode}")


def schedule_memory_test() -> None:
    """Run the memory diagnostic at the next boot only (the same way mdsched does it)."""
    _run_checked([system32("bcdedit.exe"), "/bootsequence", "{memdiag}", "/addfirst"])


def restart_pc(comment: str) -> None:
    _run_checked(
        [system32("shutdown.exe"), "/r", "/t", str(RESTART_DELAY_SECONDS), "/c", comment]
    )


def register_reopen() -> None:
    autostart.register_after_reboot(autostart.build_command([REOPEN_ARGUMENT]))


class RamTestAction(Action):
    def __init__(
        self,
        schedule_fn: Callable[[], None] = schedule_memory_test,
        restart_fn: Callable[[str], None] = restart_pc,
        register_fn: Callable[[], None] = register_reopen,
        unregister_fn: Callable[[], None] = autostart.unregister,
        state_path: Path | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.now().astimezone(),
    ) -> None:
        self._schedule = schedule_fn
        self._restart = restart_fn
        self._register = register_fn
        self._unregister = unregister_fn
        self._state_path = state_path
        self._now = now_fn

    def describe(self, language: str) -> str:
        return get_message("ram_test.describe", language)

    def warning(self, language: str) -> str:
        return get_message("ram_test.warning", language, seconds=RESTART_DELAY_SECONDS)

    def run(self, language: str) -> list[Line]:
        # Record first: if this fails, nothing has been scheduled yet.
        try:
            save_pending_ram_test(self._now(), self._state_path)
        except OSError as error:
            raise ActionError() from error

        reopens = True
        try:
            self._register()
        except OSError:
            # The test still works; the user just has to reopen the program by hand.
            logger.exception("Could not set the program to reopen after the restart")
            reopens = False

        try:
            self._schedule()
        except OSError as error:
            self._roll_back()
            raise ActionError("ram_test.schedule_failed") from error

        try:
            self._restart(get_message("ram_test.restart_comment", language))
        except OSError as error:
            # The test stays scheduled for the next restart, whenever the user does it.
            raise ActionError("ram_test.restart_failed") from error

        restarting = get_message("ram_test.restarting", language, seconds=RESTART_DELAY_SECONDS)
        follow_up = "ram_test.reopens" if reopens else "ram_test.autostart_failed"
        return [Line(restarting, Level.LOG), Line(get_message(follow_up, language), Level.LOG)]

    def _roll_back(self) -> None:
        clear_pending_ram_test(self._state_path)
        try:
            self._unregister()
        except OSError:
            logger.exception("Could not remove the reopen entry")

    def pending_since(self) -> datetime | None:
        return load_pending_ram_test(self._state_path)

    def clear_pending(self) -> None:
        clear_pending_ram_test(self._state_path)
