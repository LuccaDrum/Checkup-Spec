from pathlib import Path

import pytest

from pc_checkup.config import default_config_path, load_language, save_language
from pc_checkup.messages import DEFAULT_LANGUAGE


def test_missing_file_returns_default(tmp_path: Path) -> None:
    assert load_language(tmp_path / "config.json") == DEFAULT_LANGUAGE


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    save_language("pt", path)
    assert load_language(path) == "pt"


def test_save_creates_missing_folder(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "folder" / "config.json"
    save_language("en", path)
    assert path.exists()


def test_corrupt_file_returns_default(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_language(path) == DEFAULT_LANGUAGE


def test_missing_key_returns_default(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    assert load_language(path) == DEFAULT_LANGUAGE


def test_unsupported_language_in_file_returns_default(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"language": "xx"}', encoding="utf-8")
    assert load_language(path) == DEFAULT_LANGUAGE


def test_save_unsupported_language_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        save_language("xx", tmp_path / "config.json")


def test_default_path_uses_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_config_path() == tmp_path / "pc_checkup" / "config.json"
