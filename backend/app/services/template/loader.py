"""Template loader — discovers and resolves templates from disk.

Resolution order (first match wins for a given ``name``):

1. ``$SHADOWBLADE_TEMPLATES_DIR`` — runtime override, comma-separated
2. ``<repo_root>/templates``     — project-level user templates
3. ``<package>/builtin``         — frozen builtin set shipped with code

A template referencing ``extends: "<parent>"`` is resolved recursively
and merged via :meth:`Template.merged_with`. Cycles raise
``RuntimeError``.

Caching & hot-reload
--------------------
Loaded templates are cached per-process via an LRU. Before each cached
lookup we do a cheap stat-based check of the search path: if any
``*.json`` file's mtime changed, was added or removed since the last
check, the cache is cleared so the next ``load_template`` reads fresh
content from disk. Throttle to ``SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL``
seconds (default 1.0) to avoid stat'ing every call. Set the interval to
``0`` to check on every call (handy for tests); negative values disable
hot-reload entirely.

``fresh=True`` on :func:`load_template` always bypasses both the
throttle and the cache.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services.template.schema import Template

log = logging.getLogger("shadowblade.template.loader")


# --- discovery --------------------------------------------------------------

_PACKAGE_BUILTIN = Path(__file__).resolve().parent / "builtin"


def _repo_root() -> Path:
    # backend/app/services/template/loader.py  →  repo root is 4 parents up
    return Path(__file__).resolve().parents[4]


def template_search_paths() -> list[Path]:
    """Ordered list of directories searched for templates."""
    paths: list[Path] = []
    env = os.environ.get("SHADOWBLADE_TEMPLATES_DIR", "").strip()
    if env:
        paths.extend(Path(p).expanduser().resolve() for p in env.split(",") if p.strip())
    paths.append(_repo_root() / "templates")
    paths.append(_PACKAGE_BUILTIN)
    # Dedup while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


class TemplateNotFoundError(LookupError):
    """Raised when a requested template name has no matching JSON file."""


@dataclass(frozen=True, slots=True)
class TemplateSummary:
    """Lightweight metadata for listing endpoints."""

    name: str
    version: str
    description: str
    extends: str | None
    tags: tuple[str, ...]
    source: str  # absolute path of the JSON file
    builtin: bool


def _scan_dir(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        return {}
    out: dict[str, Path] = {}
    for entry in sorted(directory.glob("*.json")):
        if entry.name.startswith("_") or entry.name.startswith("."):
            continue
        out[entry.stem] = entry
    return out


def _index_all() -> dict[str, Path]:
    """First-occurrence-wins index across the search path."""
    merged: dict[str, Path] = {}
    for directory in template_search_paths():
        for name, path in _scan_dir(directory).items():
            merged.setdefault(name, path)
    return merged


# --- loading ----------------------------------------------------------------


def _read_raw(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"template JSON at {path} is malformed: {exc}") from exc


# --- hot-reload (mtime-based invalidation) ----------------------------------

_FILE_MTIMES: dict[str, float] = {}
_LAST_RELOAD_CHECK: float = 0.0


def _reload_interval() -> float:
    """Throttle for stat scans. Negative disables hot-reload."""
    raw = os.environ.get("SHADOWBLADE_TEMPLATES_RELOAD_INTERVAL", "1.0")
    try:
        return float(raw)
    except ValueError:
        return 1.0


def _snapshot_mtimes() -> dict[str, float]:
    """Map ``abs path → mtime`` over every JSON file in the search path."""
    out: dict[str, float] = {}
    for directory in template_search_paths():
        if not directory.is_dir():
            continue
        for entry in directory.glob("*.json"):
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue
            try:
                out[str(entry.resolve())] = entry.stat().st_mtime
            except OSError:
                continue
    return out


def _maybe_invalidate_cache() -> None:
    """Stat the search path; clear the cache if any template file changed.

    Skipped when the throttle window hasn't elapsed since the last check.
    Throttle of ``0`` forces a check every call; negative disables it.
    """
    global _LAST_RELOAD_CHECK
    interval = _reload_interval()
    if interval < 0:
        return
    now = time.monotonic()
    if interval > 0 and (now - _LAST_RELOAD_CHECK) < interval:
        return
    _LAST_RELOAD_CHECK = now

    snap = _snapshot_mtimes()
    if snap != _FILE_MTIMES:
        if _FILE_MTIMES:  # not the first call — log the actual change
            added = set(snap) - set(_FILE_MTIMES)
            removed = set(_FILE_MTIMES) - set(snap)
            modified = {
                p for p in snap.keys() & _FILE_MTIMES.keys()
                if snap[p] != _FILE_MTIMES[p]
            }
            log.info(
                "templates hot-reload: +%d -%d ~%d → cache invalidated",
                len(added), len(removed), len(modified),
            )
        _load_cached.cache_clear()
        _FILE_MTIMES.clear()
        _FILE_MTIMES.update(snap)


@lru_cache(maxsize=128)
def _load_cached(name: str) -> Template:
    return _load_uncached(name, _seen=frozenset())


def _load_uncached(name: str, *, _seen: frozenset[str]) -> Template:
    if name in _seen:
        chain = " → ".join([*_seen, name])
        raise RuntimeError(f"template extends cycle: {chain}")
    index = _index_all()
    path = index.get(name)
    if path is None:
        raise TemplateNotFoundError(
            f"template '{name}' not found in: "
            + ", ".join(str(p) for p in template_search_paths())
        )
    raw = _read_raw(path)
    # Allow JSON files to omit the name; fill it from filename for ergonomics
    raw.setdefault("name", name)
    if raw.get("name") != name:
        log.warning(
            "template %s: name field %r overridden to %r to match filename",
            path,
            raw.get("name"),
            name,
        )
        raw["name"] = name
    tmpl = Template.model_validate(raw)
    if tmpl.extends:
        parent = _load_uncached(tmpl.extends, _seen=_seen | {name})
        tmpl = parent.merged_with(tmpl)
    return tmpl


def load_template(name: str, *, fresh: bool = False) -> Template:
    """Load a template by slug.

    Parameters
    ----------
    name:
        Template slug (filename stem). Case-sensitive.
    fresh:
        If True, skip both the hot-reload throttle and the LRU cache.
        Useful for tests and the ``/templates?fresh=true`` admin path.
    """
    if fresh:
        _load_cached.cache_clear()
        _FILE_MTIMES.clear()
        global _LAST_RELOAD_CHECK
        _LAST_RELOAD_CHECK = 0.0
    else:
        _maybe_invalidate_cache()
    return _load_cached(name)


def list_templates() -> list[TemplateSummary]:
    """Return a summary list of every discoverable template."""
    _maybe_invalidate_cache()
    out: list[TemplateSummary] = []
    builtin_dir = _PACKAGE_BUILTIN.resolve()
    for name, path in sorted(_index_all().items()):
        try:
            raw = _read_raw(path)
            raw.setdefault("name", name)
            tmpl = Template.model_validate(raw)
        except (RuntimeError, ValueError) as exc:
            log.warning("skipping malformed template %s: %s", path, exc)
            continue
        out.append(
            TemplateSummary(
                name=tmpl.name,
                version=tmpl.version,
                description=tmpl.description,
                extends=tmpl.extends,
                tags=tuple(tmpl.tags),
                source=str(path),
                builtin=str(path.resolve()).startswith(str(builtin_dir)),
            )
        )
    return out


__all__ = [
    "TemplateNotFoundError",
    "TemplateSummary",
    "list_templates",
    "load_template",
    "template_search_paths",
]


def _force_rescan_for_tests() -> None:
    """Reset hot-reload state — for use in unit tests that mutate the
    search path mid-run. Not part of the public API.
    """
    global _LAST_RELOAD_CHECK
    _LAST_RELOAD_CHECK = 0.0
    _FILE_MTIMES.clear()
    _load_cached.cache_clear()
