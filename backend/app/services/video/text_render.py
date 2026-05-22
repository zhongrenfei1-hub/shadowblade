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
    highlight_color: str | None = None,
    highlight_bold: bool = False,
    highlight_underline: bool = False,
) -> Image.Image:
    """Render one subtitle cue to a transparent PNG sized for ``video_width``.

    ``[关键词]`` markers in ``text`` are recoloured to ``highlight_color`` and
    optionally rendered with a heavier stroke (``highlight_bold``) and an
    underline (``highlight_underline``). When ``highlight_color`` is None
    the markers are stripped but no colour change is applied.
    """
    from app.services.video.highlight import HighlightSegment, parse_markers

    font = _load_font(font_name, font_size)
    raw_lines = text.split("\n")[:max_lines]

    # Parse markers per line so segmentation respects newlines.
    line_segments: list[list[HighlightSegment]] = [
        parse_markers(line) if highlight_color else [HighlightSegment(line, False)]
        for line in raw_lines
    ]

    # measure
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    line_metrics: list[tuple[list[tuple[HighlightSegment, int]], int, int]] = []
    max_w = 0
    total_h = 0
    line_gap = max(2, font_size // 6)
    for segs in line_segments:
        seg_widths: list[tuple[HighlightSegment, int]] = []
        total_w = 0
        h_line = 0
        for seg in segs:
            if not seg.text:
                continue
            bbox = draw.textbbox((0, 0), seg.text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            seg_widths.append((seg, w))
            total_w += w
            h_line = max(h_line, h)
        if h_line == 0:
            # Fall back to a measurement on an empty line for layout sanity.
            bbox = draw.textbbox((0, 0), " ", font=font)
            h_line = bbox[3] - bbox[1]
        line_metrics.append((seg_widths, total_w, h_line))
        max_w = max(max_w, total_w)
        total_h += h_line + line_gap
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

    fill_rgba = _hex_to_rgba(fill_hex, 255)
    outline_rgba = _hex_to_rgba(outline_hex, 220)
    hl_rgba = _hex_to_rgba(highlight_color, 255) if highlight_color else fill_rgba
    underline_gap = max(2, font_size // 14)
    underline_h = max(2, font_size // 18)

    y = padding_y + outline_width
    for segs, line_w, line_h in line_metrics:
        if align == "center":
            x = (canvas_w - line_w) // 2
        elif align == "right":
            x = canvas_w - line_w - padding_x - outline_width
        else:
            x = padding_x + outline_width

        for seg, seg_w in segs:
            seg_fill = hl_rgba if seg.is_highlight else fill_rgba
            seg_stroke = outline_width
            if seg.is_highlight and highlight_bold:
                seg_stroke = max(outline_width, outline_width + 2)
            if shadow_offset:
                draw.text(
                    (x + shadow_offset, y + shadow_offset),
                    seg.text,
                    font=font,
                    fill=(0, 0, 0, 180),
                )
            if seg_stroke:
                draw.text(
                    (x, y),
                    seg.text,
                    font=font,
                    fill=seg_fill,
                    stroke_width=seg_stroke,
                    stroke_fill=outline_rgba,
                )
            else:
                draw.text((x, y), seg.text, font=font, fill=seg_fill)
            if seg.is_highlight and highlight_underline and seg_w > 0:
                u_y = y + line_h + underline_gap
                draw.rectangle(
                    [(x, u_y), (x + seg_w, u_y + underline_h)],
                    fill=hl_rgba,
                )
            x += seg_w
        y += line_h + line_gap

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
    highlight_color: str | None = None,
    highlight_bold: bool = False,
    highlight_underline: bool = False,
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
            highlight_color=highlight_color,
            highlight_bold=highlight_bold,
            highlight_underline=highlight_underline,
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
    title_position: str = "bottom-center",
) -> Image.Image:
    """Build the title chip used by covers (Pillow path).

    ``title_position`` mirrors :func:`covers._title_xy` keywords:
    ``bottom-center`` | ``center`` | ``left-center`` | ``right-center`` |
    ``top-left``. The accent bar tracks the title's leading edge.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Vertical gradient — darken the title side for legibility.
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)
    primary_rgb = _hex_to_rgba(primary_hex, 0)[:3]
    top_heavy = title_position == "top-left"
    for y in range(height):
        share = y / max(1, height - 1)
        if top_heavy:
            share = 1.0 - share
        a = int(share ** 1.6 * 210)
        g_draw.line([(0, y), (width, y)], fill=(*primary_rgb, a))
    img.alpha_composite(gradient)

    # Compute title coords first; the accent bar follows.
    font_size = max(24, int(height * 0.06))
    font = _load_font(font_name, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pos = (title_position or "bottom-center").lower()
    if pos == "center":
        tx = (width - tw) // 2
        ty = (height - th) // 2
    elif pos == "left-center":
        tx = int(width * 0.07)
        ty = (height - th) // 2
    elif pos == "right-center":
        tx = width - tw - int(width * 0.07)
        ty = (height - th) // 2
    elif pos == "top-left":
        tx = int(width * 0.07)
        ty = int(height * 0.10)
    else:  # bottom-center default
        tx = (width - tw) // 2
        ty = int(height * 0.82)

    # Accent bar — short underline above the title, aligned to its leading edge.
    accent = _hex_to_rgba(accent_hex, 230)
    bar_h = max(4, height // 240)
    bar_w = min(int(width * 0.16), max(80, tw // 3))
    bar_x0 = tx
    if pos == "right-center":
        bar_x0 = tx + tw - bar_w
    bar_y0 = max(0, ty - int(height * 0.04))
    draw.rectangle(
        [(bar_x0, bar_y0), (bar_x0 + bar_w, bar_y0 + bar_h)],
        fill=accent,
    )

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
