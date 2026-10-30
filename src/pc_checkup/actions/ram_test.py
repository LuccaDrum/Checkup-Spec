"""RAM test: starts the Windows Memory Diagnostic and remembers that a test is pending.

The test needs a restart, so it has two phases. This action is phase one; the
menu handles phase two by reading the result newer than the pending record.
"""

import logging
import os
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pc_checkup.actions.base import Action, ActionError
from pc_checkup.messages import get_message
from pc_checkup.models import Level, Line
from pc_checkup.storage import (
    clear_pending_ram_test,
    load_pending_ram_test,
    save_pending_ram_test,
)

logger = logging.getLogger(__name__)


def launch_mdsched() -> None:
    """Open mdsched.exe and return at once.

    Deliberately no timeout and no waiting: Windows keeps its restart-now-or-later
    window open for as long as the user takes, and a timeout would kill that window.
    """
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "mdsched.exe"
    subprocess.Popen([str(executable)])


class RamTestAction(Action):
    def __init__(
        self,
        launch_fn: Callable[[], None] = launch_mdsched,
        state_path: Path | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.now().astimezone(),
    ) -> None:
        self._launch = launch_fn
        self._state_path = state_path
        self._now = now_fn

    def describe(self, language: str) -> str:
        return get_message("ram_test.describe", language)

    def warning(self, language: str) -> str:
        return get_message("ram_test.warning", language)

    def run(self, language: str) -> list[Line]:
        # Record first: if this fails nothing has been opened yet.
        try:
            save_pending_ram_test(self._now(), self._state_path)
        except OSError as error:
            raise ActionError() from error
        try:
            self._launch()
        except OSError as error:
            clear_pending_ram_test(self._state_path)
            raise ActionError("ram_test.launch_failed") from error
        return [Line(get_message("ram_test.started", language), Level.LOG)]

    def pending_since(self) -> datetime | None:
        return load_pending_ram_test(self._state_path)

    def clear_pending(self) -> None:
        clear_pending_ram_test(self._state_path)
