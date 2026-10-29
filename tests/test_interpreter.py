from datetime import datetime, timedelta
from pathlib import Path

from pc_checkup.interpreter import BUGCHECK_NAMES, group_crashes, interpret_bsod
from pc_checkup.messages import MESSAGES, get_message
from pc_checkup.models import BsodSnapshot, EventKind, SystemEvent
from pc_checkup.sources.bsod import parse_events

FIXTURES = Path(__file__).parent / "fixtures"
START = datetime(2026, 10, 29, 8, 0)


def event(kind: EventKind, minutes: float = 0, code: int | None = None) -> SystemEvent:
    event_id = {
        EventKind.BUGCHECK: 1001,
        EventKind.UNEXPECTED_SHUTDOWN: 41,
        EventKind.HARDWARE_ERROR: 17,
    }[kind]
    return SystemEvent(
        time=START + timedelta(minutes=minutes), kind=kind, event_id=event_id, bugcheck_code=code
    )


def snapshot(*events: SystemEvent, dumps: tuple[str, ...] = ()) -> BsodSnapshot:
    return BsodSnapshot(days=15, events=tuple(events), dump_files=dumps)


def real_snapshot() -> BsodSnapshot:
    text = (FIXTURES / "bsod_events_real.json").read_text(encoding="utf-8")
    return BsodSnapshot(days=15, events=parse_events(text), dump_files=())


def test_every_known_bugcheck_has_a_message_in_every_language() -> None:
    for language in MESSAGES:
        for name in BUGCHECK_NAMES.values():
            assert get_message(f"bugcheck.{name}", language)


def test_bugcheck_and_kernel_power_of_one_crash_count_once() -> None:
    crashes = group_crashes(
        snapshot(
            event(EventKind.UNEXPECTED_SHUTDOWN, 0, 0x1A),
            event(EventKind.BUGCHECK, 0.5, 0x1A),
        )
    )
    assert len(crashes) == 1


def test_same_code_far_apart_counts_twice() -> None:
    crashes = group_crashes(
        snapshot(event(EventKind.BUGCHECK, 0, 0x1A), event(EventKind.BUGCHECK, 60, 0x1A))
    )
    assert len(crashes) == 2


def test_different_codes_close_together_count_twice() -> None:
    crashes = group_crashes(
        snapshot(event(EventKind.BUGCHECK, 0, 0x1A), event(EventKind.BUGCHECK, 1, 0x50))
    )
    assert len(crashes) == 2


def test_no_problems() -> None:
    report = interpret_bsod(snapshot(), "en")
    assert report.friendly[0].startswith("Good news")
    assert report.friendly[-1] == "Result: nothing to worry about."
    assert "No recent dump files found." in report.technical


def test_real_log_in_english() -> None:
    report = interpret_bsod(real_snapshot(), "en")
    assert report.friendly[0] == "Your PC crashed 2 times in the last 15 days."
    assert any("Memory management error" in line for line in report.friendly)
    assert any("1 unexpected shutdown without a crash code" in line for line in report.friendly)
    assert any("RAM test (option 4)" in line for line in report.friendly)
    assert report.friendly[-1].startswith("Result: worth keeping an eye on")


def test_real_log_in_portuguese() -> None:
    report = interpret_bsod(real_snapshot(), "pt")
    assert report.friendly[0] == "Seu PC travou 2 vezes nos últimos 15 dias."
    assert report.technical[0] == "Detalhes técnicos:"


def test_single_crash_uses_singular() -> None:
    report = interpret_bsod(snapshot(event(EventKind.BUGCHECK, 0, 0x3B)), "en")
    assert report.friendly[0] == "Your PC crashed once in the last 15 days."
    assert not any("RAM test" in line for line in report.friendly)


def test_unknown_code_gets_generic_message_and_raw_code_in_technical() -> None:
    report = interpret_bsod(snapshot(event(EventKind.BUGCHECK, 0, 0x9999)), "en")
    assert any("0x9999" in line and "not in our list" in line for line in report.friendly)
    assert any("code=0x9999" in line for line in report.technical)


def test_known_code_shows_its_name_in_technical() -> None:
    report = interpret_bsod(snapshot(event(EventKind.BUGCHECK, 0, 0x1A)), "en")
    assert any("code=0x1a MEMORY_MANAGEMENT" in line for line in report.technical)


def test_hardware_errors_hint_at_memory() -> None:
    report = interpret_bsod(snapshot(event(EventKind.HARDWARE_ERROR)), "en")
    assert any("hardware error report" in line for line in report.friendly)
    assert any("RAM test" in line for line in report.friendly)


def test_three_crashes_need_attention() -> None:
    events = [event(EventKind.BUGCHECK, minutes, 0x3B) for minutes in (0, 60, 120)]
    report = interpret_bsod(snapshot(*events), "en")
    assert report.friendly[0] == "Your PC crashed 3 times in the last 15 days."
    assert report.friendly[-1].startswith("Result: your PC crashes often")


def test_dump_files_are_listed() -> None:
    report = interpret_bsod(snapshot(dumps=("C:\\Windows\\MEMORY.DMP",)), "en")
    assert "Dump file: C:\\Windows\\MEMORY.DMP" in report.technical
