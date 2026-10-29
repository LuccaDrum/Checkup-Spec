import io
from typing import Any

import pytest

from pc_checkup import ui
from pc_checkup.models import Level
from pc_checkup.ui import BOLD, LEVEL_STYLES, RESET, Ui


def test_every_level_has_a_style() -> None:
    assert set(LEVEL_STYLES) == set(Level)


def test_plain_mode_returns_text_unchanged() -> None:
    plain = Ui(color=False)
    assert plain.bold("x") == "x"
    assert plain.option("2", "Blue screens") == "2) Blue screens"
    assert plain.block("hello", Level.ERROR) == "hello"
    assert set(plain.separator()) == {"-"}


def test_color_mode_makes_bold_and_separator() -> None:
    styled = Ui(color=True, width=50)
    assert styled.bold("x") == f"{BOLD}x{RESET}"
    assert styled.option("2", "Blue screens") == f"{BOLD}2){RESET} Blue screens"
    assert styled.separator() == "─" * 50


def test_block_uses_the_color_of_its_level() -> None:
    styled = Ui(color=True, width=50)
    assert styled.block("boom", Level.ERROR).startswith("\x1b[1;97;41m")
    assert styled.block("fine", Level.OK).startswith("\x1b[30;42m")


def test_block_pads_every_line_to_the_same_width() -> None:
    styled = Ui(color=True, width=50)
    text = "word " * 30
    lines = styled.block(text, Level.INFO).split("\n")
    assert len(lines) > 1
    visible = [line.removeprefix("\x1b[97;44m").removesuffix(RESET) for line in lines]
    assert {len(line) for line in visible} == {50}


def test_width_is_limited() -> None:
    assert Ui(color=True, width=500).width == 100
    assert Ui(color=True, width=10).width == 40


class FakeStream(io.StringIO):
    def __init__(self, tty: bool) -> None:
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_no_color_when_output_is_redirected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert ui.supports_color(FakeStream(tty=False)) is False


def test_no_color_variable_disables_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert ui.supports_color(FakeStream(tty=True)) is False


def test_color_enabled_on_a_terminal_that_accepts_ansi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(ui, "_enable_windows_ansi", lambda: True)
    assert ui.supports_color(FakeStream(tty=True)) is True


def test_color_disabled_when_windows_refuses_ansi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(ui, "_enable_windows_ansi", lambda: False)
    assert ui.supports_color(FakeStream(tty=True)) is False


def test_enable_windows_ansi_handles_a_failing_console(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenKernel:
        def __getattr__(self, name: str) -> Any:
            raise OSError("no console")

    class BrokenWindll:
        kernel32 = BrokenKernel()

    monkeypatch.setattr(ui.sys, "platform", "win32")
    monkeypatch.setattr(ui.ctypes, "windll", BrokenWindll(), raising=False)
    assert ui._enable_windows_ansi() is False
