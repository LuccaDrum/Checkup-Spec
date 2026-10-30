import subprocess
from pathlib import Path

import pytest

from pc_checkup.actions.base import ActionError
from pc_checkup.actions.dism import DismAction
from pc_checkup.actions.repair import REPAIR_TIMEOUT_SECONDS, RepairAction
from pc_checkup.actions.sfc import SfcAction
from pc_checkup.messages import MESSAGES
from pc_checkup.models import Level, Line


class FakeRunner:
    def __init__(self, code: int = 0, error: Exception | None = None) -> None:
        self.code = code
        self.error = error
        self.calls: list[tuple[list[str], int]] = []

    def __call__(self, command: list[str], timeout: int) -> int:
        self.calls.append((command, timeout))
        if self.error:
            raise self.error
        return self.code


def texts(lines: list[Line]) -> list[str]:
    return [line.text for line in lines]


def test_sfc_command_and_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    action = SfcAction()
    assert [Path(action.command()[0]).name, *action.command()[1:]] == ["sfc.exe", "/scannow"]
    assert action.log_path() == Path(r"C:\Windows\Logs\CBS\CBS.log")


def test_dism_command_and_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    action = DismAction()
    assert [Path(action.command()[0]).name, *action.command()[1:]] == [
        "dism.exe",
        "/Online",
        "/Cleanup-Image",
        "/RestoreHealth",
    ]
    assert action.log_path() == Path(r"C:\Windows\Logs\DISM\dism.log")


def test_runs_with_a_generous_timeout() -> None:
    runner = FakeRunner()
    SfcAction(run_fn=runner).run("en")
    assert runner.calls[0][1] == REPAIR_TIMEOUT_SECONDS
    assert REPAIR_TIMEOUT_SECONDS >= 3600


def test_sfc_success_is_green_and_has_no_technical_lines() -> None:
    lines = SfcAction(run_fn=FakeRunner(0)).run("en")
    assert len(lines) == 1
    assert lines[0].level is Level.OK
    assert lines[0].text.startswith("SFC finished without reporting an error")


def test_sfc_any_other_code_is_a_red_failure_with_technical_lines() -> None:
    lines = SfcAction(run_fn=FakeRunner(1)).run("en")
    assert lines[0].level is Level.ERROR
    assert "could not finish the scan" in lines[0].text
    assert [line.level for line in lines[1:]] == [Level.TECHNICAL, Level.TECHNICAL]
    assert lines[1].text == "Exit code: 1 (hex 0x00000001)"
    assert "CBS.log" in lines[2].text


@pytest.mark.parametrize(
    ("code", "fragment", "level"),
    [
        (0, "finished successfully", Level.OK),
        (3010, "needs a restart", Level.LOG),
        (0x800F081F, "could not find the files", Level.ERROR),
        (0x800F0906, "could not download", Level.ERROR),
        (0x800F0907, "company policy", Level.ERROR),
        (5, "denied permission", Level.ERROR),
        (740, "denied permission", Level.ERROR),
        (1639, "could not be completed", Level.ERROR),
    ],
)
def test_dism_exit_codes(code: int, fragment: str, level: Level) -> None:
    lines = DismAction(run_fn=FakeRunner(code)).run("en")
    assert fragment in lines[0].text
    assert lines[0].level is level


def test_dism_reboot_needed_is_a_success_and_never_restarts_by_itself() -> None:
    lines = DismAction(run_fn=FakeRunner(3010)).run("en")
    assert len(lines) == 1
    assert "Restart the PC when you are ready" in lines[0].text


def test_dism_failure_shows_the_code_in_hex_and_the_log() -> None:
    lines = DismAction(run_fn=FakeRunner(0x800F081F)).run("en")
    assert lines[1].text == "Exit code: 2148468767 (hex 0x800f081f)"
    assert "dism.log" in lines[2].text


def test_portuguese() -> None:
    lines = DismAction(run_fn=FakeRunner(0x800F0906)).run("pt")
    assert "não conseguiu baixar" in lines[0].text
    assert lines[1].text.startswith("Código de saída:")


def test_timeout_is_an_action_error() -> None:
    runner = FakeRunner(error=subprocess.TimeoutExpired("sfc", 1))
    with pytest.raises(ActionError) as error:
        SfcAction(run_fn=runner).run("en")
    assert error.value.key == "repair.timeout"


def test_missing_tool_is_an_action_error() -> None:
    with pytest.raises(ActionError) as error:
        DismAction(run_fn=FakeRunner(error=FileNotFoundError())).run("en")
    assert error.value.key == "repair.not_found"


@pytest.mark.parametrize("action_type", [SfcAction, DismAction])
def test_every_message_the_action_can_show_exists_in_both_languages(
    action_type: type[RepairAction],
) -> None:
    keys = {f"{action_type.prefix}.describe", f"{action_type.prefix}.warning"}
    keys |= {outcome.message_key for outcome in action_type.outcomes.values()}
    keys.add(action_type.unknown_outcome.message_key)
    for language in MESSAGES:
        assert keys <= set(MESSAGES[language])


@pytest.mark.parametrize("action_type", [SfcAction, DismAction])
def test_describe_and_warning_explain_duration_and_not_to_turn_the_pc_off(
    action_type: type[RepairAction],
) -> None:
    action = action_type()
    assert action.describe("en")
    assert "10 to 20 minutes" in action.warning("en")
    assert "Do not turn off" in action.warning("en")
    assert "10 a 20 minutos" in action.warning("pt")


def test_the_flow_asks_before_running_and_declining_runs_nothing() -> None:
    runner = FakeRunner()
    shown: list[str] = []
    ran = SfcAction(run_fn=runner).execute(
        "en", lambda text, level: shown.append(text), lambda prompt: False
    )
    assert ran is False
    assert runner.calls == []
    assert shown[-1] == "Cancelled. Nothing was changed on your PC."


def test_the_flow_runs_once_when_confirmed() -> None:
    runner = FakeRunner()
    shown: list[tuple[str, Level]] = []
    ran = DismAction(run_fn=runner).execute(
        "en", lambda text, level: shown.append((text, level)), lambda prompt: True
    )
    assert ran is True
    assert len(runner.calls) == 1
    assert shown[-1][1] is Level.OK


def test_a_timeout_in_the_flow_is_shown_in_red() -> None:
    runner = FakeRunner(error=subprocess.TimeoutExpired("dism", 1))
    shown: list[tuple[str, Level]] = []
    DismAction(run_fn=runner).execute(
        "en", lambda text, level: shown.append((text, level)), lambda prompt: True
    )
    assert shown[-1][1] is Level.ERROR
    assert "took too long" in shown[-1][0]
