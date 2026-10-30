from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pc_checkup.storage import (
    clear_pending_ram_test,
    default_state_path,
    load_pending_ram_test,
    save_pending_ram_test,
)

BRT = timezone(timedelta(hours=-3))
WHEN = datetime(2026, 10, 30, 10, 15, tzinfo=BRT)


def test_no_file_means_no_pending_test(tmp_path: Path) -> None:
    assert load_pending_ram_test(tmp_path / "state.json") is None


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    save_pending_ram_test(WHEN, path)
    assert load_pending_ram_test(path) == WHEN


def test_save_creates_missing_folder(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "state.json"
    save_pending_ram_test(WHEN, path)
    assert path.exists()


def test_clear_removes_the_pending_test(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    save_pending_ram_test(WHEN, path)
    clear_pending_ram_test(path)
    assert load_pending_ram_test(path) is None


def test_clear_without_a_file_is_fine(tmp_path: Path) -> None:
    clear_pending_ram_test(tmp_path / "state.json")


@pytest.mark.parametrize("content", ["{ not json", "{}", '{"ram_test_pending_since": "soon"}', "[]"])
def test_unusable_file_means_no_pending_test(tmp_path: Path, content: str) -> None:
    path = tmp_path / "state.json"
    path.write_text(content, encoding="utf-8")
    assert load_pending_ram_test(path) is None


def test_naive_time_is_read_as_local_time(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"ram_test_pending_since": "2026-10-30T10:15:00"}', encoding="utf-8")
    loaded = load_pending_ram_test(path)
    assert loaded is not None
    assert loaded.tzinfo is not None


def test_default_path_is_next_to_the_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_state_path() == tmp_path / "pc_checkup" / "state.json"
