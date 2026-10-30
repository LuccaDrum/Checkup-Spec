from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pc_checkup.models import RamOutcome
from pc_checkup.sources.base import SourceError
from pc_checkup.sources.ram_result import RESULTS_SCRIPT, RamResultSource, parse_results

FIXTURES = Path(__file__).parent / "fixtures"
BRT = timezone(timedelta(hours=-3))


def sample_output() -> str:
    """Hand-made sample: this PC has never run the memory test, so there is no real capture."""
    return (FIXTURES / "ram_events_sample.json").read_text(encoding="utf-8")


def test_event_ids_map_to_outcomes() -> None:
    results = parse_results(sample_output())
    assert [(r.event_id, r.outcome) for r in results] == [
        (1201, RamOutcome.NO_ERRORS),
        (1202, RamOutcome.ERRORS_FOUND),
        (1102, RamOutcome.ERRORS_FOUND),
    ]


def test_latest_result_is_the_newest() -> None:
    snapshot = RamResultSource(run_fn=lambda script: sample_output()).fetch()
    assert snapshot.latest is not None
    assert snapshot.latest.event_id == 1201
    assert snapshot.latest.outcome is RamOutcome.NO_ERRORS


def test_since_ignores_older_results() -> None:
    since = datetime(2026, 10, 26, tzinfo=BRT)
    source = RamResultSource(run_fn=lambda script: sample_output(), since=since)
    assert source.fetch().latest is None


def test_since_keeps_newer_results() -> None:
    since = datetime(2026, 10, 24, tzinfo=BRT)
    source = RamResultSource(run_fn=lambda script: sample_output(), since=since)
    assert source.fetch().latest is not None


def test_naive_since_is_treated_as_local_time() -> None:
    source = RamResultSource(run_fn=lambda script: "[]", since=datetime(2026, 1, 1))
    assert source.fetch().latest is None


@pytest.mark.parametrize("output", ["", "  \n", "[]"])
def test_no_results_means_no_latest(output: str) -> None:
    assert RamResultSource(run_fn=lambda script: output).fetch().latest is None


def test_unknown_event_id_is_ignored() -> None:
    output = '[{"Time": "2026-10-25T09:12:40.120-03:00", "Id": 9999}]'
    assert parse_results(output) == ()


def test_single_object_is_accepted() -> None:
    output = '{"Time": "2026-10-25T09:12:40.120-03:00", "Id": 1101}'
    assert len(parse_results(output)) == 1


@pytest.mark.parametrize("output", ["{ not json", '[{"Id": 1201}]', '"text"', "[1]"])
def test_garbage_raises_source_error(output: str) -> None:
    with pytest.raises(SourceError):
        parse_results(output)


def test_fetch_runs_the_results_script() -> None:
    scripts: list[str] = []

    def fake_run(script: str) -> str:
        scripts.append(script)
        return "[]"

    RamResultSource(run_fn=fake_run).fetch()
    assert scripts == [RESULTS_SCRIPT]
