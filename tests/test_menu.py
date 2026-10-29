from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from pc_checkup.config import load_language
from pc_checkup.menu import Menu
from pc_checkup.models import BsodSnapshot, EventKind, SystemEvent
from pc_checkup.sources.base import Source, SourceError


class FakeBsodSource(Source[BsodSnapshot]):
    def __init__(self, snapshot: BsodSnapshot | None = None, fail: bool = False) -> None:
        self._snapshot = snapshot or BsodSnapshot(days=15, events=(), dump_files=())
        self._fail = fail
        self.calls = 0

    def fetch(self) -> BsodSnapshot:
        self.calls += 1
        if self._fail:
            raise SourceError("boom")
        return self._snapshot


def make_menu(
    answers: list[str],
    tmp_path: Path,
    language: str = "en",
    source: Source[BsodSnapshot] | None = None,
) -> tuple[Menu, list[str], Path]:
    """Build a Menu fed by `answers`; returns it with its printed lines and config path."""
    printed: list[str] = []
    remaining: Iterator[str] = iter(answers)
    config_path = tmp_path / "config.json"
    menu = Menu(
        language,
        input_fn=lambda prompt: next(remaining),
        print_fn=printed.append,
        config_path=config_path,
        bsod_source=source or FakeBsodSource(),
    )
    return menu, printed, config_path


def test_exit_shows_menu_and_goodbye(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["0"], tmp_path)
    menu.run()
    assert "=== PC Checkup ===" in printed
    assert "7) Settings (language)" in printed
    assert printed[-1] == "Goodbye!"


def test_invalid_input_repeats_the_prompt(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["abc", "9", "", "   ", "0"], tmp_path)
    menu.run()
    assert printed.count("That is not a valid option. Please type a number from the menu.") == 4
    assert printed[-1] == "Goodbye!"


def test_input_is_trimmed(tmp_path: Path) -> None:
    menu, printed, _ = make_menu([" 0 "], tmp_path)
    menu.run()
    assert printed[-1] == "Goodbye!"


def test_unimplemented_option_says_not_available(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["3", "0"], tmp_path)
    menu.run()
    assert "This option is not available yet." in printed


def test_settings_switches_language_and_saves_it(tmp_path: Path) -> None:
    menu, printed, config_path = make_menu(["7", "0"], tmp_path)
    menu.run()
    assert "Language changed to English." not in printed
    assert "Idioma alterado para português." in printed
    assert menu.language == "pt"
    assert load_language(config_path) == "pt"
    assert printed[-1] == "Até logo!"


def test_settings_switches_back_to_english(tmp_path: Path) -> None:
    menu, printed, config_path = make_menu(["7", "0"], tmp_path, language="pt")
    menu.run()
    assert "Language changed to English." in printed
    assert load_language(config_path) == "en"


def crash_snapshot() -> BsodSnapshot:
    crash = SystemEvent(
        time=datetime(2026, 10, 29, 7, 43),
        kind=EventKind.BUGCHECK,
        event_id=1001,
        bugcheck_code=0x1A,
    )
    return BsodSnapshot(days=15, events=(crash,), dump_files=())


def test_option_2_shows_friendly_report_then_technical_details(tmp_path: Path) -> None:
    source = FakeBsodSource(crash_snapshot())
    menu, printed, _ = make_menu(["2", "0"], tmp_path, source=source)
    menu.run()
    assert source.calls == 1
    friendly = printed.index("Your PC crashed once in the last 15 days.")
    technical = printed.index("Technical details:")
    assert friendly < technical
    assert any("code=0x1a MEMORY_MANAGEMENT" in line for line in printed)


def test_option_2_in_portuguese(tmp_path: Path) -> None:
    source = FakeBsodSource(crash_snapshot())
    menu, printed, _ = make_menu(["2", "0"], tmp_path, language="pt", source=source)
    menu.run()
    assert "Seu PC travou uma vez nos últimos 15 dias." in printed


def test_option_2_without_problems(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["2", "0"], tmp_path)
    menu.run()
    assert any(line.startswith("Good news") for line in printed)


def test_option_2_failure_shows_friendly_message_and_keeps_running(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["2", "0"], tmp_path, source=FakeBsodSource(fail=True))
    menu.run()
    assert any("Could not read the Windows event log" in line for line in printed)
    assert printed[-1] == "Goodbye!"


def make_color_menu(answers: list[str], source: Source[BsodSnapshot]) -> tuple[Menu, list[str]]:
    printed: list[str] = []
    remaining: Iterator[str] = iter(answers)
    menu = Menu(
        "en",
        input_fn=lambda prompt: next(remaining),
        print_fn=printed.append,
        bsod_source=source,
        color=True,
    )
    return menu, printed


def test_color_menu_has_bold_options_and_separators() -> None:
    menu, printed = make_color_menu(["0"], FakeBsodSource())
    menu.run()
    assert "\x1b[1m2)\x1b[0m Blue screens (last 15 days)" in printed
    assert "─" in printed[1]


def test_color_menu_shows_invalid_input_in_red() -> None:
    menu, printed = make_color_menu(["abc", "0"], FakeBsodSource())
    menu.run()
    errors = [line for line in printed if line.startswith("\x1b[1;97;41m")]
    assert len(errors) == 1
    assert "not a valid option" in errors[0]


def test_color_report_uses_red_for_crashes_cyan_for_hints_and_gray_for_details() -> None:
    menu, printed = make_color_menu(["2", "0"], FakeBsodSource(crash_snapshot()))
    menu.run()
    text = "\n".join(printed)
    assert "\x1b[1;97;41m" in text
    assert "\x1b[30;46m" in text
    assert "\x1b[97;100m" in text
