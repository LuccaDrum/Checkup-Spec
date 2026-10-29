"""Base class for read-only data sources."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

SnapshotT = TypeVar("SnapshotT")


class Source(ABC, Generic[SnapshotT]):
    """Reads information from the PC and returns a snapshot. Never changes anything."""

    @abstractmethod
    def fetch(self) -> SnapshotT: ...
