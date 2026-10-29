"""Turns raw snapshots into friendly text plus technical details."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from pc_checkup.messages import get_message
from pc_checkup.models import BsodSnapshot, EventKind, Level, Line, Report

# All thresholds in one place.
THRESHOLDS = {
    "same_crash_window_seconds": 120,
    "crashes_attention": 3,
}

BUGCHECK_NAMES: dict[int, str] = {
    0x0A: "IRQL_NOT_LESS_OR_EQUAL",
    0x1A: "MEMORY_MANAGEMENT",
    0x3B: "SYSTEM_SERVICE_EXCEPTION",
    0x50: "PAGE_FAULT_IN_NONPAGED_AREA",
    0x7A: "KERNEL_DATA_INPAGE_ERROR",
    0x7E: "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
    0xD1: "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
    0x124: "WHEA_UNCORRECTABLE_ERROR",
}

VERDICT_LEVELS = {"ok": Level.OK, "warning": Level.LOG, "attention": Level.LOG}

# Crash codes that suggest a RAM problem.
MEMORY_RELATED_CODES = {0x1A, 0x50, 0x7A, 0x124}


@dataclass(frozen=True)
class Crash:
    time: datetime
    code: int


def group_crashes(snapshot: BsodSnapshot) -> tuple[Crash, ...]:
    """One crash can log several events (1001 and 41); count it once, newest first."""
    window = timedelta(seconds=THRESHOLDS["same_crash_window_seconds"])
    signals = sorted(
        (
            event
            for event in snapshot.events
            if event.bugcheck_code is not None
            and event.kind in (EventKind.BUGCHECK, EventKind.UNEXPECTED_SHUTDOWN)
        ),
        key=lambda event: event.time,
    )
    crashes: list[Crash] = []
    for event in signals:
        assert event.bugcheck_code is not None
        last = crashes[-1] if crashes else None
        if last and last.code == event.bugcheck_code and event.time - last.time <= window:
            continue
        crashes.append(Crash(event.time, event.bugcheck_code))
    return tuple(reversed(crashes))


def _code_label(code: int | None) -> str:
    if code is None:
        return "-"
    name = BUGCHECK_NAMES.get(code)
    return f"{code:#x} {name}" if name else f"{code:#x}"


def _explain(code: int, language: str) -> str:
    name = BUGCHECK_NAMES.get(code)
    if name is None:
        return get_message("bugcheck.unknown", language, code=f"{code:#x}")
    return get_message(f"bugcheck.{name}", language)


def _plural(key: str, count: int, language: str, **values: object) -> str:
    suffix = "one" if count == 1 else "many"
    return get_message(f"{key}.{suffix}", language, count=count, **values)


def interpret_bsod(snapshot: BsodSnapshot, language: str) -> Report:
    crashes = group_crashes(snapshot)
    shutdowns = [
        event
        for event in snapshot.of_kind(EventKind.UNEXPECTED_SHUTDOWN)
        if event.bugcheck_code is None
    ]
    hardware = snapshot.of_kind(EventKind.HARDWARE_ERROR)

    friendly: list[Line] = []
    if crashes:
        count_text = _plural("bsod.crashes", len(crashes), language, days=snapshot.days)
        friendly.append(Line(count_text, Level.ERROR))
        for crash in crashes:
            crash_text = get_message(
                "bsod.crash_line",
                language,
                when=f"{crash.time:%Y-%m-%d %H:%M}",
                explanation=_explain(crash.code, language),
            )
            friendly.append(Line(crash_text, Level.LOG))
    if shutdowns:
        friendly.append(Line(_plural("bsod.shutdowns", len(shutdowns), language), Level.LOG))
    if hardware:
        friendly.append(Line(_plural("bsod.hardware", len(hardware), language), Level.LOG))
    if hardware or any(crash.code in MEMORY_RELATED_CODES for crash in crashes):
        friendly.append(Line(get_message("bsod.hint.memory", language), Level.LOG))

    if not (crashes or shutdowns or hardware):
        friendly.append(Line(get_message("bsod.none", language, days=snapshot.days), Level.OK))
        verdict = "ok"
    elif len(crashes) >= THRESHOLDS["crashes_attention"]:
        verdict = "attention"
    else:
        verdict = "warning"
    friendly.append(Line(get_message(f"bsod.verdict.{verdict}", language), VERDICT_LEVELS[verdict]))

    technical = [get_message("bsod.technical_title", language)]
    for event in sorted(snapshot.events, key=lambda item: item.time, reverse=True):
        technical.append(
            get_message(
                "bsod.technical_event",
                language,
                time=f"{event.time:%Y-%m-%d %H:%M:%S}",
                kind=event.kind.value,
                event_id=event.event_id,
                code=_code_label(event.bugcheck_code),
            )
        )
    if snapshot.dump_files:
        technical.extend(
            get_message("bsod.technical_dump", language, path=path)
            for path in snapshot.dump_files
        )
    else:
        technical.append(get_message("bsod.technical_no_dumps", language))

    return Report(friendly=tuple(friendly), technical=tuple(technical))
