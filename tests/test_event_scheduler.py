"""Tests for overlap detection, room counting, and room assignment."""

from __future__ import annotations

import random
from typing import List, Sequence, Tuple

import pytest

from event_scheduler import (
    Interval,
    assign_rooms,
    can_attend_all,
    min_rooms_required,
    room_label,
)


def brute_force_overlap(events: Sequence[Interval]) -> bool:
    """O(n^2) definition: two half-open intervals overlap iff
    a.start < b.end and b.start < a.end."""
    for i, (a_start, a_end) in enumerate(events):
        for b_start, b_end in events[i + 1:]:
            if a_start < b_end and b_start < a_end:
                return True
    return False


def brute_force_rooms(events: Sequence[Interval]) -> int:
    """Max concurrency sampled at every start time."""
    peak = 0
    for point, _ in events:
        covering = sum(1 for start, end in events if start <= point < end)
        peak = max(peak, covering)
    return peak


# ----------------------------------------------------------------------
# can_attend_all
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "events, expected",
    [
        ([], True),
        ([(9, 10)], True),
        ([(9, 10), (10, 11), (11, 12)], True),      # back-to-back is fine
        ([(7, 10), (2, 4)], True),                  # unsorted input
        ([(0, 30), (5, 10), (15, 20)], False),
        ([(9, 12), (10, 11)], False),               # fully nested
        ([(9, 10), (9, 10)], False),                # duplicates
        ([(1, 5), (5, 9), (9, 9)], True),
    ],
)
def test_can_attend_all(events: List[Interval], expected: bool) -> None:
    assert can_attend_all(events) is expected


def test_can_attend_all_rejects_reversed_interval() -> None:
    with pytest.raises(ValueError):
        can_attend_all([(10, 9)])


def test_can_attend_all_randomized_against_brute_force() -> None:
    rng = random.Random(7)
    for _ in range(400):
        n = rng.randint(0, 7)
        events = []
        for _ in range(n):
            start = rng.randint(0, 20)
            events.append((start, start + rng.randint(1, 6)))
        assert can_attend_all(events) == (not brute_force_overlap(events))


# ----------------------------------------------------------------------
# min_rooms_required
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "events, expected",
    [
        ([], 0),
        ([(9, 10)], 1),
        ([(9, 10), (10, 11), (11, 12)], 1),
        ([(7, 10), (2, 4)], 1),
        ([(0, 30), (5, 10), (15, 20)], 2),
        ([(1, 5), (1, 5), (1, 5)], 3),
        ([(1, 10), (2, 3), (4, 5)], 2),             # nesting still costs a room
        ([(1, 4), (2, 5), (3, 6), (4, 7)], 3),
    ],
)
def test_min_rooms_required(events: List[Interval], expected: int) -> None:
    assert min_rooms_required(events) == expected


def test_min_rooms_randomized_against_brute_force() -> None:
    rng = random.Random(11)
    for _ in range(400):
        n = rng.randint(0, 8)
        events = []
        for _ in range(n):
            start = rng.randint(0, 15)
            events.append((start, start + rng.randint(1, 5)))
        assert min_rooms_required(events) == brute_force_rooms(events)


def test_can_attend_all_is_min_rooms_at_most_one() -> None:
    rng = random.Random(13)
    for _ in range(200):
        n = rng.randint(0, 6)
        events = [
            (s, s + rng.randint(1, 5))
            for s in (rng.randint(0, 12) for _ in range(n))
        ]
        assert can_attend_all(events) == (min_rooms_required(events) <= 1)


# ----------------------------------------------------------------------
# assign_rooms
# ----------------------------------------------------------------------
def test_assign_rooms_matches_minimum_and_has_no_conflicts() -> None:
    rng = random.Random(17)
    for _ in range(200):
        n = rng.randint(0, 9)
        events = []
        for _ in range(n):
            start = rng.randint(0, 15)
            events.append((start, start + rng.randint(1, 5)))

        schedule = assign_rooms(events)
        assert len(schedule) == n
        assert schedule == sorted(schedule, key=lambda row: (row[0], row[1]))
        assert len({room for _, _, room in schedule}) == min_rooms_required(events)

        for room in {row[2] for row in schedule}:
            booked = [(s, e) for s, e, r in schedule if r == room]
            for i, (a_start, a_end) in enumerate(booked):
                for b_start, b_end in booked[i + 1:]:
                    assert not (a_start < b_end and b_start < a_end)


def test_assign_rooms_reuses_rooms_in_preference_order() -> None:
    schedule = assign_rooms([(9, 10), (9, 11), (10, 12)])
    assert schedule == [(9, 10, "Room A"), (9, 11, "Room B"), (10, 12, "Room A")]


def test_assign_rooms_empty() -> None:
    assert assign_rooms([]) == []


@pytest.mark.parametrize(
    "index, label",
    [(0, "Room A"), (1, "Room B"), (25, "Room Z"), (26, "Room AA"),
     (27, "Room AB"), (51, "Room AZ"), (52, "Room BA"), (701, "Room ZZ")],
)
def test_room_label(index: int, label: str) -> None:
    assert room_label(index) == label
