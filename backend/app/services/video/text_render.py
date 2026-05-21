"""Pillow-based text rendering fallback.

Used when the installed ffmpeg lacks ``drawtext`` / ``libass``. We rasterise
each subtitle cue (or cover title) to a transparent PNG, then overlay it via
ffmpeg's ``overlay`` filter — which is universally available.

Two outputs:
    * :func:`render_subtitle_track` — one PNG per cue + a manifest JSON
      describing start/end timestamps. The pipeline turns those into N image
      inputs + overlay/enable expressions.
    * :func:`render_cover_text` — single PNG used as a title overlay on the
      cover frame.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.services.video.subtitle import Cue


@dataclass(slots=True)
class RenderedCue:
    start: float
    end: float
    png_path: Path
    width: int
    height: int


@dataclass(slots=True)
class SubtitleRender:
    cues: list[RenderedCue]
    manifest_path: Path


def _load_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Try a few candidate paths; fall back to default bitmap font."""
    candidates: list[str] = []
    if font_name:
        candidates.extend(
            [
                font_name,
                f"/System/Library/Fonts/{font_name}.ttc",
                f"/System/Library/Fonts/{font_name}.ttf",
                f"/Library/Fonts/{font_name}.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return r, g, b, alpha
    if len(h) == 8:
        return (
            int(h[0:2], 16),
            int(h[2:4], 16),
            int(h[4:6], 16),
            int(h[6:8], 16),
        )
    return 255, 255, 255, alpha


def render_subtitle_png(
    text: str,
    *,
    video_width: int,
    video_height: int,
    font_name: str = "PingFang SC",
    font_size: int = 64,
    fill_hex: str = "#FFFFFF",
    outline_hex: str = "#0F2A4A",
    outline_width: int = 4,
    shadow_offset: int = 0,
    padding_x: int = 28,
    padding_y: int = 12,
    bg_alpha: int = 0,
    align: str = "center",
    max_lines: int = 2,
) -> Image.Image:
    """Render one subtitle cue to a transparent PNG sized for ``video_width``."""
    font = _load_font(font_name, font_size)
    lines = text.split("\n")[:max_lines]

    # measure
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    line_metrics: list[tuple[str, int, int]] = []  # text, w, h
    max_w = 0
    total_h = 0
    line_gap = max(2, font_size // 6)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_metrics.append((line, w, h))
        max_w = max(max_w, w)
        total_h += h + line_gap
    if total_h:
        total_h -= line_gap

    canvas_w = min(video_width, max_w + 2 * (padding_x + outline_width))
    canvas_h = total_h + 2 * (padding_y + outline_width)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_alpha:
        draw.rounded_rectangle(
            [(0, 0), (canvas_w - 1, canvas_h - 1)],
            radius=18,
            fill=_hex_to_rgba(outline_hex, bg_alpha),
        )

    fill = _hex_to_rgba(fill_hex, 255)
    outline = _hex_to_rgba(outline_hex, 220)
    y = padding_y + outline_width
    for line, w, h in line_metrics:
        if align == "center":
            x = (canvas_w - w) // 2
        elif align == "right":
            x = canvas_w - w - padding_x - outline_width
        else:
            x = padding_x + outline_width

        if shadow_offset:
            draw.text(
                (x + shadow_offset, y + shadow_offset),
                line,
                font=font,
                fill=(0, 0, 0, 180),
            )
        if outline_width:
            # stroke_width works on modern Pillow
            draw.text(
                (x, y),
                line,
                font=font,
                fill=fill,
                stroke_width=outline_width,
                stroke_fill=outline,
            )
        else:
            draw.text((x, y), line, font=font, fill=fill)
        y += h + line_gap

    return img


def render_subtitle_track(
    cues: Iterable[Cue],
    out_dir: str | Path,
    *,
    video_width: int,
    video_height: int,
    font_name: str = "PingFang SC",
    font_size: int = 64,
    fill_hex: str = "#FFFFFF",
    outline_hex: str = "#0F2A4A",
    outline_width: int = 4,
) -> SubtitleRender:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rendered: list[RenderedCue] = []
    for idx, cue in enumerate(cues):
        if not cue.text.strip():
            continue
        img = render_subtitle_png(
            cue.text,
            video_width=video_width,
            video_height=video_height,
            font_name=font_name,
            font_size=font_size,
            fill_hex=fill_hex,
            outline_hex=outline_hex,
            outline_width=outline_width,
        )
        png_path = out / f"cue_{idx:04d}.png"
        img.save(png_path, "PNG")
        rendered.append(
            RenderedCue(
                start=cue.start,
                end=cue.end,
                png_path=png_path,
                width=img.width,
                height=img.height,
            )
        )

    manifest = out / "subtitles.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "start": c.start,
                    "end": c.end,
                    "png": c.png_path.name,
                    "w": c.width,
                    "h": c.height,
                }
                for c in rendered
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return SubtitleRender(cues=rendered, manifest_path=manifest)


def render_cover_title(
    text: str,
    *,
    width: int,
    height: int,
    font_name: str = "PingFang SC",
    primary_hex: str = "#0F2A4A",
    accent_hex: str = "#22D3B7",
    text_hex: str = "#FFFFFF",
) -> Image.Image:
    """Build the title chip used by covers (Pillow path)."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # vertical gradient: top transparent → bottom primary with 80% alpha
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)
    primary_rgb = _hex_to_rgba(primary_hex, 0)[:3]
    for y in range(height):
        share = y / max(1, height - 1)
        a = int(share ** 1.6 * 210)
        g_draw.line([(0, y), (width, y)], fill=(*primary_rgb, a))
    img.alpha_composite(gradient)

    accent = _hex_to_rgba(accent_hex, 230)
    bar_h = max(4, height // 240)
    draw.rectangle(
        [(int(width * 0.08), int(height * 0.78))
         , (int(width * 0.08) + int(width * 0.16), int(height * 0.78) + bar_h)],
        fill=accent,
    )

    font_size = max(24, int(height * 0.06))
    font = _load_font(font_name, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (width - tw) // 2
    ty = int(height * 0.82)
    text_rgba = _hex_to_rgba(text_hex, 255)
    draw.text(
        (tx, ty),
        text,
        font=font,
        fill=text_rgba,
        stroke_width=2,
        stroke_fill=_hex_to_rgba(primary_hex, 200),
    )
    return img


def save_overlay_png(image: Image.Image, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    image.save(p, "PNG")
    return p


__all__ = [
    "RenderedCue",
    "SubtitleRender",
    "render_subtitle_png",
    "render_subtitle_track",
    "render_cover_title",
    "save_overlay_png",
]
