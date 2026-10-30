import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from pc_checkup import autostart
from pc_checkup.actions import ram_test
from pc_checkup.actions.base import ActionError
from pc_checkup.actions.ram_test import RESTART_DELAY_SECONDS, RamTestAction
from pc_checkup.models import Level

NOW = datetime(2026, 10, 30, 10, 15, tzinfo=timezone(timedelta(hours=-3)))


class Recorder:
    """Fake system calls that record the order they were made in."""

    def __init__(
        self,
        tmp_path: Path,
        register_error: Exception | None = None,
        schedule_error: Exception | None = None,
        restart_error: Exception | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.restart_comments: list[str] = []

        def register() -> None:
            self.calls.append("register")
            if register_error:
                raise register_error

        def schedule() -> None:
            self.calls.append("schedule")
            if schedule_error:
                raise schedule_error

        def restart(comment: str) -> None:
            self.calls.append("restart")
            self.restart_comments.append(comment)
            if restart_error:
                raise restart_error

        self.action = RamTestAction(
            schedule_fn=schedule,
            restart_fn=restart,
            register_fn=register,
            unregister_fn=lambda: self.calls.append("unregister"),
            state_path=tmp_path / "state.json",
            now_fn=lambda: NOW,
        )


def test_restart_delay_is_fifteen_seconds() -> None:
    assert RESTART_DELAY_SECONDS == 15


def test_run_registers_schedules_then_restarts_in_that_order(tmp_path: Path) -> None:
    system = Recorder(tmp_path)
    lines = system.action.run("en")
    assert system.calls == ["register", "schedule", "restart"]
    assert system.action.pending_since() == NOW
    assert "restart in 15 seconds" in lines[0].text
    assert "shutdown /a" in lines[0].text
    assert "opens by itself" in lines[1].text
    assert system.restart_comments == [
        "PC Checkup: restarting to run the Windows Memory Diagnostic."
    ]


def test_the_pc_is_never_restarted_before_the_test_is_scheduled(tmp_path: Path) -> None:
    system = Recorder(tmp_path, schedule_error=OSError("bcdedit failed"))
    with pytest.raises(ActionError):
        system.action.run("en")
    assert "restart" not in system.calls


def test_failed_schedule_rolls_everything_back(tmp_path: Path) -> None:
    system = Recorder(tmp_path, schedule_error=OSError("bcdedit failed"))
    with pytest.raises(ActionError) as error:
        system.action.run("en")
    assert error.value.key == "ram_test.schedule_failed"
    assert system.action.pending_since() is None
    assert system.calls == ["register", "schedule", "unregister"]


def test_failed_autostart_does_not_block_the_test_but_tells_the_user(tmp_path: Path) -> None:
    system = Recorder(tmp_path, register_error=PermissionError())
    lines = system.action.run("en")
    assert system.calls == ["register", "schedule", "restart"]
    assert "could not set itself to open" in lines[1].text


def test_failed_restart_keeps_the_test_scheduled_and_the_record(tmp_path: Path) -> None:
    system = Recorder(tmp_path, restart_error=OSError("shutdown failed"))
    with pytest.raises(ActionError) as error:
        system.action.run("en")
    assert error.value.key == "ram_test.restart_failed"
    assert system.action.pending_since() == NOW
    assert "unregister" not in system.calls


def test_unwritable_state_stops_before_anything_is_changed(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder")
    system = Recorder(tmp_path)
    action = RamTestAction(
        schedule_fn=lambda: system.calls.append("schedule"),
        restart_fn=lambda comment: system.calls.append("restart"),
        register_fn=lambda: system.calls.append("register"),
        state_path=blocker / "state.json",
        now_fn=lambda: NOW,
    )
    with pytest.raises(ActionError):
        action.run("en")
    assert system.calls == []


def test_clear_pending(tmp_path: Path) -> None:
    system = Recorder(tmp_path)
    system.action.run("en")
    system.action.clear_pending()
    assert system.action.pending_since() is None


def test_describe_and_warning_explain_the_restart_the_delay_and_the_duration() -> None:
    action = RamTestAction()
    assert "restarts your PC automatically" in action.describe("en")
    warning = action.warning("en")
    assert "restarts 15 seconds after you confirm" in warning
    assert "10 to 20 minutes" in warning
    assert "Unsaved work will be lost" in warning
    assert "15 segundos" in action.warning("pt")


def test_declined_flow_changes_nothing_and_never_restarts(tmp_path: Path) -> None:
    system = Recorder(tmp_path)
    shown: list[str] = []
    ran = system.action.execute("en", lambda text, level: shown.append(text), lambda prompt: False)
    assert ran is False
    assert system.calls == []
    assert system.action.pending_since() is None
    assert shown[-1] == "Cancelled. Nothing was changed on your PC."


def test_accepted_flow_warns_before_it_restarts(tmp_path: Path) -> None:
    system = Recorder(tmp_path)
    shown: list[tuple[str, Level]] = []
    ran = system.action.execute("en", lambda text, level: shown.append((text, level)), lambda prompt: True)
    assert ran is True
    assert system.calls == ["register", "schedule", "restart"]
    assert "Unsaved work will be lost" in shown[1][0]


def test_failure_is_shown_in_red(tmp_path: Path) -> None:
    system = Recorder(tmp_path, schedule_error=OSError())
    shown: list[tuple[str, Level]] = []
    system.action.execute("en", lambda text, level: shown.append((text, level)), lambda prompt: True)
    assert shown[-1][1] is Level.ERROR
    assert "your PC was not restarted" in shown[-1][0]


class FakeRun:
    def __init__(self, returncode: int = 0, error: Exception | None = None) -> None:
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.returncode = returncode
        self.error = error

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((command, kwargs))
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(command, self.returncode, stdout=b"", stderr=b"")


def test_schedule_runs_bcdedit_for_the_next_boot_only(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun()
    monkeypatch.setattr(subprocess, "run", fake)
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    ram_test.schedule_memory_test()
    command, kwargs = fake.calls[0]
    assert Path(command[0]).name == "bcdedit.exe"
    assert command[1:] == ["/bootsequence", "{memdiag}", "/addfirst"]
    assert "shell" not in kwargs
    assert kwargs["timeout"] > 0


def test_restart_uses_a_short_delay_and_a_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun()
    monkeypatch.setattr(subprocess, "run", fake)
    ram_test.restart_pc("why")
    command, kwargs = fake.calls[0]
    assert Path(command[0]).name == "shutdown.exe"
    assert command[1:] == ["/r", "/t", "15", "/c", "why"]
    assert "shell" not in kwargs


@pytest.mark.parametrize(
    "fake",
    [FakeRun(returncode=1), FakeRun(error=subprocess.TimeoutExpired("x", 30)), FakeRun(error=FileNotFoundError())],
)
def test_a_failing_command_becomes_an_oserror(monkeypatch: pytest.MonkeyPatch, fake: FakeRun) -> None:
    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(OSError):
        ram_test.schedule_memory_test()


def test_register_reopen_passes_the_argument_that_shows_the_result(monkeypatch: pytest.MonkeyPatch) -> None:
    registered: list[str] = []
    monkeypatch.setattr(autostart, "register_after_reboot", registered.append)
    ram_test.register_reopen()
    assert registered[0].endswith("-m pc_checkup --show-ram-result")
