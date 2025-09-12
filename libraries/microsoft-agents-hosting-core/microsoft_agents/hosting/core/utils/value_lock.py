"""Synchronization primitives for one-time locking based on a value. Not thread-safe."""

from typing import Any
from datetime import datetime


class ValueLock:
    """A synchronization primitive for one-locking based on a value. Not thread-safe.

    This class is used to ensure that only one coroutine can ever acquire a lock for a specific value.
    Caveat: the user of the class can clear the state, which will allow re-acquisition of previously used values.
    """

    def __init__(self, initial_set=None) -> None:
        self._used_values = initial_set if initial_set is not None else set()

    def release(self) -> set[Any]:
        """Clears the underlying set."""
        released = self._used_values
        self._used_values = set()
        return released

    def acquire(self, value: Any) -> bool:
        """Acquires the lock."""
        if value is None or value in self._used_values:
            return False

        self._used_values.add(value)
        return True

    def size(self) -> int:
        """Returns the number of used values."""
        return len(self._used_values)


class SmartValueLock:
    """A wrapper around ValueLock that automatically cleans up old entries."""

    def __init__(
        self, age_threshold: int, size_threshold: int, min_cond_release_interval: float
    ) -> None:
        """

        Args:
            age_threshold: Age in seconds after which a value is considered old and can be removed.
            size_threshold: Number of locked values after which a conditional release can be triggered.
            min_cond_release_interval: Minimum interval in seconds between conditional releases.
        """
        super().__init__()
        self._added_times = {}
        self._value_lock = ValueLock()
        self._last_release_time = 0
        self._age_threshold = age_threshold
        self._size_threshold = size_threshold
        self._min_cond_release_interval = min_cond_release_interval

    def release(self) -> set[Any]:
        """Releases all locked values."""
        released = self._value_lock.release()
        self._added_times = {}
        self._last_release_time = datetime.now().timestamp()
        return released

    def _conditional_release(self) -> None:

        ts = datetime.now().timestamp()

        if (
            ts - self._last_release_time < self._min_cond_release_interval
            or self._value_lock.size() < self._size_threshold
        ):
            return

        values = self._value_lock.release()

        new_values = {
            v for v in values if (ts - self._added_times[v]) < self._age_threshold
        }
        self._value_lock = ValueLock(new_values)
        self._added_times = {v: self._added_times[v] for v in new_values}
        self._last_release_time = ts

    def acquire(self, value: Any) -> bool:
        if self._value_lock.acquire(value):
            self._added_times[value] = datetime.now().timestamp()
            self._conditional_release()
            return True
        return False
