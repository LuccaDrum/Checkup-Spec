from datetime import datetime

import pytest

from pc_checkup.models import BsodSnapshot, EventKind, SystemEvent
from pc_checkup.sources.base import Source


def make_event(kind: EventKind, event_id: int) -> SystemEvent:
    return SystemEvent(time=datetime(2026, 10, 29, 7, 43), kind=kind, event_id=event_id)


def test_of_kind_filters_events() -> None:
    crash = make_event(EventKind.BUGCHECK, 1001)
    power = make_event(EventKind.UNEXPECTED_SHUTDOWN, 41)
    snapshot = BsodSnapshot(days=15, events=(crash, power, crash), dump_files=())
    assert snapshot.of_kind(EventKind.BUGCHECK) == (crash, crash)
    assert snapshot.of_kind(EventKind.HARDWARE_ERROR) == ()


def test_events_are_immutable() -> None:
    event = make_event(EventKind.BUGCHECK, 1001)
    with pytest.raises(AttributeError):
        event.event_id = 2  # type: ignore[misc]


def test_source_cannot_be_instantiated_without_fetch() -> None:
    with pytest.raises(TypeError):
        Source()  # type: ignore[abstract]


def test_source_subclass_returns_its_snapshot() -> None:
    class FakeSource(Source[int]):
        def fetch(self) -> int:
            return 7

    assert FakeSource().fetch() == 7
