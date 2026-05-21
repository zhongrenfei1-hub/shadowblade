"""Probe the running ffmpeg for which optional filters are compiled in.

We use this to gracefully degrade when drawtext, subtitles, or libass are
missing — common when ffmpeg is built without ``--enable-libfreetype`` /
``--enable-libass`` (Homebrew default in some bottles).

When a feature is missing the pipeline rasterises the same content via Pillow
and overlays it as a PNG, which works on any ffmpeg with overlay + scale2ref.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache

from app.services.video.probe import FFMPEG


@dataclass(slots=True, frozen=True)
class FFmpegFeatures:
    has_drawtext: bool
    has_subtitles: bool  # 'subtitles' / 'ass' filter (libass)
    has_libass: bool
    has_videotoolbox: bool

    @property
    def can_burn_subtitles(self) -> bool:
        return self.has_subtitles and self.has_libass


@lru_cache(maxsize=1)
def detect_features() -> FFmpegFeatures:
    ffmpeg = shutil.which(FFMPEG)
    if not ffmpeg:
        return FFmpegFeatures(False, False, False, False)
    try:
        filters = subprocess.run(
            [ffmpeg, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        encoders = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        info = subprocess.run(
            [ffmpeg, "-hide_banner", "-buildconf"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout + subprocess.run(
            [ffmpeg, "-hide_banner", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (subprocess.TimeoutExpired, OSError):
        return FFmpegFeatures(False, False, False, False)

    def _has_filter(name: str) -> bool:
        for line in filters.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == name:
                return True
        return False

    return FFmpegFeatures(
        has_drawtext=_has_filter("drawtext"),
        has_subtitles=_has_filter("subtitles") or _has_filter("ass"),
        has_libass="libass" in info,
        has_videotoolbox="h264_videotoolbox" in encoders,
    )


__all__ = ["FFmpegFeatures", "detect_features"]
