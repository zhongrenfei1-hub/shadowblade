"""yt-dlp adapter — pull a clip (or section) from any URL yt-dlp supports.

Supports:
  - YouTube, Vimeo, TikTok, Douyin (抖音), Bilibili (B站), Twitter, Instagram,
    Twitch, Reddit, Dailymotion, and ~1500 other sites.

Usage:
  await ytdlp_download(url, out_dir, sections="*0:00-0:10")
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("shadowblade.stock.ytdlp")


@dataclass(slots=True)
class YtClip:
    path: Path
    source_url: str
    title: str
    duration: float
    width: int
    height: int


def _binary() -> str:
    # Prefer yt-dlp from the same venv that runs uvicorn (PATH may not include
    # the venv's bin dir, but ``sys.executable``'s parent always does).
    import sys

    venv_bin = Path(sys.executable).parent / "yt-dlp"
    if venv_bin.exists():
        return str(venv_bin)
    path = shutil.which("yt-dlp")
    if path:
        return path
    raise RuntimeError(
        "yt-dlp is not installed. Install with `pip install yt-dlp` (already "
        "in backend/requirements.txt) and re-run."
    )


def has_ytdlp() -> bool:
    try:
        _binary()
        return True
    except RuntimeError:
        return False


async def ytdlp_download(
    url: str,
    out_dir: str | Path,
    *,
    sections: str | None = None,  # "*0:00-0:10" or "0:20-0:30" (yt-dlp syntax)
    max_height: int = 1920,
    cookies_browser: str | None = None,
    filename_hint: str | None = None,
) -> YtClip:
    """Download a clip from a URL.

    ``sections`` controls which time range to grab — saves bandwidth for long
    source videos. yt-dlp's syntax: ``*HH:MM:SS-HH:MM:SS`` (the asterisk means
    "use the first match").

    ``cookies_browser`` is one of: chrome / safari / firefox — useful for
    sites that require login (YouTube age-restricted, Bilibili paid videos).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = _binary()

    stem = filename_hint or f"yt_{abs(hash(url)) % 10_000_000:07d}"
    output_template = str(out_dir / f"{stem}.%(ext)s")

    cmd: list[str] = [
        binary,
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--print-json",
        # Prefer MP4 + cap height
        "-f",
        f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/b[height<={max_height}][ext=mp4]/b",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
    ]
    if sections:
        cmd += ["--download-sections", sections]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    cmd.append(url)

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed: {stderr.decode(errors='ignore')[-400:]}"
        )

    # yt-dlp --print-json emits the metadata json on stdout
    import json as _json

    meta: dict = {}
    for line in stdout.decode(errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                meta = _json.loads(line)
                break
            except _json.JSONDecodeError:
                continue

    # Locate the produced file — yt-dlp may have used a different extension
    candidates = sorted(out_dir.glob(f"{stem}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError("yt-dlp ran but produced no output file")
    produced = candidates[0]

    return YtClip(
        path=produced,
        source_url=url,
        title=str(meta.get("title", produced.stem)),
        duration=float(meta.get("duration", 0) or 0),
        width=int(meta.get("width", 0) or 0),
        height=int(meta.get("height", 0) or 0),
    )


__all__ = ["YtClip", "ytdlp_download"]
