"""TTL-cache unit tests — pure Python, no FastAPI."""

from __future__ import annotations

import time

import pytest

from app.services.analytics.cache import TTLCache


def test_cache_hit_within_ttl():
    cache = TTLCache(ttl_seconds=10.0)
    cache.set(("foo",), 42)
    assert cache.get(("foo",)) == 42


def test_cache_miss_after_ttl_expires():
    cache = TTLCache(ttl_seconds=0.05)
    cache.set(("foo",), 42)
    time.sleep(0.08)
    assert cache.get(("foo",)) is None


def test_cache_invalidate_all():
    cache = TTLCache(ttl_seconds=10.0)
    cache.set(("a",), 1)
    cache.set(("b",), 2)
    dropped = cache.invalidate()
    assert dropped == 2
    assert cache.get(("a",)) is None
    assert cache.get(("b",)) is None


def test_cache_invalidate_prefix():
    cache = TTLCache(ttl_seconds=10.0)
    cache.set(("overview", 1, "30d"), "a")
    cache.set(("overview", 2, "30d"), "b")
    cache.set(("trends", 1, "30d"), "c")
    dropped = cache.invalidate(prefix=("overview",))
    assert dropped == 2
    assert cache.get(("overview", 1, "30d")) is None
    assert cache.get(("trends", 1, "30d")) == "c"


def test_cache_respects_maxsize_lru():
    cache = TTLCache(ttl_seconds=10.0, maxsize=3)
    for i in range(5):
        cache.set((i,), i)
    # Eviction is approximate-LRU by expires_at — but we just need the
    # cache to never grow beyond maxsize.
    assert cache.size() <= 3


def test_cache_rejects_non_positive_ttl():
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=0)


def test_cache_set_with_zero_ttl_skips_insertion():
    cache = TTLCache(ttl_seconds=10.0)
    cache.set(("foo",), 1, ttl_seconds=0)
    assert cache.get(("foo",)) is None
