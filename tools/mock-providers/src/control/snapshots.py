"""Captured request/response snapshots for replay testing.

Use case: a flaky integration test produces an unexpected provider response. We
capture it once via `/control/snapshots`, then the next CI run replays the
exact bytes deterministically — no upstream calls, no flakiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class Snapshot:
    response: dict[str, object]
    status_code: int


class SnapshotStore:
    """In-memory snapshot table. Cleared on `/control/reset`."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[str, Snapshot] = {}

    def add(self, key: str, response: dict[str, object], status_code: int = 200) -> None:
        with self._lock:
            self._items[key] = Snapshot(response=response, status_code=status_code)

    def get(self, key: str) -> Snapshot | None:
        with self._lock:
            return self._items.get(key)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
