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


@dataclass(frozen=True)
class BsodSnapshot:
    days: int
    events: tuple[SystemEvent, ...]
    dump_files: tuple[str, ...]

    def of_kind(self, kind: EventKind) -> tuple[SystemEvent, ...]:
        return tuple(event for event in self.events if event.kind is kind)
