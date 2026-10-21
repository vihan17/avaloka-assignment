"""Tests for the O(1) LRU cache."""

from __future__ import annotations

import random
from collections import OrderedDict

import pytest

from lru_cache import LRUCache


class ReferenceLRU:
    """Independent implementation used for differential testing."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.data: "OrderedDict[int, int]" = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key: int, value: int) -> None:
        if key in self.data:
            self.data[key] = value
            self.data.move_to_end(key)
            return
        if len(self.data) == self.capacity:
            self.data.popitem(last=False)
        self.data[key] = value


def test_leetcode_example() -> None:
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)              # evicts key 2
    assert cache.get(2) == -1
    cache.put(4, 4)              # evicts key 1
    assert cache.get(1) == -1
    assert cache.get(3) == 3
    assert cache.get(4) == 4


def test_capacity_one_always_evicts() -> None:
    cache = LRUCache(1)
    cache.put(1, 10)
    cache.put(2, 20)
    assert cache.get(1) == -1
    assert cache.get(2) == 20


def test_update_existing_key_does_not_evict() -> None:
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(1, 100)            # update, not insert
    assert len(cache) == 2
    assert cache.get(2) == 2
    assert cache.get(1) == 100


def test_get_refreshes_recency() -> None:
    cache = LRUCache(3)
    for key in (1, 2, 3):
        cache.put(key, key)
    assert cache.get(1) == 1     # 1 becomes most recent, 2 is now LRU
    cache.put(4, 4)              # must evict 2
    assert cache.get(2) == -1
    assert list(cache.keys_mru_to_lru()) == [4, 1, 3]


def test_repeated_eviction_order_is_lru_not_fifo() -> None:
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(1)
    cache.put(3, 3)
    cache.get(2)
    assert cache.get(2) == -1
    assert cache.get(1) == 1
    assert cache.get(3) == 3


@pytest.mark.parametrize("capacity", [0, -1, -100])
def test_rejects_non_positive_capacity(capacity: int) -> None:
    with pytest.raises(ValueError):
        LRUCache(capacity)


def test_rejects_non_integer_capacity() -> None:
    with pytest.raises(TypeError):
        LRUCache(2.5)            # type: ignore[arg-type]


def test_random_operations_match_reference() -> None:
    rng = random.Random(20261021)

    for _ in range(300):
        capacity = rng.randint(1, 6)
        cache = LRUCache(capacity)
        reference = ReferenceLRU(capacity)

        for _ in range(200):
            if rng.random() < 0.45:
                key = rng.randint(0, 12)
                assert cache.get(key) == reference.get(key)
            else:
                key = rng.randint(0, 12)
                value = rng.randint(0, 10_000)
                cache.put(key, value)
                reference.put(key, value)

            assert len(cache) == len(reference.data)
            # OrderedDict keeps LRU -> MRU, so reverse it for comparison.
            assert list(cache.keys_mru_to_lru()) == list(reversed(reference.data))
