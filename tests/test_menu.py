from collections.abc import Iterator
from pathlib import Path

from pc_checkup.config import load_language
from pc_checkup.menu import Menu


def make_menu(
    answers: list[str], tmp_path: Path, language: str = "en"
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
