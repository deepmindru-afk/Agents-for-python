"""Synchronization primitives for one-time locking based on a value. Not thread-safe."""

from typing import Any, Optional
from datetime import datetime


class ValueLock:
    """A synchronization primitive for one-locking based on a value. Not thread-safe.

    This class is used to ensure that only one coroutine can ever acquire a lock for a specific value.
    Caveat: the user of the class can clear the state, which will allow re-acquisition of previously used values.
    """

    def __init__(self, initial_values: Optional[set[Any]] = None) -> None:
        self._used_values = initial_values if initial_values is not None else set()

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


# containment used rather than inheritance because a ConditionalReleaseValueLock's behavior
# is not a superset of ValueLock's behavior, and is fundamentally different.
class SmartValueLock:
    """A wrapper around ValueLock that automatically cleans up old entries."""

    def __init__(
        self,
        min_lock_duration: float,
        size_threshold: int,
        min_cond_release_interval: float = 0.0,
        initial_values: Optional[set[Any]] = None,
    ) -> None:
        """

        Args:
            min_lock_duration: Minimum duration in seconds that a value must be held before it can be released.
            size_threshold: Number of locked values after which a conditional release can be triggered.
            min_cond_release_interval: Minimum interval in seconds between conditional releases.
        """
        self._added_times = {}
        self._last_release_time = datetime.now().timestamp()
        self._min_lock_duration = min_lock_duration
        self._size_threshold = size_threshold
        self._min_cond_release_interval = min_cond_release_interval

        if initial_values:
            for v in initial_values:
                self._added_times[v] = self._last_release_time
            self._value_lock = ValueLock(initial_values)
        else:
            self._value_lock = ValueLock()

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
            v for v in values if (ts - self._added_times[v]) < self._min_lock_duration
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

    def size(self) -> int:
        return self._value_lock.size()
