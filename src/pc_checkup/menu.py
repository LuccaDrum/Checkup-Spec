"""Numbered menu: shows options, validates input and dispatches."""

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pc_checkup.config import save_language
from pc_checkup.interpreter import interpret_bsod, interpret_ssd
from pc_checkup.messages import SUPPORTED_LANGUAGES, get_message
from pc_checkup.models import BsodSnapshot, Level, Report, SsdSnapshot
from pc_checkup.sources.base import Source, SourceError
from pc_checkup.sources.bsod import BsodSource
from pc_checkup.sources.ssd import SsdSource
from pc_checkup.ui import Ui

logger = logging.getLogger(__name__)

SnapshotT = TypeVar("SnapshotT")

# (choice typed by the user, message key of its label), in display order.
OPTIONS = [
    ("1", "menu.full_check"),
    ("2", "menu.bsod"),
    ("3", "menu.ssd"),
    ("4", "menu.ram"),
    ("5", "menu.sfc"),
    ("6", "menu.dism"),
    ("7", "menu.settings"),
    ("0", "menu.exit"),
]
VALID_CHOICES = {choice for choice, _ in OPTIONS}

# Lets the user read a short confirmation before the menu is drawn again.
CONFIRMATION_PAUSE_SECONDS = 0.7


class Menu:
    def __init__(
        self,
        language: str,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
        config_path: Path | None = None,
        bsod_source: Source[BsodSnapshot] | None = None,
        color: bool = False,
        sleep_fn: Callable[[float], None] = time.sleep,
        ssd_source: Source[SsdSnapshot] | None = None,
    ) -> None:
        self.language = language
        self._input = input_fn
        self._print = print_fn
        self._config_path = config_path
        self._bsod_source = bsod_source or BsodSource()
        self._ssd_source = ssd_source or SsdSource()
        self._ui = Ui(color)
        self._sleep = sleep_fn

    def _text(self, key: str) -> str:
        return get_message(key, self.language)

    def _say(self, key: str, level: Level = Level.INFO) -> None:
        self._print(self._ui.block(self._text(key), level))

    def show(self) -> None:
        self._print("")
        self._print(self._ui.separator())
        self._print(self._ui.bold(self._text("menu.title")))
        self._print(self._ui.separator())
        for choice, key in OPTIONS:
            self._print(self._ui.option(choice, self._text(key)))
        self._print(self._ui.separator())

    def read_choice(self) -> str:
        while True:
            choice = self._input(self._ui.bold(self._text("menu.prompt"))).strip()
            if choice in VALID_CHOICES:
                return choice
            self._say("menu.invalid", Level.ERROR)

    def toggle_language(self) -> None:
        index = SUPPORTED_LANGUAGES.index(self.language)
        self.language = SUPPORTED_LANGUAGES[(index + 1) % len(SUPPORTED_LANGUAGES)]
        save_language(self.language, self._config_path)
        self._say("settings.language_changed", Level.NOTICE)
        self._sleep(CONFIRMATION_PAUSE_SECONDS)

    def _show_check(
        self,
        source: Source[SnapshotT],
        interpret: Callable[[SnapshotT, str], Report],
        working_key: str,
        failed_key: str,
    ) -> None:
        self._say(working_key)
        try:
            snapshot = source.fetch()
        except SourceError:
            logger.exception("Could not read data for %s", working_key)
            self._say(failed_key, Level.ERROR)
            return
        report = interpret(snapshot, self.language)
        for line in report.friendly:
            self._print(self._ui.block(line.text, line.level))
        if report.technical:
            self._print("")
            for text in report.technical:
                self._print(self._ui.block(text, Level.TECHNICAL))

    def show_bsod(self) -> None:
        self._show_check(self._bsod_source, interpret_bsod, "bsod.working", "bsod.read_failed")

    def show_ssd(self) -> None:
        self._show_check(self._ssd_source, interpret_ssd, "ssd.working", "ssd.read_failed")

    def run(self) -> None:
        while True:
            self.show()
            choice = self.read_choice()
            if choice == "0":
                self._say("menu.goodbye")
                return
            if choice == "2":
                self.show_bsod()
            elif choice == "3":
                self.show_ssd()
            elif choice == "7":
                self.toggle_language()
            else:
                self._say("menu.not_available", Level.LOG)
