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
class BsodSnapshot:
    days: int
    events: tuple[SystemEvent, ...]
    dump_files: tuple[str, ...]

    def of_kind(self, kind: EventKind) -> tuple[SystemEvent, ...]:
        return tuple(event for event in self.events if event.kind is kind)
