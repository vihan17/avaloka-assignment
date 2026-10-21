"""Small end-to-end demonstration whose output is pasted into the report.

Run with:  python demo.py
"""

from __future__ import annotations

from event_scheduler import assign_rooms, can_attend_all, min_rooms_required
from lru_cache import LRUCache


def show_cache() -> None:
    cache = LRUCache(2)
    print("LRU cache, capacity = 2")
    print(f"  {'operation':<15}{'result':>7}   {'MRU -> LRU':<14}note")
    print("  " + "-" * 58)

    steps = [
        ("put", 1, 1),
        ("put", 2, 2),
        ("get", 1, None),
        ("put", 3, 3),
        ("get", 2, None),
        ("put", 4, 4),
        ("get", 1, None),
        ("get", 3, None),
        ("get", 4, None),
    ]

    for operation, key, value in steps:
        before = set(cache.keys_mru_to_lru())
        if operation == "put":
            cache.put(key, value)
            label = f"put({key}, {value})"
            result = "-"
        else:
            result = str(cache.get(key))
            label = f"get({key})"

        after = list(cache.keys_mru_to_lru())
        evicted = before - set(after)
        note = f"evicted {evicted.pop()}" if evicted else ""
        print(f"  {label:<15}{result:>7}   {str(after):<14}{note}")


def show_overlaps() -> None:
    cases = [
        [(9, 10), (10, 11), (11, 12)],
        [(9, 11), (10, 12)],
        [(9, 12), (10, 11)],
        [(7, 10), (2, 4)],
    ]
    print("\ncan_attend_all")
    for events in cases:
        print(f"  {str(events):<34}{can_attend_all(events)}")


def show_rooms() -> None:
    cases = [
        [(9, 10), (10, 11), (11, 12)],
        [(0, 30), (5, 10), (15, 20)],
        [(1, 5), (1, 5), (1, 5)],
        [(1, 10), (2, 3), (4, 5)],
    ]
    print("\nmin_rooms_required")
    for events in cases:
        print(f"  {str(events):<34}{min_rooms_required(events)}")


def clock(hour: float) -> str:
    return f"{int(hour):02d}:{round((hour % 1) * 60):02d}"


def show_schedule() -> None:
    meetings = [
        ("Kickoff", (9.0, 10.0)),
        ("Design review", (9.0, 11.0)),
        ("1:1 with Priya", (10.0, 10.5)),
        ("Customer call", (10.5, 11.5)),
        ("Retro", (11.0, 12.0)),
    ]
    print("\nassign_rooms")
    for start, end, room in assign_rooms([slot for _, slot in meetings]):
        name = next(n for n, slot in meetings if slot == (start, end))
        print(f"  {room:<8} {clock(start)}-{clock(end)}   {name}")


if __name__ == "__main__":
    show_cache()
    show_overlaps()
    show_rooms()
    show_schedule()
