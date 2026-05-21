"""Colour grading — LUT application + built-in look presets.

Two paths:
    1. ``apply_lut(path_to_cube)`` — uses ffmpeg's ``lut3d`` filter.
    2. ``apply_preset(name)`` — built-in looks compiled from curves and
       channel mixers (no external LUT files needed).

Built-in looks:
    - ``natural``    no-op (default)
    - ``warm``       +temperature, lift orange in mids, slight crush
    - ``cool``       cold cyan shadows, neutral mids, lift highlights
    - ``cinematic``  teal-orange split toning, contrast boost
    - ``punchy``     +saturation, +contrast, mild S-curve
    - ``mono``       desaturate + slight green tint
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

LookName = Literal[
    "natural", "warm", "cool", "cinematic", "punchy", "mono", "vintage"
]


PRESETS: dict[str, str] = {
    "natural": "null",
    "warm": (
        "eq=contrast=1.05:brightness=0.02:saturation=1.08,"
        "colorbalance=rs=0.06:gs=0.02:bs=-0.04:rm=0.04:bm=-0.02"
    ),
    "cool": (
        "eq=contrast=1.05:saturation=0.95,"
        "colorbalance=rs=-0.05:bs=0.07:bh=0.04"
    ),
    "cinematic": (
        "eq=contrast=1.18:saturation=1.05:gamma=0.96,"
        "colorbalance=rs=0.05:bs=0.05:rh=-0.04:bh=0.06"
    ),
    "punchy": (
        "eq=contrast=1.22:saturation=1.18:brightness=0.02,"
        "curves=master='0/0 0.25/0.18 0.5/0.55 0.75/0.85 1/1'"
    ),
    "mono": "hue=s=0,eq=contrast=1.08",
    "vintage": (
        "eq=contrast=0.96:saturation=0.78,"
        "colorbalance=rs=0.08:gs=-0.02:bs=-0.05:rm=0.04:bm=-0.04,"
        "noise=alls=2:allf=t"
    ),
}


def apply_preset(name: LookName | str) -> str:
    """Return the filter chain for a named look; empty if natural."""
    if name not in PRESETS:
        return ""
    chain = PRESETS[name]
    return "" if chain == "null" else chain


def apply_lut(cube_path: str | Path, *, interp: str = "tetrahedral") -> str:
    """Return the lut3d filter for a .cube LUT file."""
    p = Path(cube_path)
    if not p.exists():
        raise FileNotFoundError(f"LUT not found: {p}")
    # Escape any colons in the path for filtergraph syntax
    safe = str(p).replace(":", r"\:")
    return f"lut3d=file='{safe}':interp={interp}"


def auto_white_balance(strength: float = 0.5) -> str:
    """Cheap auto white balance via the ``colorbalance`` filter average."""
    strength = max(0.0, min(1.0, strength))
    return f"colorlevels=rimin={0.015 * strength:.4f}:gimin={0.015 * strength:.4f}:bimin={0.015 * strength:.4f}"


def compose_color_chain(
    *,
    preset: LookName | str | None = None,
    lut_path: str | Path | None = None,
    auto_wb: bool = False,
) -> str:
    """Combine the requested colour stages, in editorial order."""
    parts: list[str] = []
    if auto_wb:
        parts.append(auto_white_balance())
    if preset:
        chain = apply_preset(preset)
        if chain:
            parts.append(chain)
    if lut_path:
        parts.append(apply_lut(lut_path))
    return ",".join(parts)


__all__ = [
    "PRESETS",
    "apply_preset",
    "apply_lut",
    "auto_white_balance",
    "compose_color_chain",
]
