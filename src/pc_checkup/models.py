"""Plain data containers shared by sources, interpreter and menu."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventKind(Enum):
    BUGCHECK = "bugcheck"
    UNEXPECTED_SHUTDOWN = "unexpected_shutdown"
    HARDWARE_ERROR = "hardware_error"


@dataclass(frozen=True)
class SystemEvent:
    time: datetime
    kind: EventKind
    event_id: int
    bugcheck_code: int | None = None
    details: str = ""


class Level(Enum):
    """How a line should look: plain text, a log band, or a status color."""

    INFO = "info"
    LOG = "log"
    OK = "ok"
    NOTICE = "notice"
    ERROR = "error"
    TECHNICAL = "technical"


@dataclass(frozen=True)
class Line:
    text: str
    level: Level = Level.INFO


@dataclass(frozen=True)
class Report:
    """What the user reads: a friendly part first, technical details below."""

    friendly: tuple[Line, ...]
    technical: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiskInfo:
    """One physical disk. A reliability counter the drive does not report is None."""

    device_id: str
    name: str
    media_type: str
    bus_type: str
    health: str
    size_bytes: int | None = None
    wear_percent: int | None = None
    temperature_c: int | None = None
    power_on_hours: int | None = None
    read_errors_uncorrected: int | None = None
    write_errors_uncorrected: int | None = None

    def unreadable_fields(self) -> tuple[str, ...]:
        readings = {
            "wear": self.wear_percent,
            "temperature": self.temperature_c,
            "power_on_hours": self.power_on_hours,
            "read_errors": self.read_errors_uncorrected,
            "write_errors": self.write_errors_uncorrected,
        }
        return tuple(name for name, value in readings.items() if value is None)


@dataclass(frozen=True)
class SsdSnapshot:
    disks: tuple[DiskInfo, ...]


@dataclass(frozen=True)
class BsodSnapshot:
    days: int
    events: tuple[SystemEvent, ...]
    dump_files: tuple[str, ...]

    def of_kind(self, kind: EventKind) -> tuple[SystemEvent, ...]:
        return tuple(event for event in self.events if event.kind is kind)
