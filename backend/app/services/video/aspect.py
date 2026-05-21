"""Multi-aspect rendering — letterbox + smart center-crop variants.

Given a source aspect, produce filter fragments for each requested target
aspect. The crop mode picks the saliency centre — we approximate it as the
horizontal/vertical centre by default, but support a manual ``saliency``
override (0..1, 0=top/left, 1=bottom/right).

Strategies:
    - ``pad``   keep entire frame, letterbox/pillarbox with a brand colour.
    - ``crop``  scale to fill, crop to centre.
    - ``blur_bg`` scale to fill height/width, blur the cropped-out area for
      background, then place the un-cropped frame centred — Instagram style.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AspectName = Literal["9:16", "16:9", "1:1", "4:5"]


@dataclass(slots=True)
class AspectSpec:
    name: AspectName
    width: int
    height: int

    @property
    def ratio(self) -> float:
        return self.width / self.height


ASPECT_PRESETS: dict[str, AspectSpec] = {
    "9:16": AspectSpec("9:16", 1080, 1920),
    "16:9": AspectSpec("16:9", 1920, 1080),
    "1:1": AspectSpec("1:1", 1080, 1080),
    "4:5": AspectSpec("4:5", 1080, 1350),
}


def get_aspect(name: str) -> AspectSpec:
    if name not in ASPECT_PRESETS:
        raise KeyError(f"unknown aspect: {name}")
    return ASPECT_PRESETS[name]


def reframe_filter(
    *,
    target: AspectSpec,
    mode: Literal["pad", "crop", "blur_bg"] = "crop",
    saliency_x: float = 0.5,
    saliency_y: float = 0.5,
    pad_color: str = "0x0F2A4A",
) -> str:
    """Filter fragment that takes one video stream and emits the reframed one.

    All modes ensure the output is exactly ``target.width x target.height``.
    """
    saliency_x = max(0.0, min(1.0, saliency_x))
    saliency_y = max(0.0, min(1.0, saliency_y))
    if mode == "pad":
        return (
            f"scale={target.width}:{target.height}:force_original_aspect_ratio=decrease,"
            f"pad={target.width}:{target.height}:"
            f"(ow-iw)/2:(oh-ih)/2:color={pad_color},"
            f"setsar=1"
        )
    if mode == "crop":
        crop_x = f"max(0,min(iw-{target.width},iw*{saliency_x:.3f}-{target.width // 2}))"
        crop_y = f"max(0,min(ih-{target.height},ih*{saliency_y:.3f}-{target.height // 2}))"
        return (
            f"scale={target.width}:{target.height}:force_original_aspect_ratio=increase,"
            f"crop={target.width}:{target.height}:{crop_x}:{crop_y},"
            f"setsar=1"
        )
    # blur_bg
    return (
        f"split[scaled][blur];"
        f"[scaled]scale={target.width}:{target.height}:"
        f"force_original_aspect_ratio=decrease[scaled_fit];"
        f"[blur]scale={target.width}:{target.height}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={target.width}:{target.height},"
        f"gblur=sigma=24[blur_bg];"
        f"[blur_bg][scaled_fit]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )


__all__ = ["AspectSpec", "AspectName", "ASPECT_PRESETS", "get_aspect", "reframe_filter"]
