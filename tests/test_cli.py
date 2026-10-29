from collections.abc import Iterator
from pathlib import Path

from pc_checkup.cli import main


def run_main(
    answers: list[str], tmp_path: Path, *, admin: bool, relaunch_ok: bool = True
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
