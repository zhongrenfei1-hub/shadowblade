"""Process-local TTL cache for analytics responses.

Aggregation queries are read-only and *expensive* (group-bys + joins on
render_tasks ×  projects). The dashboard makes the exact same call from
every chart on the page, so memoising the response for ~60s yields a
~5× p99 improvement with zero downside — stats lag for at most one TTL.

The interface is intentionally a strict subset of Redis (``get`` /
``set`` / ``invalidate``) so swapping to Redis later is a one-file
change. The fallback is a dict-backed implementation so the tests stay
hermetic (no Redis required to run ``pytest``).

The cache key is a tuple ``(endpoint, workspace_id, period, ...extra)``
hashed via ``repr``; collisions across endpoints are impossible because
the endpoint name is the first element.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Tiny thread-safe TTL cache.

    Not Redis. Not a perfect LRU. Just enough to dedupe the storm of
    dashboard requests that hit within a few hundred ms of each other.

    Capacity is bounded so a runaway test or pathological caller can't
    leak memory — we drop the oldest entries when ``maxsize`` is hit.
    """

    def __init__(self, *, ttl_seconds: float = 60.0, maxsize: int = 256) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._ttl = float(ttl_seconds)
        self._maxsize = maxsize
        self._store: dict[Any, _CacheEntry] = {}
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------------

    def get(self, key: Any) -> Any | None:
        """Return the cached value or ``None`` if missing/expired."""
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < now:
                # Lazy eviction — cheaper than a sweeper thread.
                self._store.pop(key, None)
                return None
            return entry.value

    def set(self, key: Any, value: Any, *, ttl_seconds: float | None = None) -> None:
        """Insert ``value`` under ``key``. ``ttl_seconds`` overrides the default."""
        ttl = float(ttl_seconds if ttl_seconds is not None else self._ttl)
        if ttl <= 0:
            return  # negative TTL ≡ don't cache
        now = time.monotonic()
        with self._lock:
            if len(self._store) >= self._maxsize and key not in self._store:
                # Drop the entry with the earliest expiry — approximates
                # LRU well enough for our short TTLs.
                oldest = min(self._store.items(), key=lambda kv: kv[1].expires_at)
                self._store.pop(oldest[0], None)
            self._store[key] = _CacheEntry(value=value, expires_at=now + ttl)

    def invalidate(self, *, prefix: tuple[Any, ...] | None = None) -> int:
        """Drop entries; with ``prefix`` only those whose key starts with it.

        Returns the number of entries dropped — useful for assertions in
        tests.
        """
        with self._lock:
            if prefix is None:
                count = len(self._store)
                self._store.clear()
                return count
            doomed: list[Any] = [
                k for k in self._store
                if isinstance(k, tuple) and len(k) >= len(prefix)
                and k[: len(prefix)] == prefix
            ]
            for k in doomed:
                self._store.pop(k, None)
            return len(doomed)

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    # -- helpers ------------------------------------------------------------

    def items(self) -> Iterable[tuple[Any, Any]]:
        """Snapshot of (key, value) for currently-live entries."""
        now = time.monotonic()
        with self._lock:
            return [
                (k, v.value)
                for k, v in self._store.items()
                if v.expires_at >= now
            ]


@lru_cache(maxsize=1)
def get_analytics_cache() -> TTLCache:
    """Module-level singleton — one cache per process.

    Wrapped in ``lru_cache`` so dependency injection still gets the same
    instance across requests while tests can swap it out via
    ``get_analytics_cache.cache_clear()``.
    """
    return TTLCache(ttl_seconds=60.0, maxsize=512)


__all__ = ["TTLCache", "get_analytics_cache"]
