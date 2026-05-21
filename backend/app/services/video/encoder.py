"""Encoder presets + thin ffmpeg runner.

Presets are *named profiles* targeting common social/enterprise outputs:
    - ``social_9x16``  — 1080×1920, 30 fps, 8 Mb/s, H.264 high
    - ``hero_16x9``    — 1920×1080, 30 fps, 10 Mb/s
    - ``square_1x1``   — 1080×1080, 30 fps, 8 Mb/s
    - ``preview_360``  — 640×360 (16:9) or 360×640 (9:16), 24 fps, 1.4 Mb/s

Mac builds with ``videotoolbox`` hardware encode use ``h264_videotoolbox``
when available. Falls back to ``libx264`` for portability.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.services.video.probe import FFMPEG


@dataclass(slots=True)
class EncodePreset:
    name: str
    width: int
    height: int
    fps: int
    video_bitrate: str  # e.g. "8M"
    audio_bitrate: str = "192k"
    pix_fmt: str = "yuv420p"
    profile: str = "high"
    level: str = "4.2"
    container: str = "mp4"


PRESETS: dict[str, EncodePreset] = {
    "social_9x16": EncodePreset(
        "social_9x16", 1080, 1920, 30, "8M", "192k"
    ),
    "hero_16x9": EncodePreset(
        "hero_16x9", 1920, 1080, 30, "10M", "192k"
    ),
    "square_1x1": EncodePreset(
        "square_1x1", 1080, 1080, 30, "8M", "192k"
    ),
    "preview_360_9x16": EncodePreset(
        "preview_360_9x16", 360, 640, 24, "1400k", "128k"
    ),
    "preview_360_16x9": EncodePreset(
        "preview_360_16x9", 640, 360, 24, "1400k", "128k"
    ),
}


def list_presets() -> list[str]:
    return list(PRESETS.keys())


def get_preset(name: str) -> EncodePreset:
    if name not in PRESETS:
        raise KeyError(f"unknown encode preset: {name}")
    return PRESETS[name]


_HW_PROBE_CACHE: bool | None = None


def has_videotoolbox() -> bool:
    """Mac VideoToolbox availability check — runs ffmpeg -encoders once."""
    global _HW_PROBE_CACHE
    if _HW_PROBE_CACHE is not None:
        return _HW_PROBE_CACHE
    ffmpeg = shutil.which(FFMPEG)
    if not ffmpeg:
        _HW_PROBE_CACHE = False
        return False
    try:
        import subprocess

        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        _HW_PROBE_CACHE = "h264_videotoolbox" in out.stdout
    except (subprocess.TimeoutExpired, OSError):
        _HW_PROBE_CACHE = False
    return _HW_PROBE_CACHE


def video_codec_args(preset: EncodePreset, *, hw: bool | None = None) -> list[str]:
    use_hw = has_videotoolbox() if hw is None else hw
    if use_hw:
        return [
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            preset.video_bitrate,
            "-pix_fmt",
            preset.pix_fmt,
            "-profile:v",
            preset.profile,
            "-allow_sw",
            "1",
        ]
    return [
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-b:v",
        preset.video_bitrate,
        "-maxrate",
        preset.video_bitrate,
        "-bufsize",
        f"{int(_strip_unit(preset.video_bitrate) * 2)}k",
        "-pix_fmt",
        preset.pix_fmt,
        "-profile:v",
        preset.profile,
        "-level",
        preset.level,
    ]


def audio_codec_args(preset: EncodePreset) -> list[str]:
    return [
        "-c:a",
        "aac",
        "-b:a",
        preset.audio_bitrate,
        "-ar",
        "48000",
        "-ac",
        "2",
    ]


def _strip_unit(rate: str) -> int:
    rate = rate.strip().lower()
    if rate.endswith("m"):
        return int(float(rate[:-1]) * 1000)
    if rate.endswith("k"):
        return int(float(rate[:-1]))
    return int(rate)


async def run_ffmpeg(cmd: list[str], *, timeout: float = 600.0) -> tuple[int, str, str]:
    """Run an ffmpeg argv list and capture stdout/stderr (decoded)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise RuntimeError(f"ffmpeg timed out after {timeout:.0f}s") from exc
    return (
        proc.returncode or 0,
        out.decode(errors="ignore"),
        err.decode(errors="ignore"),
    )


def normalize_clip_filter(
    *,
    width: int,
    height: int,
    fps: int,
    sar_target: str = "1:1",
) -> str:
    """Scale + pad to ``width x height`` and force fps / sample aspect ratio.

    This is what we apply to each input clip before xfade so the chain
    sees uniform-sized frames.
    """
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar={sar_target},"
        f"fps={fps},"
        f"format=yuv420p"
    )


def output_path_for(
    storage_root: str | Path,
    project_id: int | str,
    *,
    preset: str = "social_9x16",
    suffix: str = "mp4",
) -> Path:
    root = Path(storage_root) / "mix" / str(project_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{preset}.{suffix}"


__all__ = [
    "EncodePreset",
    "PRESETS",
    "list_presets",
    "get_preset",
    "has_videotoolbox",
    "video_codec_args",
    "audio_codec_args",
    "run_ffmpeg",
    "normalize_clip_filter",
    "output_path_for",
]
