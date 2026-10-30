"""Turns raw snapshots into friendly text plus technical details."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from pc_checkup.messages import get_message
from pc_checkup.models import (
    BsodSnapshot,
    DiskInfo,
    EventKind,
    Level,
    Line,
    RamOutcome,
    RamSnapshot,
    Report,
    SsdSnapshot,
)

# All thresholds in one place.
THRESHOLDS = {
    "same_crash_window_seconds": 120,
    "crashes_attention": 3,
    # SSD: percent of life remaining (Windows reports wear as percent used).
    "ssd_life_aging_below": 80,
    "ssd_life_critical_below": 10,
    "ssd_temperature_hot_c": 70,
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

VERDICT_LEVELS = {
    "ok": Level.OK,
    "limited": Level.LOG,
    "unknown": Level.LOG,
    "warning": Level.LOG,
    "attention": Level.LOG,
}

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


@dataclass(frozen=True)
class DiskReadings:
    """What can be trusted from a disk. None means missing or not believable."""

    wear: int | None
    temperature: int | None
    hours: int | None
    read_errors: int | None
    write_errors: int | None

    def unreadable(self) -> tuple[str, ...]:
        names = {
            "wear": self.wear,
            "temperature": self.temperature,
            "power_on_hours": self.hours,
            "read_errors": self.read_errors,
            "write_errors": self.write_errors,
        }
        return tuple(name for name, value in names.items() if value is None)


def trusted_readings(disk: DiskInfo) -> DiskReadings:
    """Drop placeholder values: some RAID controllers report 0 degrees and 0 wear."""
    placeholder = disk.temperature_c is not None and disk.temperature_c <= 0
    return DiskReadings(
        wear=None if placeholder else disk.wear_percent,
        temperature=None if placeholder else disk.temperature_c,
        hours=disk.power_on_hours,
        read_errors=disk.read_errors_uncorrected,
        write_errors=disk.write_errors_uncorrected,
    )


def _ssd_health_key(health: str) -> str:
    return health if health in ("Healthy", "Warning", "Unhealthy") else "unknown"


def _interpret_disk(disk: DiskInfo, language: str) -> list[Line]:
    readings = trusted_readings(disk)
    health_key = _ssd_health_key(disk.health)
    size_gb = round(disk.size_bytes / 1_000_000_000) if disk.size_bytes else "?"
    lines = [
        Line(
            get_message(
                "ssd.disk",
                language,
                id=disk.device_id,
                name=disk.name,
                media=disk.media_type,
                size=size_gb,
                bus=disk.bus_type,
            ),
            Level.LOG,
        ),
        Line(
            get_message(f"ssd.health.{health_key}", language),
            Level.ERROR if health_key == "Unhealthy" else Level.LOG,
        ),
    ]

    verdict = "ok" if health_key == "Healthy" else "warning"
    if health_key == "Unhealthy":
        verdict = "attention"

    if readings.wear is not None:
        life = 100 - readings.wear
        if life < THRESHOLDS["ssd_life_critical_below"]:
            wear_key, wear_level, verdict = "ssd.wear.critical", Level.ERROR, "attention"
        elif life < THRESHOLDS["ssd_life_aging_below"]:
            wear_key, wear_level = "ssd.wear.aging", Level.LOG
            verdict = verdict if verdict == "attention" else "warning"
        else:
            wear_key, wear_level = "ssd.wear", Level.LOG
        lines.append(Line(get_message(wear_key, language, life=life), wear_level))

    if readings.temperature is not None:
        hot = readings.temperature >= THRESHOLDS["ssd_temperature_hot_c"]
        key = "ssd.temperature.hot" if hot else "ssd.temperature"
        lines.append(Line(get_message(key, language, value=readings.temperature), Level.LOG))
        if hot and verdict == "ok":
            verdict = "warning"

    if readings.hours is not None:
        lines.append(
            Line(get_message("ssd.hours", language, hours=readings.hours, days=readings.hours // 24), Level.LOG)
        )

    error_counts = [c for c in (readings.read_errors, readings.write_errors) if c is not None]
    if error_counts:
        total = sum(error_counts)
        if total > 0:
            lines.append(Line(get_message("ssd.errors.found", language, count=total), Level.ERROR))
            verdict = "attention"
        else:
            lines.append(Line(get_message("ssd.errors.none", language), Level.LOG))

    missing = readings.unreadable()
    if missing:
        fields = ", ".join(get_message(f"ssd.field.{name}", language) for name in missing)
        lines.append(Line(get_message("ssd.unreadable", language, fields=fields), Level.LOG))
        if verdict == "ok" and readings.wear is None:
            verdict = "limited"

    lines.append(Line(get_message(f"ssd.verdict.{verdict}", language), VERDICT_LEVELS[verdict]))
    return lines


def interpret_ssd(snapshot: SsdSnapshot, language: str) -> Report:
    if not snapshot.disks:
        return Report(friendly=(Line(get_message("ssd.none", language), Level.LOG),))
    friendly: list[Line] = []
    for index, disk in enumerate(snapshot.disks):
        if index:
            friendly.append(Line(""))
        friendly.extend(_interpret_disk(disk, language))
    return Report(friendly=tuple(friendly))


def interpret_ram(snapshot: RamSnapshot, language: str) -> Report:
    latest = snapshot.latest
    if latest is None:
        return Report(
            friendly=(
                Line(get_message("ram.none", language), Level.LOG),
                Line(get_message("ram.verdict.unknown", language), VERDICT_LEVELS["unknown"]),
            )
        )
    when = f"{latest.time:%Y-%m-%d %H:%M}"
    if latest.outcome is RamOutcome.ERRORS_FOUND:
        return Report(
            friendly=(
                Line(get_message("ram.errors", language, when=when), Level.ERROR),
                Line(get_message("ram.verdict.attention", language), VERDICT_LEVELS["attention"]),
            )
        )
    return Report(
        friendly=(
            Line(get_message("ram.no_errors", language, when=when), Level.LOG),
            Line(get_message("ram.verdict.ok", language), VERDICT_LEVELS["ok"]),
        )
    )
