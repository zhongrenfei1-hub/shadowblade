"""Per-user API-key secrets store — persisted to ``~/.shadowblade/secrets.json``.

Design goals:
  - **One file, machine-local.** Outside the repo, so accidental ``git add .``
    can't leak keys.
  - **Load into os.environ on startup** so existing code reading
    ``os.environ.get('PEXELS_API_KEY')`` keeps working unchanged.
  - **Updates take effect immediately** (the API endpoints write the file
    and re-mirror into os.environ in the same call).
  - **GET returns a *masked* view** — never the full key over the wire.

This is intentionally NOT a vault — keys sit on disk in plaintext, mode 600.
For team/production deploys use real secret manager (1Password, AWS SM, ...).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Iterator

log = logging.getLogger("shadowblade.secrets")

# Catalogue: which keys we know about and what env var they map to.
# Add new providers here; the GET endpoint discovers them automatically.
SUPPORTED_KEYS: dict[str, dict] = {
    "pexels": {
        "env": "PEXELS_API_KEY",
        "label": "Pexels Videos API",
        "hint": "在 https://www.pexels.com/api/new/ 申请，1 分钟免费",
        "test_url": "https://api.pexels.com/videos/search?query=test&per_page=1",
        "test_header": "Authorization",
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "label": "OpenAI / OpenRouter",
        "hint": "sk-... · 在 https://platform.openai.com/api-keys 申请",
        "test_url": None,
        "test_header": None,
    },
    "deepseek": {
        "env": "DEEPSEEK_API_KEY",
        "label": "DeepSeek",
        "hint": "在 https://platform.deepseek.com/api_keys 申请，~$0.001/视频",
        "test_url": None,
        "test_header": None,
    },
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "label": "Anthropic Claude",
        "hint": "sk-ant-... · 在 https://console.anthropic.com 申请",
        "test_url": None,
        "test_header": None,
    },
}


_STORE_PATH = Path.home() / ".shadowblade" / "secrets.json"
_LOCK = Lock()


def _read_disk() -> dict[str, str]:
    if not _STORE_PATH.exists():
        return {}
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("secrets file unreadable, starting empty: %s", exc)
        return {}


def _write_disk(data: dict[str, str]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_STORE_PATH)
    try:
        _STORE_PATH.chmod(0o600)
    except OSError:
        pass


def load_into_env() -> dict[str, str]:
    """Read disk store + mirror into ``os.environ``. Called once at startup
    and again after each mutation. Returns the current store dict."""
    with _LOCK:
        data = _read_disk()
        for slug, value in data.items():
            spec = SUPPORTED_KEYS.get(slug)
            if not spec or not value:
                continue
            # Only set when env-var wasn't already provided externally
            if not os.environ.get(spec["env"]):
                os.environ[spec["env"]] = value
        return data


def mask(value: str) -> str:
    """Display-only masking. 'sk-1234567890abcdef' → 'sk-1•••••cdef'."""
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}•••••{value[-4:]}"


def status() -> list[dict]:
    """Snapshot for ``GET /api/v1/keys`` — never reveals the full key."""
    store = _read_disk()
    out: list[dict] = []
    for slug, spec in SUPPORTED_KEYS.items():
        from_store = store.get(slug)
        from_env = os.environ.get(spec["env"])
        # Prefer the stored value as "user-managed"; env wins only when
        # store is empty (matches startup precedence).
        active = bool(from_store or from_env)
        out.append(
            {
                "slug": slug,
                "label": spec["label"],
                "env": spec["env"],
                "hint": spec["hint"],
                "configured": active,
                "source": "store" if from_store else ("env" if from_env else None),
                "masked": mask(from_store or from_env or ""),
            }
        )
    return out


def set_key(slug: str, value: str) -> dict:
    """Persist a key and re-mirror to os.environ. Returns the new status row."""
    if slug not in SUPPORTED_KEYS:
        raise ValueError(f"unknown key slug: {slug}")
    value = (value or "").strip()
    if not value:
        raise ValueError("value is empty — use DELETE to remove")
    with _LOCK:
        data = _read_disk()
        data[slug] = value
        _write_disk(data)
        os.environ[SUPPORTED_KEYS[slug]["env"]] = value
    for row in status():
        if row["slug"] == slug:
            return row
    raise RuntimeError("post-write status lookup failed")


def delete_key(slug: str) -> dict:
    if slug not in SUPPORTED_KEYS:
        raise ValueError(f"unknown key slug: {slug}")
    with _LOCK:
        data = _read_disk()
        existed = data.pop(slug, None)
        _write_disk(data)
        # Only clear env if the value came from store, never from external env.
        env_name = SUPPORTED_KEYS[slug]["env"]
        if os.environ.get(env_name) == existed:
            os.environ.pop(env_name, None)
    for row in status():
        if row["slug"] == slug:
            return row
    raise RuntimeError("post-delete status lookup failed")


async def test_key(slug: str) -> dict:
    """Hit the provider's smallest endpoint to verify the key actually works."""
    if slug not in SUPPORTED_KEYS:
        raise ValueError(f"unknown key slug: {slug}")
    spec = SUPPORTED_KEYS[slug]
    env_value = os.environ.get(spec["env"])
    if not env_value:
        return {"slug": slug, "ok": False, "reason": "key not configured"}
    if not spec.get("test_url"):
        return {"slug": slug, "ok": True, "reason": "stored (no live probe for this provider)"}

    import httpx

    try:
        async with httpx.AsyncClient(timeout=8.0) as cli:
            r = await cli.get(spec["test_url"], headers={spec["test_header"]: env_value})
            if r.status_code == 200:
                return {"slug": slug, "ok": True, "reason": "200 OK"}
            return {"slug": slug, "ok": False, "reason": f"{r.status_code} {r.text[:120]}"}
    except httpx.RequestError as exc:
        return {"slug": slug, "ok": False, "reason": f"network: {exc}"}


def iter_known() -> Iterator[tuple[str, dict]]:
    for slug, spec in SUPPORTED_KEYS.items():
        yield slug, spec


__all__ = [
    "SUPPORTED_KEYS",
    "load_into_env",
    "status",
    "set_key",
    "delete_key",
    "test_key",
    "mask",
    "iter_known",
]
