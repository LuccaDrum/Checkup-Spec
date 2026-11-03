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
    log_path: Path | None = None,
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
        setup_logging_fn=lambda: log_path,
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
    error: ClassVar[BaseException | None] = None

    def __init__(self, language: str, *args: Any, **kwargs: Any) -> None:
        self.language = language

    def show_ram_test(self, allow_start: bool = True) -> None:
        FakeMenu.calls.append(("show_ram_test", allow_start))

    def run(self) -> None:
        FakeMenu.calls.append("run")
        if FakeMenu.error:
            raise FakeMenu.error


@pytest.fixture
def fake_menu(monkeypatch: pytest.MonkeyPatch) -> type[FakeMenu]:
    FakeMenu.calls = []
    FakeMenu.error = None
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


def test_logging_is_set_up_once_at_the_start(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_setup() -> None:
        calls.append("setup")

    main(
        is_admin_fn=lambda: True,
        input_fn=lambda prompt: "0" if prompt.startswith("Choose") else "",
        print_fn=lambda text: None,
        config_path=tmp_path / "config.json",
        color=False,
        argv=[],
        setup_logging_fn=fake_setup,
    )
    assert calls == ["setup"]


def test_an_unexpected_error_shows_a_friendly_message_with_the_log_path(
    tmp_path: Path, fake_menu: type[FakeMenu], caplog: pytest.LogCaptureFixture
) -> None:
    fake_menu.error = RuntimeError("a bug")
    log_file = tmp_path / "checkup.log"
    code, printed, _ = run_main([""], tmp_path, admin=True, log_path=log_file)
    assert code == 1
    assert any("Something unexpected went wrong" in line and str(log_file) in line for line in printed)
    assert not any("RuntimeError" in line or "Traceback" in line for line in printed)
    assert "Unexpected error" in caplog.text


def test_an_unexpected_error_without_a_log_file_says_so(
    tmp_path: Path, fake_menu: type[FakeMenu]
) -> None:
    fake_menu.error = RuntimeError("a bug")
    code, printed, _ = run_main([""], tmp_path, admin=True, log_path=None)
    assert code == 1
    assert any("could not be saved" in line for line in printed)


def test_the_window_still_waits_for_enter_after_an_error(
    tmp_path: Path, fake_menu: type[FakeMenu]
) -> None:
    fake_menu.error = RuntimeError("a bug")
    prompts: list[str] = []

    def record(prompt: str) -> str:
        prompts.append(prompt)
        return ""

    main(
        is_admin_fn=lambda: True,
        input_fn=record,
        print_fn=lambda text: None,
        config_path=tmp_path / "config.json",
        color=False,
        argv=[],
        setup_logging_fn=lambda: None,
    )
    assert prompts == ["Press Enter to close this window..."]


@pytest.mark.parametrize("error", [KeyboardInterrupt(), EOFError()])
def test_ctrl_c_and_closed_input_end_politely_without_an_error(
    tmp_path: Path, fake_menu: type[FakeMenu], error: BaseException
) -> None:
    fake_menu.error = error
    code, printed, _ = run_main([""], tmp_path, admin=True)
    assert code == 0
    assert "Interrupted. Goodbye!" in printed


def test_a_second_ctrl_c_at_the_final_prompt_does_not_crash(
    tmp_path: Path, fake_menu: type[FakeMenu]
) -> None:
    def interrupted(prompt: str) -> str:
        raise KeyboardInterrupt

    code = main(
        is_admin_fn=lambda: True,
        input_fn=interrupted,
        print_fn=lambda text: None,
        config_path=tmp_path / "config.json",
        color=False,
        argv=[],
        setup_logging_fn=lambda: None,
    )
    assert code == 0


def test_declined_uac_does_not_crash_if_the_final_prompt_is_interrupted(tmp_path: Path) -> None:
    def interrupted(prompt: str) -> str:
        raise EOFError

    code = main(
        is_admin_fn=lambda: False,
        relaunch_fn=lambda: False,
        input_fn=interrupted,
        print_fn=lambda text: None,
        config_path=tmp_path / "config.json",
        color=False,
        argv=[],
        setup_logging_fn=lambda: None,
    )
    assert code == 1