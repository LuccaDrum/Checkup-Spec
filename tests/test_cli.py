from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest

from pc_checkup import cli
from pc_checkup.cli import main, parse_args


def run_main(
    answers: list[str],
    tmp_path: Path,
    *,
    admin: bool,
    relaunch_ok: bool = True,
    argv: list[str] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Run main() with fakes; returns exit code, printed lines and relaunch calls."""
    printed: list[str] = []
    relaunches: list[str] = []
    remaining: Iterator[str] = iter(answers)

    def fake_relaunch() -> bool:
        relaunches.append("called")
        return relaunch_ok

    code = main(
        is_admin_fn=lambda: admin,
        relaunch_fn=fake_relaunch,
        input_fn=lambda prompt: next(remaining),
        print_fn=printed.append,
        config_path=tmp_path / "config.json",
        color=False,
        argv=argv or [],
    )
    return code, printed, relaunches


def test_admin_runs_the_menu_then_waits_for_enter(tmp_path: Path) -> None:
    code, printed, relaunches = run_main(["0", ""], tmp_path, admin=True)
    assert code == 0
    assert "=== PC Checkup ===" in printed
    assert relaunches == []


def test_not_admin_relaunches_and_exits_without_menu(tmp_path: Path) -> None:
    code, printed, relaunches = run_main([], tmp_path, admin=False)
    assert code == 0
    assert relaunches == ["called"]
    assert printed == []


def test_declined_uac_explains_why_admin_is_needed(tmp_path: Path) -> None:
    code, printed, _ = run_main([""], tmp_path, admin=False, relaunch_ok=False)
    assert code == 1
    assert any("administrator" in line for line in printed)
    assert "=== PC Checkup ===" not in printed


def test_flag_is_off_by_default() -> None:
    assert parse_args([]).show_ram_result is False


def test_flag_is_recognized() -> None:
    assert parse_args(["--show-ram-result"]).show_ram_result is True


def test_unknown_arguments_are_ignored() -> None:
    assert parse_args(["-q", "--whatever"]).show_ram_result is False


class FakeMenu:
    """Records what main() asks the menu to do, so nothing real is read or started."""

    calls: ClassVar[list[Any]] = []

    def __init__(self, language: str, *args: Any, **kwargs: Any) -> None:
        self.language = language

    def show_ram_test(self, allow_start: bool = True) -> None:
        FakeMenu.calls.append(("show_ram_test", allow_start))

    def run(self) -> None:
        FakeMenu.calls.append("run")


@pytest.fixture
def fake_menu(monkeypatch: pytest.MonkeyPatch) -> type[FakeMenu]:
    FakeMenu.calls = []
    monkeypatch.setattr(cli, "Menu", FakeMenu)
    return FakeMenu


def test_reopened_after_the_ram_test_shows_the_result_read_only_then_the_menu(
    tmp_path: Path, fake_menu: type[FakeMenu]
) -> None:
    run_main([""], tmp_path, admin=True, argv=["--show-ram-result"])
    assert fake_menu.calls == [("show_ram_test", False), "run"]


def test_normal_start_does_not_touch_the_ram_test(
    tmp_path: Path, fake_menu: type[FakeMenu]
) -> None:
    run_main([""], tmp_path, admin=True)
    assert fake_menu.calls == ["run"]


def test_the_flag_without_admin_still_relaunches_first(
    tmp_path: Path, fake_menu: type[FakeMenu]
) -> None:
    code, _, relaunches = run_main([], tmp_path, admin=False, argv=["--show-ram-result"])
    assert code == 0
    assert relaunches == ["called"]
    assert fake_menu.calls == []
