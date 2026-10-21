"""Concurrency tests: invariants must survive parallel access.

The switch interval is shortened so the interpreter preempts threads far more
often than it normally would, which makes interleavings much more likely.
"""

from __future__ import annotations

import random
import sys
import threading
from typing import List

import pytest

from lru_cache import LRUCache
from thread_safe import ShardedLRUCache, ThreadSafeLRUCache


def assert_consistent(cache: LRUCache) -> None:
    """The dict and the linked list must describe exactly the same entries."""
    keys: List[int] = []
    node = cache._head.next                       # white-box on purpose
    while node is not cache._tail:
        assert node.prev.next is node
        assert node.next.prev is node
        assert cache._map[node.key] is node
        keys.append(node.key)                     # type: ignore[arg-type]
        node = node.next
    assert len(keys) == len(cache)
    assert set(keys) == set(cache._map)
    assert len(keys) <= cache.capacity


def hammer(cache, seed: int, operations: int) -> None:
    rng = random.Random(seed)
    for i in range(operations):
        key = rng.randrange(512)
        if i % 2:
            cache.get(key)
        else:
            cache.put(key, i)


def test_single_lock_cache_survives_parallel_use() -> None:
    previous = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        cache = ThreadSafeLRUCache(64)
        threads = [
            threading.Thread(target=hammer, args=(cache, seed, 4000))
            for seed in range(8)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(cache) == 64
        assert len(cache.snapshot()) == 64
        assert len(set(cache.snapshot())) == 64
        assert_consistent(cache._cache)
    finally:
        sys.setswitchinterval(previous)


def test_sharded_cache_never_exceeds_capacity() -> None:
    previous = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        cache = ShardedLRUCache(100, shards=8)
        threads = [
            threading.Thread(target=hammer, args=(cache, seed + 100, 4000))
            for seed in range(8)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(cache) <= 100
        assert sum(len(s) for s in cache._shards) <= 100
    finally:
        sys.setswitchinterval(previous)


@pytest.mark.parametrize("capacity, shards", [(1, 8), (3, 2), (100, 4)])
def test_sharded_capacity_is_split_exactly(capacity: int, shards: int) -> None:
    cache = ShardedLRUCache(capacity, shards=shards)
    assert sum(s._cache.capacity for s in cache._shards) == capacity
    for shard in cache._shards:
        assert len(shard) == 0


def test_sharded_cache_preserves_values_when_nothing_is_evicted() -> None:
    cache = ShardedLRUCache(100, shards=4)
    for key in range(50):
        cache.put(key, key * 3)
    for key in range(50):
        assert cache.get(key) == key * 3
