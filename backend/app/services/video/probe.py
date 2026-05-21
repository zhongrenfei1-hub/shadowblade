"""ffprobe wrapper — async media inspection.

Exposes :class:`MediaInfo` with the metadata the rest of the pipeline needs:
duration, fps, sample rate, loudness (BS.1770 integrated LUFS), keyframes.
"""

from __future__ import annotations

import asyncio
import json
import shlex
from dataclasses import dataclass, field
from pathlib import Path

FFPROBE = "ffprobe"
FFMPEG = "ffmpeg"


@dataclass(slots=True)
class MediaInfo:
    path: Path
    duration: float
    has_video: bool
    has_audio: bool
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    audio_codec: str = ""
    sample_rate: int = 0
    channels: int = 0
    bit_rate: int = 0
    keyframes: list[float] = field(default_factory=list)
    loudness_i: float | None = None  # integrated LUFS
    loudness_tp: float | None = None  # true peak
    loudness_lra: float | None = None  # loudness range

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 0.0

    @property
    def is_portrait(self) -> bool:
        return self.height > self.width if self.width else False


async def _run(cmd: list[str]) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out, err


async def probe(path: str | Path, *, with_loudness: bool = False) -> MediaInfo:
    """Read media metadata. Optional BS.1770 loudness pass costs ~1× duration."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"media not found: {p}")
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(p),
    ]
    code, out, err = await _run(cmd)
    if code != 0:
        raise RuntimeError(f"ffprobe failed: {err.decode(errors='ignore')}")
    data = json.loads(out)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0.0))
    bit_rate = int(fmt.get("bit_rate", 0) or 0)
    info = MediaInfo(
        path=p, duration=duration, has_video=False, has_audio=False, bit_rate=bit_rate
    )
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            info.has_video = True
            info.width = int(s.get("width", 0))
            info.height = int(s.get("height", 0))
            info.video_codec = s.get("codec_name", "")
            r = s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1"
            try:
                num, den = r.split("/")
                info.fps = round(float(num) / float(den), 3) if float(den) else 0.0
            except ValueError:
                info.fps = 0.0
        elif s.get("codec_type") == "audio":
            info.has_audio = True
            info.audio_codec = s.get("codec_name", "")
            info.sample_rate = int(s.get("sample_rate", 0) or 0)
            info.channels = int(s.get("channels", 0) or 0)
    if with_loudness and info.has_audio:
        try:
            (
                info.loudness_i,
                info.loudness_tp,
                info.loudness_lra,
            ) = await measure_loudness(p)
        except RuntimeError:
            pass
    return info


async def measure_loudness(path: str | Path) -> tuple[float, float, float]:
    """BS.1770 integrated loudness, true peak, loudness range (LUFS / dBTP / LU)."""
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "loudnorm=print_format=json",
        "-f",
        "null",
        "-",
    ]
    code, _out, err = await _run(cmd)
    if code != 0:
        raise RuntimeError(f"loudnorm pass failed: {err.decode(errors='ignore')[-200:]}")
    text = err.decode(errors="ignore")
    start = text.rfind("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError("loudnorm json not found")
    payload = json.loads(text[start : end + 1])
    return (
        float(payload.get("input_i", -23.0)),
        float(payload.get("input_tp", -2.0)),
        float(payload.get("input_lra", 7.0)),
    )


async def detect_keyframes(path: str | Path, *, max_count: int = 64) -> list[float]:
    """Return up to ``max_count`` keyframe timestamps (seconds)."""
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-skip_frame",
        "nokey",
        "-show_entries",
        "frame=pts_time",
        "-of",
        "csv=p=0",
        str(path),
    ]
    code, out, _err = await _run(cmd)
    if code != 0:
        return []
    times: list[float] = []
    for line in out.decode(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            times.append(float(line))
        except ValueError:
            continue
        if len(times) >= max_count:
            break
    return times


def shell_quote(parts: list[str]) -> str:
    """Render an argv list as a shell-safe one-liner — handy for debug logs."""
    return " ".join(shlex.quote(p) for p in parts)
