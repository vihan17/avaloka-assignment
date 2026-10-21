"""Problem 1 - Least Recently Used (LRU) cache with O(1) get and put.

Design: a dict maps every key to its node, and a doubly linked list keeps the
nodes in recency order (front = most recently used, back = least recently
used).  Each operation touches only a constant number of pointers.
"""

from __future__ import annotations

from typing import Dict, Iterator, Optional


class _Node:
    """One cache entry.  `__slots__` keeps the per-entry memory cost low."""

    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: int = 0, value: int = 0) -> None:
        self.key = key
        self.value = value
        self.prev: Optional["_Node"] = None
        self.next: Optional["_Node"] = None


class LRUCache:
    """Fixed-capacity cache that evicts the least recently used entry.

    List layout (sentinels are never real entries):

        head <-> [most recent] <-> ... <-> [least recent] <-> tail
    """

    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be >= 1")

        self._capacity = capacity
        self._map: Dict[int, _Node] = {}

        # Two sentinels remove every null-check from the pointer surgery.
        self._head = _Node()
        self._tail = _Node()
        self._head.next = self._tail
        self._tail.prev = self._head

    # ------------------------------------------------------------------
    # Internal list primitives - each one is O(1)
    # ------------------------------------------------------------------
    def _detach(self, node: _Node) -> None:
        """Cut `node` out of the list, leaving its neighbours joined."""
        previous, following = node.prev, node.next
        assert previous is not None and following is not None, "sentinel detach"
        previous.next = following
        following.prev = previous
        node.prev = None
        node.next = None

    def _push_front(self, node: _Node) -> None:
        """Insert `node` directly after the head sentinel (most recent)."""
        first = self._head.next
        assert first is not None, "head sentinel is unlinked"
        node.prev = self._head
        node.next = first
        first.prev = node
        self._head.next = node

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, key: int) -> int:
        """Return the value for `key`, or -1.  Marks the key as used."""
        node = self._map.get(key)
        if node is None:
            return -1

        if node is not self._head.next:     # already most recent -> no work
            self._detach(node)
            self._push_front(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        """Insert or update `key`, evicting the LRU entry when full."""
        node = self._map.get(key)

        if node is not None:                # update in place, refresh recency
            node.value = value
            if node is not self._head.next:
                self._detach(node)
                self._push_front(node)
            return

        if len(self._map) == self._capacity:
            lru = self._tail.prev           # the oldest real node
            assert lru is not None, "tail sentinel is unlinked"
            self._detach(lru)
            del self._map[lru.key]

        node = _Node(key, value)
        self._map[key] = node
        self._push_front(node)

    # ------------------------------------------------------------------
    # Introspection helpers (used by the tests and the demo)
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._map)

    @property
    def capacity(self) -> int:
        return self._capacity

    def __contains__(self, key: object) -> bool:
        return key in self._map

    def keys_mru_to_lru(self) -> Iterator[int]:
        """Yield keys from most to least recently used - O(n), debug only."""
        current = self._head.next
        while current is not self._tail:
            assert current is not None
            yield current.key
            current = current.next

    def __repr__(self) -> str:
        entries = ", ".join(
            f"{k}: {self._map[k].value}" for k in self.keys_mru_to_lru()
        )
        return f"LRUCache(capacity={self._capacity}, [{entries}])"
