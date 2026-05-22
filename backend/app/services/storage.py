"""Local-filesystem storage helpers for user uploads.

Used by the brand-kit logo endpoint and (eventually) other asset uploads.
Files live under ``<settings.storage_root>/brand_kits/<workspace_id>/`` so
removing a workspace can be done with a single ``shutil.rmtree``.

The functions here are async-friendly stubs around ``pathlib``: real
ffmpeg work happens in :mod:`app.services.video`, so we don't need an
S3 adapter to make the API usable in tests.
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("shadowblade.storage")

# Mirror the static mount in ``main.py`` so URLs we hand back resolve to
# the served files. Keep these two strings in lock-step.
STATIC_MOUNT_PREFIX = "/static/storage"


# Allowed logo image extensions and their content-type families. We never
# trust the client-supplied content-type alone — the extension also has to
# match one of these, and the image must decode through Pillow.
ALLOWED_LOGO_EXTENSIONS: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

# Hard ceilings — we reject earlier, before reading into memory.
MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5 MiB


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(raw: str) -> str:
    """Strip path separators / weird characters out of an upload filename.

    Falls back to a digest if the input is empty or all-junk so we always
    return something usable.
    """
    name = Path(raw).name  # drop any directory parts the client snuck in
    sanitised = _SAFE_NAME_RE.sub("_", name).strip("._-")
    if not sanitised:
        sanitised = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return sanitised[:120]  # keep filesystem-friendly


def brand_kit_logo_dir(workspace_id: int) -> Path:
    """Filesystem directory backing brand-kit logos for a workspace."""
    root = Path(settings.storage_root) / "brand_kits" / str(workspace_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def public_url_for(path: Path) -> str:
    """Map an on-disk path under ``storage_root`` to its public URL.

    Returns a path beginning with the static mount prefix that FastAPI
    serves via :class:`fastapi.staticfiles.StaticFiles`.
    """
    storage_root = Path(settings.storage_root).resolve()
    try:
        rel = path.resolve().relative_to(storage_root)
    except ValueError:
        raise ValueError(
            f"path {path} is outside storage_root {storage_root}"
        ) from None
    return f"{STATIC_MOUNT_PREFIX}/{rel.as_posix()}"


def save_brand_logo(
    *,
    workspace_id: int,
    filename: str,
    data: bytes,
) -> Path:
    """Write logo bytes to the workspace's brand-kit storage and return the path.

    Caller is responsible for validating the content-type / extension *and*
    the byte length before invoking this. We re-validate the byte cap here
    as a belt-and-braces safety net.
    """
    if len(data) > MAX_LOGO_BYTES:
        raise ValueError(
            f"logo too large: {len(data)} bytes (max {MAX_LOGO_BYTES})"
        )
    target_dir = brand_kit_logo_dir(workspace_id)
    target = target_dir / safe_filename(filename)
    target.write_bytes(data)
    log.info(
        "saved brand-kit logo workspace=%s bytes=%s path=%s",
        workspace_id,
        len(data),
        target,
    )
    return target


def reset_storage(root: Path | None = None) -> None:
    """Test helper — remove everything under ``brand_kits/``.

    Called by integration tests that want a known-clean filesystem.
    """
    base = Path(root or settings.storage_root) / "brand_kits"
    if base.exists():
        shutil.rmtree(base)


__all__ = [
    "ALLOWED_LOGO_EXTENSIONS",
    "MAX_LOGO_BYTES",
    "STATIC_MOUNT_PREFIX",
    "brand_kit_logo_dir",
    "public_url_for",
    "reset_storage",
    "safe_filename",
    "save_brand_logo",
]
