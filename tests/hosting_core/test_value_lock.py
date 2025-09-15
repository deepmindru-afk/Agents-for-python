from time import sleep
from typing import Any, Iterable, Optional
from abc import ABC, abstractmethod

import pytest

from microsoft_agents.hosting.core import ValueLock, SmartValueLock


class BaseValueLockTests(ABC):
    @abstractmethod
    def build_lock(self, values: Optional[Iterable[Any]] = None) -> Any:
        raise NotImplementedError()

    def test_init_empty(self):
        lock = self.build_lock()
        assert lock.size() == 0
        assert lock.release() == {}

    def test_init_non_empty(self):
        lock = self.build_lock(range(10))
        assert lock.size() == 4
        assert lock.release() == {range(10)}

    def test_release_empty(self):
        lock = self.build_lock()
        assert lock.release() == {}
        assert lock.size() == 0

    def test_release_non_empty(self):
        lock = self.build_lock({"a", "b", "c", "C", "c"})
        assert lock.release() == {"a", "b", "c", "C"}
        assert lock.size() == 0

    def test_acquire_taken(self):
        lock = self.build_lock({"a", "b", "c"})
        assert lock.acquire("a") is False
        assert lock.acquire("b") is False
        assert lock.acquire("c") is False
        assert lock.size() == 3

    def test_acquire(self):
        lock = self.build_lock()
        assert lock.acquire("a") is True
        assert lock.size() == 1

    def test_acquire_multiple(self):
        lock = self.build_lock()
        assert lock.acquire("b") is True
        assert lock.acquire("a") is True
        assert lock.acquire("a") is False
        assert lock.acquire("b") is False
        assert lock.acquire("c") is True
        assert lock.size() == 3

    def test_acquire_released_value(self):
        lock = self.build_lock()
        assert lock.acquire("a") is True
        lock.release()
        assert lock.acquire("a") is True
        assert lock.size() == 1

    @pytest.mark.parametrize("value", [1, 2, 3, "abc", "wow", object(), True, False])
    def test_init_with_flow(self, value):
        lock = self.build_lock()
        assert lock.size() == 0
        assert lock.release == {}
        assert lock.acquire(value) is True

    @pytest.mark.parametrize("value", [1, 2, 3, "abc", "wow", object(), True, False])
    def test_init_with_value_with_flow(self, value):
        lock = self.build_lock({value})
        assert lock.size() == 1
        assert lock.acquire(value) is False
        assert lock.release() == {"initial"}
        assert lock.size() == 0
        assert lock.acquire("initial") is True
        assert lock.acquire("new_value") is True
        assert lock.size() == 2


class TestValueLock(BaseValueLockTests):
    def build_lock(self, values: Optional[Iterable[Any]] = None):
        return ValueLock(set(values) if values else set())


# SmartValueLock should pass all of the tests
# under the default conditions for build_lock
# defined in TestSmartValueLock
class TestSmartValueLockBase(BaseValueLockTests):
    def build_lock(self, values: Optional[Iterable[Any]] = None):
        return SmartValueLock(
            min_value_duration=0.2,
            size_threshold=2,
            min_cond_release_interval=0.1,
            initial_values=set(values) if values else set(),
        )


class TestSmartValueLockOnly:
    def build_lock(
        self,
        values: Optional[Iterable[Any]] = None,
        min_value_duration: float = 0.2,
        size_threshold: int = 5,
        min_cond_release_interval: float = 0.1,
    ) -> SmartValueLock:
        if not values:
            values = set()
        lock = SmartValueLock(
            min_value_duration, size_threshold, min_cond_release_interval
        )
        for value in values:
            lock.acquire(value)
        return lock

    def test_init_empty(self):
        lock = SmartValueLock(
            min_value_duration=0.2, size_threshold=5, min_cond_release_interval=0.1
        )
        assert lock.size() == 0
        assert lock.release() == {}

    def test_conditional_release_nop(self):
        lock = self.build_lock(
            min_value_duration=0.1, size_threshold=5, min_cond_release_interval=0.1
        )
        lock.acquire(1)
        assert lock.size() == 1
        sleep(0.15)
        assert lock.size() == 1
        assert lock.release() == {1}

    def test_conditional_release_nop_min_interval_from_init(self):
        lock = self.build_lock(
            min_value_duration=0.1, size_threshold=1, min_cond_release_interval=0.1
        )
        lock.acquire(1)
        sleep(0.05)
        lock.acquire(2)
        assert lock.size() == 2
        assert lock.release() == {1, 2}

    @pytest.mark.parametrize("min_value_duration", [0, 0.01, 0.02])
    def test_conditional_release_nop_min_interval_from_init_no_min(
        self, min_value_duration
    ):
        lock = self.build_lock(min_value_duration=min_value_duration, size_threshold=2)
        lock.acquire(1)
        sleep(min_value_duration)
        lock.acquire(2)
        assert lock.size() == 1
        assert lock.release() == {2}

    @pytest.mark.parametrize("first, second", [(1, 2), (2, 2), (3, 4), ("ab", "ab")])
    def test_conditional_release_nop_min_interval_second(self, first, second):
        lock = self.build_lock(
            min_value_duration=0.1, size_threshold=1, min_cond_release_interval=0.1
        )
        lock.acquire(first)
        assert lock.size() == 1
        sleep(0.15)
        assert lock.size() == 0
        assert lock.release() == {}

        lock.acquire(second)

        sleep(0.05)

        lock.acquire("new_value")
        assert lock.size() == 2
        assert lock.release() == {second, "new_value"}

    def test_conditional_release_size_thresh(self):
        lock = self.build_lock(
            min_value_duration=0.1, size_threshold=2, min_cond_release_interval=0.1
        )
        assert lock.acquire("a")
        assert lock.size() == 1
        sleep(0.12)
        assert lock.acquire("b")
        assert lock.size() == 1
        assert lock.release() == {"b"}

    def test_conditional_release_size_thresh_nop(self):
        lock = self.build_lock(
            min_value_duration=0.1, size_threshold=10, min_cond_release_interval=0.1
        )
        assert lock.acquire("a")
        assert lock.size() == 1
        sleep(0.12)
        assert lock.acquire("b")
        assert lock.acquire("c")
        assert lock.size() == 3
        assert lock.release() == {"a", "b", "c"}

    def test_conditional_release_min_value_duration(self):

        lock = self.build_lock(
            min_value_duration=0.1, size_threshold=5, min_cond_release_interval=0.1
        )
        for i in range(10):
            assert lock.acquire(i)
            assert lock.size() == i

        sleep(0.05)

        for j in range(10):
            assert lock.acquire(j + 10)
            assert lock.size() == j + 10

        sleep(0.05)

        assert lock.acquire(20)
        assert lock.size() == 11
        assert lock.release() == {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}

    def test_flow_with_conditional_release_with_initial_values(self):
        initial_values = {1, 2, 3, 4, 5}
        lock = self.build_lock(
            values=initial_values,
            min_value_duration=0.1,
            size_threshold=5,
            min_cond_release_interval=0.1,
        )
        assert lock.size() == 5
        sleep(0.05)
        assert lock.acquire(6)
        assert lock.size() == 6
        sleep(0.06)
        assert lock.size() == 1
        sleep(0.1)
        assert lock.acquire(1)
        assert lock.release() == {1}
