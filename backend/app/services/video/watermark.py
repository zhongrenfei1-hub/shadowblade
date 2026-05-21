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
    # Optional time gating — when set, the watermark only shows in this range.
    # Use ``(0, head_seconds)`` for opener-only branding,
    # ``(duration - tail_seconds, duration)`` for closer-only.
    visible_from: float | None = None
    visible_to: float | None = None
    # Pulse: when > 0, watermark blinks with this period (seconds full cycle)
    pulse_period: float = 0.0
    pulse_min_alpha: float = 0.35


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
    visible_from = 0.0 if spec.visible_from is None else max(0.0, spec.visible_from)
    visible_to = duration if spec.visible_to is None else min(duration, spec.visible_to)
    fade_out_start = max(0.0, visible_to - spec.fade_out)
    # Opacity expression — pulse if requested, otherwise constant.
    if spec.pulse_period > 0:
        # 0..1 triangular wave, scaled between pulse_min_alpha .. opacity
        alpha_expr = (
            f"{spec.pulse_min_alpha:.3f}+"
            f"({spec.opacity - spec.pulse_min_alpha:.3f})*"
            f"(0.5+0.5*sin(2*PI*t/{spec.pulse_period:.3f}))"
        )
    else:
        alpha_expr = f"{spec.opacity:.3f}"

    # Use scale2ref so we don't need to know the main frame size up-front.
    # ``enable=`` restricts the watermark to the visible window. fade=alpha
    # smoothly ramps into / out of view.
    scale_ref = (
        f"{logo_label}format=rgba[wm_op];"
        f"[wm_op]{video_label}scale2ref=w='oh*mdar':h='ih*{spec.width_pct:.3f}'[wm_scaled][vbase];"
        f"[wm_scaled]fade=t=in:st={visible_from:.3f}:d={spec.fade_in:.2f}:alpha=1,"
        f"fade=t=out:st={fade_out_start:.3f}:d={spec.fade_out:.2f}:alpha=1,"
        f"colorchannelmixer=aa='{alpha_expr}'[wm_ready];"
        f"[vbase][wm_ready]overlay=x='{x}':y='{y}':"
        f"enable='between(t,{visible_from:.3f},{visible_to:.3f})':"
        f"format=auto{out_label}"
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
