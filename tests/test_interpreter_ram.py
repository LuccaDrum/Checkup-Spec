from datetime import datetime

from pc_checkup.interpreter import interpret_ram
from pc_checkup.models import Level, RamOutcome, RamSnapshot, RamTestResult, Report

WHEN = datetime(2026, 10, 25, 9, 12)


def snapshot(outcome: RamOutcome | None) -> RamSnapshot:
    if outcome is None:
        return RamSnapshot(latest=None)
    return RamSnapshot(latest=RamTestResult(time=WHEN, outcome=outcome, event_id=1201))


def texts(report: Report) -> list[str]:
    return [line.text for line in report.friendly]


def test_no_result_yet() -> None:
    report = interpret_ram(snapshot(None), "en")
    assert texts(report)[0].startswith("No RAM test result was found.")
    assert texts(report)[-1] == "Result: nothing to report yet."
    assert report.technical == ()


def test_no_errors_found() -> None:
    report = interpret_ram(snapshot(RamOutcome.NO_ERRORS), "en")
    assert texts(report) == [
        "The last RAM test (2026-10-25 09:12) found no errors.",
        "Result: the memory looked fine in the last test.",
    ]
    assert report.friendly[-1].level is Level.OK


def test_errors_found_are_red_and_advise_backup() -> None:
    report = interpret_ram(snapshot(RamOutcome.ERRORS_FOUND), "en")
    assert report.friendly[0].level is Level.ERROR
    assert "found memory errors" in report.friendly[0].text
    assert "Back up your files" in report.friendly[-1].text


def test_portuguese() -> None:
    report = interpret_ram(snapshot(RamOutcome.NO_ERRORS), "pt")
    assert texts(report)[0] == "O último teste de RAM (2026-10-25 09:12) não encontrou erros."
