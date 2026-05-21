"""Pexels Videos API — free royalty-free stock footage.

Get an API key at https://www.pexels.com/api/ (instant, no review).
Set ``PEXELS_API_KEY`` env var or pass via ``api_key=`` to the search call.

Pexels rate limits: 200 requests/hour, 20,000/month — generous for any
reasonable production use.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

log = logging.getLogger("shadowblade.stock.pexels")

PEXELS_API = "https://api.pexels.com/videos"
_TIMEOUT = httpx.Timeout(connect=8.0, read=30.0, write=30.0, pool=8.0)


def _key(explicit: str | None) -> str:
    key = explicit or os.environ.get("PEXELS_API_KEY") or os.environ.get("SHADOWBLADE_PEXELS_KEY")
    if not key:
        raise RuntimeError(
            "PEXELS_API_KEY not set. Get one at https://www.pexels.com/api/ and "
            "export PEXELS_API_KEY=... (or SHADOWBLADE_PEXELS_KEY=...)"
        )
    return key


@dataclass(slots=True)
class PexelsClip:
    id: int
    url: str  # page URL
    download_url: str  # direct MP4 link (best matching quality)
    width: int
    height: int
    duration: int  # seconds
    photographer: str
    photographer_url: str

    @property
    def aspect(self) -> str:
        if not self.height:
            return "?"
        r = self.width / self.height
        if r > 1.5:
            return "16:9"
        if r < 0.7:
            return "9:16"
        return "1:1"


def _pick_file(video_files: list[dict], *, prefer_portrait: bool, max_height: int = 1920) -> dict | None:
    """Pick the highest-quality MP4 file that fits within max_height."""
    candidates = [f for f in video_files if f.get("file_type") == "video/mp4"]
    if not candidates:
        return None
    # Sort by height descending, cap at max_height
    candidates.sort(key=lambda f: (f.get("height") or 0), reverse=True)
    for f in candidates:
        h = f.get("height") or 0
        if h and h <= max_height:
            return f
    return candidates[-1]


async def pexels_search(
    query: str,
    *,
    per_page: int = 8,
    orientation: str = "portrait",  # portrait | landscape | square
    size: str = "medium",  # large | medium | small
    api_key: str | None = None,
) -> list[PexelsClip]:
    """Search Pexels Videos. ``orientation=portrait`` is best for 9:16."""
    key = _key(api_key)
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": orientation,
        "size": size,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"Authorization": key}) as cli:
        r = await cli.get(f"{PEXELS_API}/search", params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Pexels search failed: {r.status_code} {r.text[:200]}")
        data = r.json()
    out: list[PexelsClip] = []
    for video in data.get("videos", []):
        files = video.get("video_files", [])
        pick = _pick_file(files, prefer_portrait=orientation == "portrait")
        if not pick:
            continue
        out.append(
            PexelsClip(
                id=int(video.get("id", 0)),
                url=video.get("url", ""),
                download_url=pick.get("link", ""),
                width=int(pick.get("width") or 0),
                height=int(pick.get("height") or 0),
                duration=int(video.get("duration") or 0),
                photographer=(video.get("user") or {}).get("name", ""),
                photographer_url=(video.get("user") or {}).get("url", ""),
            )
        )
    return out


async def pexels_download(
    clip: PexelsClip,
    out_dir: str | Path,
    *,
    max_seconds: float | None = 6.0,
) -> Path:
    """Download a clip to ``out_dir/pexels_<id>.mp4``. If ``max_seconds`` is
    set the file is trimmed via ffmpeg afterwards to keep storage small."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"pexels_{clip.id}.mp4"
    if target.exists() and target.stat().st_size > 10_000:
        return target

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as cli:
        async with cli.stream("GET", clip.download_url) as r:
            if r.status_code != 200:
                raise RuntimeError(
                    f"Pexels download failed: {r.status_code} on {clip.download_url[:120]}"
                )
            tmp = target.with_suffix(".part")
            with open(tmp, "wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
            tmp.replace(target)

    if max_seconds and clip.duration > max_seconds + 0.5:
        trimmed = target.with_suffix(".trim.mp4")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-y",
            "-i",
            str(target),
            "-t",
            f"{max_seconds:.2f}",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(trimmed),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode == 0 and trimmed.exists():
            trimmed.replace(target)
        else:
            log.warning("ffmpeg trim failed for %s: %s", clip.id, err.decode(errors="ignore")[-200:])

    return target


__all__ = ["PexelsClip", "pexels_search", "pexels_download"]
