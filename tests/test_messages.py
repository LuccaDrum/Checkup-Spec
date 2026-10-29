import pytest

from pc_checkup.messages import MESSAGES, SUPPORTED_LANGUAGES, get_message


def test_every_language_has_the_same_keys() -> None:
    reference = set(MESSAGES["en"])
    for language in SUPPORTED_LANGUAGES:
        assert set(MESSAGES[language]) == reference, f"keys differ in '{language}'"


def test_supported_languages_match_messages() -> None:
    assert set(SUPPORTED_LANGUAGES) == set(MESSAGES)


def test_no_message_is_empty() -> None:
    for language, texts in MESSAGES.items():
        for key, text in texts.items():
            assert text.strip(), f"empty text for '{key}' in '{language}'"


def test_get_message_returns_text_in_requested_language() -> None:
    assert get_message("menu.exit", "en") == "Exit"
    assert get_message("menu.exit", "pt") == "Sair"


def test_get_message_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        get_message("does.not.exist", "en")
