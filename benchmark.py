"""Rough performance sanity check (not part of the graded solution).

Run with:  python benchmark.py
"""

from __future__ import annotations

import random
import time
import tracemalloc

from event_scheduler import assign_rooms, can_attend_all, min_rooms_required
from lru_cache import LRUCache


def row(label: str, value: str) -> None:
    print(f"  {label:<30}{value:>12}")


def bench_lru(operations: int = 400_000, capacity: int = 10_000) -> None:
    rng = random.Random(1)
    keys = [rng.randrange(capacity * 3) for _ in range(operations)]
    cache = LRUCache(capacity)

    start = time.perf_counter()
    hits = 0
    for i, key in enumerate(keys):
        if i % 2:
            hits += cache.get(key) != -1
        else:
            cache.put(key, i)
    elapsed = time.perf_counter() - start

    print(f"LRU cache, capacity {capacity:,}")
    row(
        f"{operations:,} mixed operations",
        f"{elapsed:.3f} s   {operations / elapsed / 1e6:.2f} M ops/s",
    )

    tracemalloc.start()
    full = LRUCache(capacity)
    for key in range(capacity):
        full.put(key, key)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    row(f"{capacity:,} live entries", f"{peak / capacity:.0f} bytes/entry")


def bench_lru_scaling(operations: int = 200_000) -> None:
    """The point of O(1): cost per operation should not grow with capacity."""
    rng = random.Random(3)
    keys = [rng.randrange(1_000_000) for _ in range(operations)]

    print(f"LRU cost per operation, {operations:,} ops each")
    for capacity in (100, 10_000, 200_000):
        cache = LRUCache(capacity)
        start = time.perf_counter()
        for i, key in enumerate(keys):
            if i % 2:
                cache.get(key)
            else:
                cache.put(key, i)
        elapsed = time.perf_counter() - start
        row(f"capacity {capacity:,}", f"{elapsed / operations * 1e9:.0f} ns/op")


def bench_scheduler(n: int = 100_000) -> None:
    rng = random.Random(2)
    events = []
    for _ in range(n):
        start = rng.randrange(0, 1_000_000)
        events.append((start, start + rng.randrange(1, 60)))

    print(f"Scheduler, {n:,} events")
    for name, fn, note in (
        ("can_attend_all", can_attend_all, ""),
        ("min_rooms_required", min_rooms_required, " rooms"),
        ("assign_rooms", assign_rooms, " assignments"),
    ):
        t0 = time.perf_counter()
        result = fn(events)
        elapsed = time.perf_counter() - t0
        if isinstance(result, list):
            shown = f"{len(result):,}{note}"
        else:
            shown = f"{result}{note}"
        row(name, f"{elapsed:.3f} s   {shown}")


if __name__ == "__main__":
    bench_lru()
    bench_lru_scaling()
    bench_scheduler()
