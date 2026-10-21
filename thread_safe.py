"""Thread-safe wrappers for the LRU cache (discussion question 4).

`LRUCache` is deliberately lock-free and therefore not safe to share between
threads: `get()` mutates the recency list, so even a "read" is a write.
"""

from __future__ import annotations

import threading
from typing import List

from lru_cache import LRUCache


class ThreadSafeLRUCache:
    """One mutex around the whole cache - correct, simple, serialising.

    A readers-writer lock would not help: every hit reorders the linked list,
    so `get` needs exclusive access just as much as `put` does.
    """

    def __init__(self, capacity: int) -> None:
        self._cache = LRUCache(capacity)
        self._lock = threading.Lock()

    def get(self, key: int) -> int:
        with self._lock:
            return self._cache.get(key)

    def put(self, key: int, value: int) -> None:
        with self._lock:
            self._cache.put(key, value)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def snapshot(self) -> List[int]:
        """Keys from most to least recently used, copied under the lock."""
        with self._lock:
            return list(self._cache.keys_mru_to_lru())


class ShardedLRUCache:
    """`shards` independent caches, each with its own lock.

    Capacity is divided as evenly as possible, so the total never exceeds
    `capacity`.  The price is that eviction is decided per shard, which makes
    the global ordering approximate: a hot key that hashes to a cold shard can
    be evicted before a cold key in a hot shard.
    """

    def __init__(self, capacity: int, shards: int = 8) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if shards < 1:
            raise ValueError("shards must be >= 1")

        shard_count = min(shards, capacity)
        base, extra = divmod(capacity, shard_count)
        self._shards = [
            ThreadSafeLRUCache(base + (1 if i < extra else 0))
            for i in range(shard_count)
        ]

    def _shard_for(self, key: int) -> ThreadSafeLRUCache:
        return self._shards[hash(key) % len(self._shards)]

    def get(self, key: int) -> int:
        return self._shard_for(key).get(key)

    def put(self, key: int, value: int) -> None:
        self._shard_for(key).put(key, value)

    def __len__(self) -> int:
        return sum(len(shard) for shard in self._shards)
