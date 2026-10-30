import pytest

from pc_checkup.actions.base import Action, ActionError
from pc_checkup.models import Level, Line


class FakeAction(Action):
    def __init__(self, error: ActionError | None = None) -> None:
        self.ran = 0
        self._error = error

    def describe(self, language: str) -> str:
        return "what it does"

    def warning(self, language: str) -> str:
        return "how long and how risky"

    def run(self, language: str) -> list[Line]:
        self.ran += 1
        if self._error:
            raise self._error
        return [Line("done", Level.OK)]


def run_flow(action: Action, answer: bool, language: str = "en") -> tuple[bool, list[tuple[str, Level]], list[str]]:
    shown: list[tuple[str, Level]] = []
    prompts: list[str] = []

    def confirm(prompt: str) -> bool:
        prompts.append(prompt)
        return answer

    ran = action.execute(language, lambda text, level: shown.append((text, level)), confirm)
    return ran, shown, prompts


def test_cannot_instantiate_without_the_steps() -> None:
    with pytest.raises(TypeError):
        Action()  # type: ignore[abstract]


def test_flow_is_describe_warn_confirm_run() -> None:
    action = FakeAction()
    ran, shown, prompts = run_flow(action, answer=True)
    assert ran is True
    assert action.ran == 1
    assert [text for text, _ in shown] == ["what it does", "how long and how risky", "done"]
    assert prompts == ["Do you want to continue? (y/n): "]


def test_declining_never_runs_the_action() -> None:
    action = FakeAction()
    ran, shown, _ = run_flow(action, answer=False)
    assert ran is False
    assert action.ran == 0
    assert shown[-1][0] == "Cancelled. Nothing was changed on your PC."


def test_describe_and_warning_come_before_the_question() -> None:
    order: list[str] = []

    def ask(prompt: str) -> bool:
        order.append("ASK")
        return False

    FakeAction().execute("en", lambda text, level: order.append(text), ask)
    assert order[:3] == ["what it does", "how long and how risky", "ASK"]


def test_a_failing_action_shows_a_red_message_and_returns_false() -> None:
    action = FakeAction(error=ActionError())
    ran, shown, _ = run_flow(action, answer=True)
    assert ran is False
    assert shown[-1] == ("Something went wrong and the action could not be completed.", Level.ERROR)


def test_error_can_carry_its_own_message_key() -> None:
    action = FakeAction(error=ActionError("ram_test.launch_failed"))
    _, shown, _ = run_flow(action, answer=True)
    assert shown[-1] == ("The Windows Memory Diagnostic could not be started.", Level.ERROR)


def test_flow_speaks_portuguese() -> None:
    _, _, prompts = run_flow(FakeAction(), answer=True, language="pt")
    assert prompts == ["Deseja continuar? (s/n): "]
