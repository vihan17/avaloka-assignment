# Avaloka take-home — O(1) LRU cache and event scheduler

Solutions to the two-problem take-home assignment, written in Python 3.10 with
the standard library only.

The primary deliverable is `Vihan_Chorada_Avaloka_Assignment.pdf`. It contains
the reasoning in plain English before each implementation, the full source,
and the discussion answers. This README is the short version for browsing the
code.

## Contents

| Path | What it is |
| --- | --- |
| `lru_cache.py` | Problem 1: `LRUCache` with O(1) `get` and `put` |
| `event_scheduler.py` | Problem 2: overlap check, minimum room count, room assignment |
| `thread_safe.py` | Locked and sharded wrappers used in discussion 3.4 |
| `demo.py` | Small walkthrough whose output is embedded in the report |
| `benchmark.py` | Rough timing and memory check (not part of the solution) |
| `tests/` | 47 pytest tests, including randomised differential checks |
| `build_report.py`, `build/template.html` | Rebuild the PDF from these sources |
| `Vihan_Chorada_Avaloka_Assignment.pdf` | Submission document |

## Running it

```bash
python demo.py                 # readable walkthrough
python -m pytest tests -q      # 47 tests
python benchmark.py            # timing and memory sanity check
```

The solution modules have no third-party dependencies. `pytest` is needed only
for the tests; `Pygments`, `pypdf`, and a local Chrome/Edge are needed only to
rebuild the PDF.

## Problem 1 — LRU cache

```python
from lru_cache import LRUCache

cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
cache.get(1)      # 1, and 1 becomes most recently used
cache.put(3, 3)   # evicts 2
cache.get(2)      # -1
```

**Design.** A dictionary maps each key to its node, and a doubly linked list
keeps those nodes in recency order:

```
head <-> most recent <-> ... <-> least recent <-> tail
```

`get` finds the node in the dictionary and moves it to the front. `put`
either updates an existing node or inserts a new one, evicting `tail.prev`
when the cache is full. Two sentinel nodes remove the null checks from the
pointer surgery. Every operation touches a constant number of pointers.

| Operation | Time | Space |
| --- | --- | --- |
| `get(key)` | O(1) expected | O(1) |
| `put(key, value)` | O(1) expected | O(1) |
| Whole cache | — | O(capacity) |

"Expected" is the honest qualifier: the list work is worst-case O(1), but the
dictionary probe is O(1) only on average. A missing key returns `-1`;
capacity must be at least 1.

## Problem 2 — event scheduler

Events are half-open intervals `[start, end)`. That convention is what makes
an event ending at 10:00 and another starting at 10:00 compatible.

```python
from event_scheduler import can_attend_all, min_rooms_required, assign_rooms

can_attend_all([(9, 10), (10, 11), (11, 12)])   # True
min_rooms_required([(9, 10), (10, 11), (11, 12)])  # 1
assign_rooms([(9, 10), (10, 11)])               # [(9, 10, 'Room A'), (10, 11, 'Room A')]
```

**`can_attend_all`.** Sort by start time, then sweep while remembering the
furthest end seen so far. The next event is safe only if it starts at or after
that point. Keeping the maximum end, rather than just the previous end, is
what handles nested intervals such as `(9, 12), (10, 11)`.

**`min_rooms_required`.** Sweep in start order with a min-heap of end times.
Before seating each event, pop every room that has already been released
(`end <= start`). The heap then holds exactly the events in progress, and the
largest heap size over the sweep is the minimum number of rooms. This equals
the peak concurrency, which is a lower bound because all those events overlap
at that instant.

**`assign_rooms`.** The same sweep, but the heap carries room ids. A second
min-heap tracks free ids, and finished rooms are released back into it. Each
event takes the lowest-numbered free room, or opens a new one when none is
free. The result is deterministic, uses no more than `min_rooms_required`
rooms, and returns `(start, end, room_label)` in chronological order. Labels
are bijective base-26: `Room A … Room Z, Room AA, Room AB …`.

| Function | Time | Space |
| --- | --- | --- |
| `can_attend_all` | O(n log n) | O(n) |
| `min_rooms_required` | O(n log n) | O(n) |
| `assign_rooms` | O(n log n) | O(n) |
| `room_label` | O(log n) | O(1) |

Reversed intervals raise `ValueError`; zero-length events (`start == end`) are
allowed. The sort dominates in every case.

## Thread safety

`LRUCache` is deliberately lock-free and is not safe to share between threads.
`get` is not a read: a hit reorders the linked list, so every lookup is a
mutation and a readers-writer lock would not help.

- `ThreadSafeLRUCache` puts one mutex around the whole cache. Correct and
  simple, but it serialises all traffic.
- `ShardedLRUCache` splits the capacity across independent shards, each with
  its own lock. Eviction becomes per-shard, so the global LRU order is
  approximate — a hot key in a cold shard can be evicted before a cold key in
  a hot shard.

The tests run eight threads over random operations and then check that the
dictionary and the linked list still contain the same keys in the same order,
that the locked cache is exactly at capacity, and that every `prev`/`next` link
is consistent.

## Measured on the build machine

CPython 3.10, one run, for shape rather than absolute speed:

| Measurement | Result |
| --- | --- |
| 400,000 mixed LRU operations, capacity 10,000 | 0.390 s (1.03 M ops/s) |
| Memory per live entry, 10,000 entries | 121 bytes |
| Cost per operation at capacity 100 / 10,000 / 200,000 | 790 / 922 / 890 ns |
| `can_attend_all`, 100,000 events | 0.087 s |
| `min_rooms_required`, 100,000 events | 0.167 s, 15 rooms |
| `assign_rooms`, 100,000 events | 0.257 s |

The flat per-operation cost across a 2,000× capacity range is the practical
point of the O(1) design.

## Tests

```text
$ python -m pytest tests -q
...............................................                          [100%]
47 passed
```

Coverage includes the LeetCode-style example, capacity-one eviction, update
without eviction, recency refresh, FIFO-vs-LRU ordering, input validation, 300
randomised cache histories compared against an independent `OrderedDict`
reference, brute-force checks of both scheduler functions, room-assignment
invariants, and the multi-threaded stress test.

## Rebuilding the PDF

`build_report.py` runs the tests, demo, and benchmark, injects their real
output and the source excerpts into `build/template.html`, renders it with
headless Chrome, and stamps page footers with `pypdf`.

```bash
python build_report.py
```

Requires `pytest`, `Pygments`, and `pypdf`, plus Chrome or Edge installed at a
standard path. The script renders twice so the table-of-contents page numbers
match the final pagination.

## Assumptions

- All rooms are identical; there are no buffers, capacities, or equipment
  constraints.
- Intervals are half-open and may have zero length; end before start is
  invalid input.
- The scheduler and the cache are in-process data structures. Persistence,
  distributed coordination, and eviction across processes are out of scope and
  discussed only as extensions.
