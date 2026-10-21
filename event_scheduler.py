"""Problem 2 - Event scheduling on half-open intervals.

Every event is treated as the half-open interval [start, end).  That single
convention encodes the requirement that an event ending at 10 and another
starting at 10 do not conflict, and it makes the sweep logic easy to reason
about.
"""

from __future__ import annotations

import heapq
from typing import Iterable, List, Sequence, Tuple

Interval = Tuple[float, float]


def _validated(events: Iterable[Interval]) -> List[Interval]:
    """Return the intervals as a list, rejecting reversed or empty input."""
    cleaned: List[Interval] = []
    for start, end in events:
        if start > end:
            raise ValueError(f"event end {end!r} precedes start {start!r}")
        cleaned.append((start, end))
    return cleaned


def can_attend_all(events: Sequence[Interval]) -> bool:
    """True when no two events overlap.

    Sort by start time and walk forward while remembering the furthest end
    seen so far.  A new event is safe only if it starts at or after that
    point.  Keeping the *maximum* end (instead of the previous end) is what
    makes nested intervals such as (9, 12), (10, 11) work.

    Time  O(n log n)  - the sort dominates
    Space O(n)        - the sorted copy
    """
    ordered = sorted(_validated(events))
    furthest_end = float("-inf")

    for start, end in ordered:
        if start < furthest_end:            # strict: touching is allowed
            return False
        furthest_end = max(furthest_end, end)
    return True


def min_rooms_required(events: Sequence[Interval]) -> int:
    """Minimum number of identical rooms needed to host every event.

    Sweep events in start-time order.  A min-heap holds the end time of every
    room currently in use; before seating the next event, every room that has
    already been released (end <= start) is popped.  Whatever remains is the
    set of concurrent events, and the largest such set over the whole sweep is
    exactly the number of rooms required.

    Time  O(n log n)  - one sort, n pushes, at most n pops
    Space O(n)        - the heap
    """
    ordered = sorted(_validated(events))
    busy: List[float] = []                  # min-heap of end times
    peak = 0

    for start, end in ordered:
        while busy and busy[0] <= start:    # room is free again
            heapq.heappop(busy)
        heapq.heappush(busy, end)
        peak = max(peak, len(busy))

    return peak


def room_label(index: int) -> str:
    """0 -> 'Room A', 25 -> 'Room Z', 26 -> 'Room AA', 27 -> 'Room AB'."""
    if index < 0:
        raise ValueError("room index must be >= 0")
    letters = ""
    n = index + 1                            # bijective base-26
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"Room {letters}"


def assign_rooms(events: Sequence[Interval]) -> List[Tuple[float, float, str]]:
    """Greedily pin every event to a concrete room.

    Returns (start, end, room) tuples in chronological order. Reusing the
    lowest free room (or opening a new one) is optimal for interval
    partitioning, so the result uses exactly min_rooms_required(events) rooms.

    Time  O(n log n)
    Space O(n)
    """
    ordered = sorted(_validated(events))

    free: List[int] = []                            # min-heap of room ids
    busy: List[Tuple[float, int]] = []              # (end, room id)
    next_room_id = 0
    schedule: List[Tuple[float, float, str]] = []

    for start, end in ordered:
        while busy and busy[0][0] <= start:         # release finished rooms
            _, room_id = heapq.heappop(busy)
            heapq.heappush(free, room_id)

        if free:
            room_id = heapq.heappop(free)
        else:
            room_id = next_room_id
            next_room_id += 1

        heapq.heappush(busy, (end, room_id))
        schedule.append((start, end, room_label(room_id)))

    return schedule
