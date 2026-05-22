"""Hot-reload behaviour — templates picked up after disk changes.

Each test forces the throttle to 0 so every load triggers a stat scan,
then mutates the search-path directory and verifies the next
``load_template`` call sees the new content.

The ``SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL`` env var controls the
throttle:
    > 0    throttle in seconds
    = 0    check on every call (used by these tests)
    < 0    disabled — never re-check
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from app.services.template import (
    TemplateNotFoundError,
    list_templates,
    load_template,
)
from app.services.template.loader import (
    _force_rescan_for_tests,
    _maybe_invalidate_cache,
    _snapshot_mtimes,
)


@pytest.fixture
def fast_reload(monkeypatch):
    """Force hot-reload to fire on every call."""
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL", "0")
    _force_rescan_for_tests()
    yield
    _force_rescan_for_tests()


@pytest.fixture
def tdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_DIR", str(tmp_path))
    _force_rescan_for_tests()
    yield tmp_path
    _force_rescan_for_tests()


def _write(p: Path, body: dict) -> None:
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


# ---------- file-change detection -------------------------------------------


def test_edit_to_file_picked_up_after_invalidate(tdir, fast_reload):
    f = tdir / "vlog.json"
    _write(f, {"transition": {"style": "calm"}})
    assert load_template("vlog").transition.style == "calm"

    # Sleep just enough that mtime resolution catches us (HFS+/APFS = 1s)
    time.sleep(1.05)
    _write(f, {"transition": {"style": "energetic"}})

    assert load_template("vlog").transition.style == "energetic"


def test_new_file_appears_after_invalidate(tdir, fast_reload):
    _write(tdir / "a.json", {"transition": {"style": "calm"}})
    assert "a" in {s.name for s in list_templates()}

    time.sleep(1.05)
    _write(tdir / "b.json", {"transition": {"style": "energetic"}})

    names = {s.name for s in list_templates()}
    assert "a" in names and "b" in names
    assert load_template("b").transition.style == "energetic"


def test_deleted_file_disappears_after_invalidate(tdir, fast_reload):
    _write(tdir / "gone.json", {"transition": {"style": "calm"}})
    assert load_template("gone").transition.style == "calm"

    time.sleep(1.05)
    (tdir / "gone.json").unlink()

    with pytest.raises(TemplateNotFoundError):
        load_template("gone")


# ---------- throttle behaviour ----------------------------------------------


def test_throttle_skips_intermediate_calls(tdir, monkeypatch):
    """With a 60s throttle, an edit shouldn't be visible until throttle elapses."""
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL", "60")
    _force_rescan_for_tests()

    f = tdir / "throttled.json"
    _write(f, {"transition": {"style": "calm"}})
    assert load_template("throttled").transition.style == "calm"

    # Edit + immediate reload — throttle blocks the rescan, old value sticks
    time.sleep(1.05)
    _write(f, {"transition": {"style": "energetic"}})
    assert load_template("throttled").transition.style == "calm"  # stale on purpose

    # fresh=True still bypasses everything
    assert load_template("throttled", fresh=True).transition.style == "energetic"


def test_disabled_interval_never_rescans(tdir, monkeypatch):
    """Negative interval → hot-reload off entirely."""
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL", "-1")
    _force_rescan_for_tests()

    f = tdir / "frozen.json"
    _write(f, {"transition": {"style": "calm"}})
    assert load_template("frozen").transition.style == "calm"

    time.sleep(1.05)
    _write(f, {"transition": {"style": "energetic"}})

    # Cache stays warm forever
    assert load_template("frozen").transition.style == "calm"


# ---------- snapshot helper -------------------------------------------------


def test_snapshot_mtimes_lists_all_json(tdir, fast_reload):
    _write(tdir / "a.json", {"name": "a"})
    _write(tdir / "b.json", {"name": "b"})
    # Hidden / underscore-prefixed files are ignored
    (tdir / "_hidden.json").write_text("{}")
    (tdir / ".dotfile.json").write_text("{}")

    snap = _snapshot_mtimes()
    paths = {Path(p).name for p in snap}
    assert "a.json" in paths
    assert "b.json" in paths
    assert "_hidden.json" not in paths
    assert ".dotfile.json" not in paths


def test_maybe_invalidate_runs_without_search_paths(monkeypatch, tmp_path):
    """When the env points to a nonexistent dir, invalidate should be a no-op."""
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_DIR", str(tmp_path / "ghost"))
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL", "0")
    _force_rescan_for_tests()
    # Should not raise
    _maybe_invalidate_cache()
