"""Keyword-driven stock footage search — no API key required.

Two free, key-less sources:

  * yt-dlp's built-in search prefixes (``ytsearchN:keyword``,
    ``ytsearchdate:keyword``, ``scsearchN:keyword`` …) — works against
    YouTube et al. yt-dlp handles the search-result-page scraping for us.

  * archive.org's open advanced search API — returns clip identifiers for
    movies/short-films matching a query. We fetch the metadata, pick an
    MP4 derivative, and download it. archive.org is reachable from China
    without a VPN, so it's our China-friendly fallback.

Both routes write into ``<storage_root>/stock/search/<source>_<id>.mp4`` and
return absolute paths the mix pipeline can ingest.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.services.stock.youtube import _binary as _ytdlp_bin

log = logging.getLogger("shadowblade.stock.search")


@dataclass(slots=True)
class FoundClip:
    source: str  # "youtube" | "archive"
    path: Path
    title: str
    duration: float
    source_id: str
    width: int = 0
    height: int = 0


# ─── yt-dlp search ─────────────────────────────────────────────────────


async def ytsearch_download(
    keyword: str,
    out_dir: str | Path,
    *,
    count: int = 3,
    max_seconds: float = 6.0,
    max_height: int = 720,
    max_duration_filter: int = 120,  # skip very long uploads
    prefix: str = "ytsearch",  # ytsearch / scsearch / bilisearch
) -> list[FoundClip]:
    """Search via yt-dlp's ``<prefix>N:keyword`` syntax and download N matches."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = _ytdlp_bin()

    # Search 4 extra candidates so we can skip any that 403/region-block.
    search_query = f"{prefix}{count + 4}:{keyword}"

    found: list[FoundClip] = []
    cmd: list[str] = [
        binary,
        "--no-warnings",
        "--no-playlist",
        "--socket-timeout",
        "12",
        "--match-filter",
        f"duration<{max_duration_filter}",
        "-f",
        f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/b[height<={max_height}][ext=mp4]/b",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_dir / "yt_%(id)s.%(ext)s"),
        "--print-json",
        # Honor download-sections so we don't pull 60-second files we only
        # need 6 seconds of. yt-dlp evaluates this per-format.
        "--download-sections",
        f"*0:00-0:{int(max_seconds):02d}",
        search_query,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise RuntimeError(f"yt-dlp search timed out: {keyword!r}") from exc

    if proc.returncode != 0 and not stdout:
        raise RuntimeError(
            f"yt-dlp search failed: {stderr.decode(errors='ignore')[-300:]}"
        )

    import json as _json

    for line in stdout.decode(errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            meta = _json.loads(line)
        except _json.JSONDecodeError:
            continue
        produced = out_dir / f"yt_{meta.get('id', 'unknown')}.mp4"
        if not produced.exists() or produced.stat().st_size < 30_000:
            continue
        found.append(
            FoundClip(
                source="youtube",
                path=produced,
                title=str(meta.get("title", produced.stem)),
                duration=float(meta.get("duration", 0) or 0),
                source_id=str(meta.get("id", "")),
                width=int(meta.get("width", 0) or 0),
                height=int(meta.get("height", 0) or 0),
            )
        )
        if len(found) >= count:
            break

    return found


# ─── archive.org search ────────────────────────────────────────────────


ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA = "https://archive.org/metadata"
_VIDEO_EXT_PRIORITY = (".mp4", ".mov", ".m4v")


async def archive_search_download(
    keyword: str,
    out_dir: str | Path,
    *,
    count: int = 3,
    max_seconds: float = 6.0,
    rows: int = 12,
) -> list[FoundClip]:
    """Hit archive.org's advanced-search JSON, pick MP4 derivatives, download."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "q": f'"{keyword}" mediatype:movies',
        "fl[]": ["identifier", "title", "downloads"],
        "sort[]": "downloads desc",
        "rows": str(rows),
        "output": "json",
    }
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as cli:
        r = await cli.get(ARCHIVE_SEARCH, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"archive.org search failed: {r.status_code}")
        docs = (r.json().get("response") or {}).get("docs", [])

    found: list[FoundClip] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0), follow_redirects=True) as cli:
        for doc in docs:
            identifier = doc.get("identifier")
            if not identifier:
                continue
            try:
                meta_r = await cli.get(f"{ARCHIVE_METADATA}/{identifier}")
                if meta_r.status_code != 200:
                    continue
                meta = meta_r.json()
            except (httpx.RequestError, ValueError):
                continue
            pick = _pick_archive_file(meta.get("files", []))
            if not pick:
                continue

            target = out_dir / f"archive_{identifier}.mp4"
            url = f"https://archive.org/download/{identifier}/{pick['name']}"
            try:
                if not target.exists() or target.stat().st_size < 50_000:
                    async with cli.stream("GET", url) as resp:
                        if resp.status_code != 200:
                            continue
                        with open(target, "wb") as f:
                            async for chunk in resp.aiter_bytes(64 * 1024):
                                f.write(chunk)
            except (httpx.RequestError, OSError):
                continue

            # Trim to max_seconds so we don't keep 90-minute movies on disk
            await _trim_in_place(target, max_seconds)

            duration = float(pick.get("length", 0) or 0) or max_seconds
            found.append(
                FoundClip(
                    source="archive",
                    path=target,
                    title=str(doc.get("title") or identifier),
                    duration=min(duration, max_seconds),
                    source_id=identifier,
                    width=int(pick.get("width", 0) or 0),
                    height=int(pick.get("height", 0) or 0),
                )
            )
            if len(found) >= count:
                break
    return found


def _pick_archive_file(files: list[dict]) -> dict | None:
    """Pick the smallest-but-still-usable MP4 derivative from a metadata list.

    Prefers ``h.264`` or ``MPEG4`` formats with explicit width/height. Avoids
    huge ProRes/lossless masters that would take forever to download.
    """
    mp4s: list[tuple[int, dict]] = []
    for f in files:
        name = f.get("name", "")
        ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
        if ext not in {"mp4", "mov", "m4v"}:
            continue
        # Estimate priority: prefer h.264 + sub-200MB
        size = int(f.get("size") or 0)
        if 1_000_000 <= size <= 250_000_000:
            mp4s.append((size, f))
    if not mp4s:
        return None
    mp4s.sort(key=lambda t: t[0])
    return mp4s[0][1]


def _safe_seconds(value: str | float | None) -> float:
    """Archive.org duration field can be ``"H:MM:SS"`` or ``"123.4"`` etc."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    m = re.match(r"^(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)$", str(value).strip())
    if m:
        h = int(m.group(1) or 0)
        mn = int(m.group(2))
        s = float(m.group(3))
        return h * 3600 + mn * 60 + s
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


async def _trim_in_place(path: Path, max_seconds: float) -> None:
    trimmed = path.with_suffix(".trim.mp4")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(path),
        "-t",
        f"{max_seconds:.2f}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ac",
        "1",
        "-ar",
        "48000",
        str(trimmed),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    _, err = await proc.communicate()
    if proc.returncode == 0 and trimmed.exists() and trimmed.stat().st_size > 30_000:
        trimmed.replace(path)
    else:
        if trimmed.exists():
            try:
                trimmed.unlink()
            except OSError:
                pass


# ─── unified search-and-download ──────────────────────────────────────


async def search_and_download(
    keyword: str,
    out_dir: str | Path,
    *,
    count: int = 3,
    max_seconds: float = 6.0,
    sources: tuple[str, ...] = ("youtube", "archive"),
) -> list[FoundClip]:
    """Try each source in order until we have ``count`` usable clips.

    Falls back transparently: if YouTube search returns 0 (region-blocked
    or query has no short matches) we move on to archive.org and so on.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    found: list[FoundClip] = []
    last_error: Exception | None = None

    for source in sources:
        if len(found) >= count:
            break
        try:
            if source == "youtube":
                more = await ytsearch_download(
                    keyword,
                    out_dir,
                    count=count - len(found),
                    max_seconds=max_seconds,
                )
            elif source == "archive":
                more = await archive_search_download(
                    keyword,
                    out_dir,
                    count=count - len(found),
                    max_seconds=max_seconds,
                )
            else:
                continue
        except RuntimeError as exc:
            last_error = exc
            log.warning("source %s failed for %r: %s", source, keyword, exc)
            continue
        found.extend(more)

    if not found:
        msg = f"no clips found for keyword: {keyword!r}"
        if last_error:
            msg += f" (last error: {last_error})"
        raise RuntimeError(msg)
    return found[:count]


__all__ = [
    "FoundClip",
    "ytsearch_download",
    "archive_search_download",
    "search_and_download",
]
