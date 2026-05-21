"""Brand watermark — safe-area logo overlay.

Position is expressed in the social-media safe zone (5% margin on each edge of
the canvas). Opacity defaults to 0.78 — visible but not distracting. The
output is a filter_complex fragment, not an executed command.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WatermarkPosition(str, Enum):
    TOP_LEFT = "tl"
    TOP_RIGHT = "tr"
    BOTTOM_LEFT = "bl"
    BOTTOM_RIGHT = "br"
    BOTTOM_CENTER = "bc"


@dataclass(slots=True)
class WatermarkSpec:
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    opacity: float = 0.78
    margin_pct: float = 0.05  # safe-area margin
    width_pct: float = 0.16  # logo width as % of video width
    fade_in: float = 0.4
    fade_out: float = 0.4


def _coords(pos: WatermarkPosition) -> tuple[str, str]:
    """Return (x, y) expressions for the overlay filter."""
    m = "main_w*0.05"
    my = "main_h*0.05"
    if pos == WatermarkPosition.TOP_LEFT:
        return m, my
    if pos == WatermarkPosition.TOP_RIGHT:
        return f"main_w-overlay_w-{m}", my
    if pos == WatermarkPosition.BOTTOM_LEFT:
        return m, f"main_h-overlay_h-{my}"
    if pos == WatermarkPosition.BOTTOM_CENTER:
        return "(main_w-overlay_w)/2", f"main_h-overlay_h-{my}"
    return f"main_w-overlay_w-{m}", f"main_h-overlay_h-{my}"


def build_watermark_chain(
    *,
    video_label: str,
    logo_label: str,
    duration: float,
    spec: WatermarkSpec | None = None,
    out_label: str = "[vmark]",
) -> str:
    """Filter graph fragment that overlays a logo onto the main video."""
    spec = spec or WatermarkSpec()
    x, y = _coords(spec.position)
    fade_out_start = max(0.0, duration - spec.fade_out)
    # Prepare logo: scale by % of main width, apply opacity + edge fades.
    logo_chain = (
        f"{logo_label}format=rgba,"
        f"scale=w='main_w*{spec.width_pct:.3f}':h=-2:force_original_aspect_ratio=decrease,"
        f"format=rgba,"
        f"colorchannelmixer=aa={spec.opacity:.2f},"
        f"fade=t=in:st=0:d={spec.fade_in:.2f}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d={spec.fade_out:.2f}:alpha=1"
        f"[wm_prep];"
    )
    # Note: scale=w=main_w*X needs the main video for reference frame size,
    # but ffmpeg's scale filter can't read main_w. We compute the absolute
    # pixel width when calling — keep this version simple by using overlay's
    # scale2ref alternative below.
    logo_chain = (
        f"{logo_label}format=rgba,"
        f"colorchannelmixer=aa={spec.opacity:.2f},"
        f"fade=t=in:st=0:d={spec.fade_in:.2f}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d={spec.fade_out:.2f}:alpha=1"
        f"[wm_pre];"
        f"[wm_pre]{video_label.replace(']', '_ref]') if False else ''}"
    )
    # Use scale2ref so we don't need to know the main frame size up-front
    scale_ref = (
        f"{logo_label}format=rgba,"
        f"colorchannelmixer=aa={spec.opacity:.2f}[wm_op];"
        f"[wm_op]{video_label}scale2ref=w='oh*mdar':h='ih*{spec.width_pct:.3f}'[wm_scaled][vbase];"
        f"[wm_scaled]fade=t=in:st=0:d={spec.fade_in:.2f}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d={spec.fade_out:.2f}:alpha=1[wm_ready];"
        f"[vbase][wm_ready]overlay=x='{x}':y='{y}':format=auto{out_label}"
    )
    return scale_ref


def build_text_watermark(
    *,
    video_label: str,
    text: str,
    font_file: str | None = None,
    duration: float,
    spec: WatermarkSpec | None = None,
    color: str = "white@0.78",
    out_label: str = "[vmark]",
) -> str:
    """Text-only watermark fallback (e.g. handle / hashtag)."""
    spec = spec or WatermarkSpec()
    x, y = _coords(spec.position)
    fade_out_start = max(0.0, duration - spec.fade_out)
    font_arg = f":fontfile={font_file}" if font_file else ""
    safe_text = text.replace(":", r"\:").replace("'", r"\'")
    return (
        f"{video_label}drawtext=text='{safe_text}'{font_arg}:"
        f"fontcolor={color}:fontsize=h*0.024:"
        f"x={x}:y={y}:"
        f"alpha='if(lt(t,{spec.fade_in:.2f}),t/{spec.fade_in:.2f},"
        f"if(gt(t,{fade_out_start:.2f}),"
        f"max(0,1-(t-{fade_out_start:.2f})/{spec.fade_out:.2f}),1))'"
        f"{out_label}"
    )


__all__ = [
    "WatermarkPosition",
    "WatermarkSpec",
    "build_watermark_chain",
    "build_text_watermark",
]
