"""Shared logic of the repair actions (SFC and DISM): run a tool, explain its exit code.

Results are decided by exit codes through a table, never by the tool's text.
"""

import logging
import subprocess
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pc_checkup.actions.base import Action, ActionError
from pc_checkup.actions.command import run_tool
from pc_checkup.messages import get_message
from pc_checkup.models import Level, Line

logger = logging.getLogger(__name__)

# Generous: these repairs are long and killing one halfway is worse than waiting.
REPAIR_TIMEOUT_SECONDS = 3 * 60 * 60


@dataclass(frozen=True)
class Outcome:
    message_key: str
    level: Level
    succeeded: bool


class RepairAction(Action):
    """Subclasses say which tool to run and what its exit codes mean."""

    prefix: ClassVar[str]
    outcomes: ClassVar[dict[int, Outcome]]
    unknown_outcome: ClassVar[Outcome]

    def __init__(
        self,
        run_fn: Callable[[list[str], int], int] = run_tool,
        timeout: int = REPAIR_TIMEOUT_SECONDS,
    ) -> None:
        self._run = run_fn
        self._timeout = timeout

    @abstractmethod
    def command(self) -> list[str]: ...

    @abstractmethod
    def log_path(self) -> Path: ...

    def describe(self, language: str) -> str:
        return get_message(f"{self.prefix}.describe", language)

    def warning(self, language: str) -> str:
        return get_message(f"{self.prefix}.warning", language)

    def run(self, language: str) -> list[Line]:
        try:
            code = self._run(self.command(), self._timeout)
        except subprocess.TimeoutExpired as error:
            raise ActionError("repair.timeout") from error
        except OSError as error:
            raise ActionError("repair.not_found") from error

        outcome = self.outcomes.get(code, self.unknown_outcome)
        logger.info("%s exited with code %#x", self.prefix, code)
        lines = [Line(get_message(outcome.message_key, language), outcome.level)]
        if not outcome.succeeded:
            lines.append(
                Line(
                    get_message("repair.technical_code", language, code=code, hex=f"{code:#010x}"),
                    Level.TECHNICAL,
                )
            )
            lines.append(
                Line(
                    get_message("repair.technical_log", language, path=str(self.log_path())),
                    Level.TECHNICAL,
                )
            )
        return lines
