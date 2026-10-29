import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from pc_checkup.models import EventKind
from pc_checkup.sources.base import SourceError
from pc_checkup.sources.bsod import BsodSource, build_events_script, parse_events

FIXTURES = Path(__file__).parent / "fixtures"


def real_output() -> str:
    return (FIXTURES / "bsod_events_real.json").read_text(encoding="utf-8")


def make_source(
    output: str, tmp_path: Path, now: datetime | None = None
) -> tuple[BsodSource, list[str]]:
    scripts: list[str] = []

    def fake_run(script: str) -> str:
        scripts.append(script)
        return output

    source = BsodSource(
        days=15,
        run_fn=fake_run,
        minidump_dir=tmp_path / "Minidump",
        memory_dump=tmp_path / "MEMORY.DMP",
        now_fn=lambda: now or datetime(2026, 10, 29, 12, 0),
    )
    return source, scripts


def test_real_log_is_parsed(tmp_path: Path) -> None:
    source, _ = make_source(real_output(), tmp_path)
    snapshot = source.fetch()
    crashes = snapshot.of_kind(EventKind.BUGCHECK)
    assert len(crashes) == 1
    assert crashes[0].bugcheck_code == 0x1A
    assert len(snapshot.of_kind(EventKind.UNEXPECTED_SHUTDOWN)) == 3
    assert snapshot.of_kind(EventKind.HARDWARE_ERROR) == ()


def test_kernel_power_bugcheck_code_is_read_in_decimal(tmp_path: Path) -> None:
    events = parse_events(real_output())
    shutdowns = [e for e in events if e.kind is EventKind.UNEXPECTED_SHUTDOWN]
    assert [e.bugcheck_code for e in shutdowns] == [0x1A, 0x7E, None]


def test_empty_output_means_no_events(tmp_path: Path) -> None:
    for output in ("", "  \n", "[]"):
        source, _ = make_source(output, tmp_path)
        assert source.fetch().events == ()


def test_script_receives_the_number_of_days(tmp_path: Path) -> None:
    source, scripts = make_source("[]", tmp_path)
    source.fetch()
    assert scripts[0].startswith("$days = 15\n")
    assert build_events_script(3).startswith("$days = 3\n")


def test_whea_event_is_hardware_error() -> None:
    raw = [
        {
            "Time": "2026-10-28T10:00:00.000-03:00",
            "Id": 17,
            "Provider": "Microsoft-Windows-WHEA-Logger",
            "Props": ["x", "y"],
        }
    ]
    events = parse_events(json.dumps(raw))
    assert events[0].kind is EventKind.HARDWARE_ERROR
    assert events[0].details == "x | y"


def test_unknown_event_is_ignored() -> None:
    raw = [{"Time": "2026-10-28T10:00:00.000-03:00", "Id": 7, "Provider": "Other", "Props": []}]
    assert parse_events(json.dumps(raw)) == ()


@pytest.mark.parametrize("output", ["{ not json", '[{"Id": 1}]', '"text"'])
def test_garbage_output_raises_source_error(output: str) -> None:
    with pytest.raises(SourceError):
        parse_events(output)


def test_dump_files_only_recent_ones(tmp_path: Path) -> None:
    now = datetime(2026, 10, 29, 12, 0)
    minidumps = tmp_path / "Minidump"
    minidumps.mkdir()
    recent = minidumps / "recent.dmp"
    old = minidumps / "old.dmp"
    recent.write_text("x")
    old.write_text("x")
    (minidumps / "notes.txt").write_text("x")
    old_time = (now - timedelta(days=40)).timestamp()
    os.utime(old, (old_time, old_time))
    recent_time = (now - timedelta(days=1)).timestamp()
    os.utime(recent, (recent_time, recent_time))
    memory = tmp_path / "MEMORY.DMP"
    memory.write_text("x")
    os.utime(memory, (recent_time, recent_time))

    source, _ = make_source("[]", tmp_path, now=now)
    assert source.fetch().dump_files == (str(recent), str(memory))


def test_missing_dump_locations_are_fine(tmp_path: Path) -> None:
    source, _ = make_source("[]", tmp_path)
    assert source.fetch().dump_files == ()
