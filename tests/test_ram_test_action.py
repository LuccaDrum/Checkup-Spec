import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from pc_checkup.actions import ram_test
from pc_checkup.actions.base import ActionError
from pc_checkup.actions.ram_test import RamTestAction
from pc_checkup.models import Level

NOW = datetime(2026, 10, 30, 10, 15, tzinfo=timezone(timedelta(hours=-3)))


def make_action(tmp_path: Path, launch_error: Exception | None = None) -> tuple[RamTestAction, list[str]]:
    launched: list[str] = []

    def fake_launch() -> None:
        if launch_error:
            raise launch_error
        launched.append("mdsched")

    action = RamTestAction(launch_fn=fake_launch, state_path=tmp_path / "state.json", now_fn=lambda: NOW)
    return action, launched


def test_run_launches_the_test_and_records_it_as_pending(tmp_path: Path) -> None:
    action, launched = make_action(tmp_path)
    lines = action.run("en")
    assert launched == ["mdsched"]
    assert action.pending_since() == NOW
    assert lines[0].level is Level.LOG
    assert "choose option 4" in lines[0].text


def test_failed_launch_leaves_no_pending_record(tmp_path: Path) -> None:
    action, _ = make_action(tmp_path, launch_error=FileNotFoundError())
    with pytest.raises(ActionError) as error:
        action.run("en")
    assert error.value.key == "ram_test.launch_failed"
    assert action.pending_since() is None


def test_unwritable_state_stops_before_launching(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder")
    launched: list[str] = []
    action = RamTestAction(
        launch_fn=lambda: launched.append("mdsched"),
        state_path=blocker / "state.json",
        now_fn=lambda: NOW,
    )
    with pytest.raises(ActionError):
        action.run("en")
    assert launched == []


def test_clear_pending(tmp_path: Path) -> None:
    action, _ = make_action(tmp_path)
    action.run("en")
    action.clear_pending()
    assert action.pending_since() is None


def test_describe_and_warning_explain_the_restart_and_the_duration() -> None:
    action = RamTestAction()
    assert "restart" in action.describe("en")
    assert "10 to 20 minutes" in action.warning("en")
    assert "nunca reinicia" in action.warning("pt")


def test_full_flow_declined_does_nothing(tmp_path: Path) -> None:
    action, launched = make_action(tmp_path)
    shown: list[str] = []
    ran = action.execute("en", lambda text, level: shown.append(text), lambda prompt: False)
    assert ran is False
    assert launched == []
    assert action.pending_since() is None
    assert shown[-1] == "Cancelled. Nothing was changed on your PC."


def test_full_flow_accepted_launches_once(tmp_path: Path) -> None:
    action, launched = make_action(tmp_path)
    ran = action.execute("en", lambda text, level: None, lambda prompt: True)
    assert ran is True
    assert launched == ["mdsched"]


def test_launch_mdsched_starts_the_windows_tool_without_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_popen(command: list[str], **kwargs: Any) -> None:
        calls.append((command, kwargs))

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    ram_test.launch_mdsched()
    command, kwargs = calls[0]
    assert Path(command[0]).name == "mdsched.exe"
    assert "shell" not in kwargs
