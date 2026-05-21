"""Clip variable-speed support — setpts (video) + atempo (audio) chains.

ffmpeg's ``atempo`` is bounded to [0.5, 100]. For slower-than-0.5×, we chain
multiple atempos. For faster-than-2× we do the same.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SpeedSpec:
    factor: float = 1.0  # >1 = faster (shorter), <1 = slower (longer)
    audio: bool = True
    keep_pitch: bool = True  # use atempo (keeps pitch) vs asetrate

    def clamp(self) -> "SpeedSpec":
        return SpeedSpec(
            factor=max(0.1, min(8.0, self.factor)),
            audio=self.audio,
            keep_pitch=self.keep_pitch,
        )


def setpts_expr(factor: float) -> str:
    """Video time-stretch: setpts=PTS / factor (factor=2 → half-length)."""
    if factor == 1.0:
        return ""
    return f"setpts=PTS/{factor:.4f}"


def atempo_chain(factor: float) -> str:
    """Build a chain of atempo filters that multiplies to ``factor``."""
    if factor == 1.0:
        return ""
    chain: list[str] = []
    remaining = factor
    while remaining > 2.0:
        chain.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        chain.append("atempo=0.5")
        remaining /= 0.5
    if abs(remaining - 1.0) > 1e-6:
        chain.append(f"atempo={remaining:.4f}")
    return ",".join(chain)


def apply_to_clip(
    *,
    video_label: str,
    audio_label: str,
    spec: SpeedSpec,
    out_v: str = "[vs]",
    out_a: str = "[as]",
) -> tuple[str, str]:
    """Return (video_chain, audio_chain) for one clip's speed application."""
    spec = spec.clamp()
    v_expr = setpts_expr(spec.factor)
    a_chain = atempo_chain(spec.factor) if spec.audio else ""
    v_full = f"{video_label}{v_expr}{out_v}" if v_expr else f"{video_label}copy{out_v}"
    a_full = (
        f"{audio_label}{a_chain}{out_a}"
        if a_chain
        else f"{audio_label}anull{out_a}"
    )
    return v_full, a_full


__all__ = ["SpeedSpec", "setpts_expr", "atempo_chain", "apply_to_clip"]
