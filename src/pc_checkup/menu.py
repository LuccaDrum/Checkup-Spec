"""Numbered menu: shows options, validates input and dispatches."""

import logging
from collections.abc import Callable
from pathlib import Path

from pc_checkup.config import save_language
from pc_checkup.interpreter import interpret_bsod
from pc_checkup.messages import SUPPORTED_LANGUAGES, get_message
from pc_checkup.models import BsodSnapshot
from pc_checkup.sources.base import Source, SourceError
from pc_checkup.sources.bsod import BsodSource

logger = logging.getLogger(__name__)

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


class Menu:
    def __init__(
        self,
        language: str,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
        config_path: Path | None = None,
        bsod_source: Source[BsodSnapshot] | None = None,
    ) -> None:
        self.language = language
        self._input = input_fn
        self._print = print_fn
        self._config_path = config_path
        self._bsod_source = bsod_source or BsodSource()

    def _text(self, key: str) -> str:
        return get_message(key, self.language)

    def show(self) -> None:
        self._print(self._text("menu.title"))
        for choice, key in OPTIONS:
            self._print(f"{choice}) {self._text(key)}")

    def read_choice(self) -> str:
        while True:
            choice = self._input(self._text("menu.prompt")).strip()
            if choice in VALID_CHOICES:
                return choice
            self._print(self._text("menu.invalid"))

    def toggle_language(self) -> None:
        index = SUPPORTED_LANGUAGES.index(self.language)
        self.language = SUPPORTED_LANGUAGES[(index + 1) % len(SUPPORTED_LANGUAGES)]
        save_language(self.language, self._config_path)
        self._print(self._text("settings.language_changed"))

    def show_bsod(self) -> None:
        self._print(self._text("bsod.working"))
        try:
            snapshot = self._bsod_source.fetch()
        except SourceError:
            logger.exception("Could not read blue screen data")
            self._print(self._text("bsod.read_failed"))
            return
        report = interpret_bsod(snapshot, self.language)
        for line in report.friendly:
            self._print(line)
        self._print("")
        for line in report.technical:
            self._print(line)

    def run(self) -> None:
        while True:
            self.show()
            choice = self.read_choice()
            if choice == "0":
                self._print(self._text("menu.goodbye"))
                return
            if choice == "2":
                self.show_bsod()
            elif choice == "7":
                self.toggle_language()
            else:
                self._print(self._text("menu.not_available"))
