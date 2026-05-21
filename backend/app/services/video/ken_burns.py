"""Ken Burns — slow zoom/pan on static images and low-motion clips.

Returns the filter fragment to apply to one input. The ``zoompan`` filter is
finicky:
    - It emits frames at its own rate (``-fps`` arg or ``framerate=`` filter
      option). We set ``fps=preset.fps`` and ``d=`` (duration in frames).
    - To pan smoothly, ``x``/``y`` are expressions of the *frame number* ``on``.

Modes:
    - ``in``        — zoom from 1.0 → 1.18 over the clip
    - ``out``       — zoom from 1.18 → 1.0
    - ``pan_left``  — slight zoom-in + drift left
    - ``pan_right`` — slight zoom-in + drift right
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class KenBurnsMode(str, Enum):
    IN = "in"
    OUT = "out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"


@dataclass(slots=True)
class KenBurnsSpec:
    mode: KenBurnsMode = KenBurnsMode.IN
    zoom_start: float = 1.0
    zoom_end: float = 1.18
    # Source must be at least target size; zoompan operates in source coords.


def build_ken_burns(
    *,
    duration: float,
    fps: int,
    width: int,
    height: int,
    spec: KenBurnsSpec | None = None,
) -> str:
    """Return the filter chain (no input/output labels)."""
    spec = spec or KenBurnsSpec()
    frames = max(2, int(round(duration * fps)))

    if spec.mode == KenBurnsMode.IN:
        zoom = f"min(zoom+{(spec.zoom_end - spec.zoom_start) / frames:.6f},{spec.zoom_end})"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif spec.mode == KenBurnsMode.OUT:
        zoom = f"if(eq(on,0),{spec.zoom_end},max(zoom-{(spec.zoom_end - spec.zoom_start) / frames:.6f},{spec.zoom_start}))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif spec.mode == KenBurnsMode.PAN_LEFT:
        zoom = f"min(zoom+{(spec.zoom_end - spec.zoom_start) / frames:.6f},{spec.zoom_end})"
        x = f"iw-(iw/zoom)-(on/{frames})*(iw*0.06)"
        y = "ih/2-(ih/zoom/2)"
    else:  # pan_right
        zoom = f"min(zoom+{(spec.zoom_end - spec.zoom_start) / frames:.6f},{spec.zoom_end})"
        x = f"(on/{frames})*(iw*0.06)"
        y = "ih/2-(ih/zoom/2)"

    # zoompan needs a fresh keyframe baseline — feed it via ``framerate=`` and
    # set ``d=`` to the *total* output frames per input frame (= ``frames``
    # since we have a single still or freeze frame).
    return (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"setsar=1,"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps}"
    )


def auto_mode(clip_index: int) -> KenBurnsMode:
    """Cheap heuristic alternation when the caller doesn't pick one."""
    return [
        KenBurnsMode.IN,
        KenBurnsMode.PAN_RIGHT,
        KenBurnsMode.OUT,
        KenBurnsMode.PAN_LEFT,
    ][clip_index % 4]


__all__ = ["KenBurnsMode", "KenBurnsSpec", "build_ken_burns", "auto_mode"]
