"""Cover (thumbnail) generation.

Strategy:
    1. Pick the most "interesting" keyframe via ffmpeg ``thumbnail`` filter.
    2. Scale-and-pad to the target aspect.
    3. Apply a brand gradient overlay (vertical, primary → accent).
    4. Optional title text in the safe area.

Returns a JPEG by default — small, web-friendly, plays well in CDNs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.services.video.features import detect_features
from app.services.video.probe import FFMPEG
from app.services.video.text_render import render_cover_title


@dataclass(slots=True)
class CoverSpec:
    width: int = 1080
    height: int = 1920
    primary: str = "#0F2A4A"
    accent: str = "#22D3B7"
    gradient_alpha: float = 0.42
    title: str | None = None
    font: str | None = None
    quality: int = 4  # 2..6, lower is better for mjpeg


async def generate_cover(
    source_video: str | Path,
    out_path: str | Path,
    *,
    timestamp: float | None = None,
    spec: CoverSpec | None = None,
) -> Path:
    """Generate a brand cover from a source video.

    If ``timestamp`` is None we use the ``thumbnail`` filter — picks the most
    representative frame from the first 100 frames.
    """
    spec = spec or CoverSpec()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    primary = _hex_to_ffcolor(spec.primary)
    accent = _hex_to_ffcolor(spec.accent)

    features = detect_features()

    filter_parts: list[str] = []
    if timestamp is None:
        filter_parts.append("thumbnail=100")
    filter_parts.append(
        f"scale={spec.width}:{spec.height}:force_original_aspect_ratio=increase"
    )
    filter_parts.append(f"crop={spec.width}:{spec.height}")
    filter_parts.append("format=rgba")
    filter_parts.append(
        f"drawbox=x=0:y=0:w=iw:h=ih:color={accent}@{spec.gradient_alpha * 0.4:.2f}:t=fill"
    )
    inputs: list[str] = ["-i", str(source_video)]
    title_overlay_path: Path | None = None

    if spec.title:
        if features.has_drawtext:
            font_arg = f":fontfile={spec.font}" if spec.font else ""
            safe_title = spec.title.replace(":", r"\:").replace("'", r"\'")
            filter_parts.append(
                f"drawtext=text='{safe_title}'{font_arg}:fontcolor=white:"
                f"fontsize=h*0.06:x=(w-text_w)/2:y=h-th-h*0.12:"
                f"box=1:boxcolor={primary}@0.55:boxborderw=24"
            )
        else:
            # Pillow fallback: render title to PNG, overlay it
            title_img = render_cover_title(
                spec.title,
                width=spec.width,
                height=spec.height,
                font_name=spec.font or "PingFang SC",
                primary_hex=spec.primary,
                accent_hex=spec.accent,
            )
            title_overlay_path = out.with_suffix(".title.png")
            title_img.save(title_overlay_path, "PNG")
            inputs += ["-i", str(title_overlay_path)]

    filter_parts.append("format=yuvj420p")
    base_vf = ",".join(filter_parts)

    if title_overlay_path is not None:
        vf_complex = f"[0:v]{base_vf}[base];[base][1:v]overlay=0:0:format=auto,format=yuvj420p[vout]"
        filter_args = ["-filter_complex", vf_complex, "-map", "[vout]"]
    else:
        filter_args = ["-vf", base_vf]

    cmd = [FFMPEG, "-hide_banner", "-nostats", "-y"]
    if timestamp is not None:
        cmd += ["-ss", f"{max(0.0, timestamp):.3f}"]
    cmd += inputs
    cmd += [
        "-frames:v",
        "1",
        *filter_args,
        "-q:v",
        str(spec.quality),
        str(out),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"cover generation failed: {stderr.decode(errors='ignore')[-400:]}"
        )
    if title_overlay_path is not None and title_overlay_path.exists():
        try:
            title_overlay_path.unlink()
        except OSError:
            pass
    return out


def _hex_to_ffcolor(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    if len(h) not in (6, 8):
        return "0x000000"
    return f"0x{h.upper()}"


__all__ = ["CoverSpec", "generate_cover"]
