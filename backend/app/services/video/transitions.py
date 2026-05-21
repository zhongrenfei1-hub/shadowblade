"""Smart transitions — xfade-driven, content-aware.

xfade picks the visual; ``select_transition`` picks which xfade fits the cut
based on simple signals (cut energy, brightness delta, motion estimate). We
keep the catalogue small and *editorial* — slick cuts, no MTV-era wipes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class TransitionKind(str, Enum):
    """xfade-compatible transition names that survived editorial review."""

    FADE = "fade"  # neutral crossfade — safe default
    FADEBLACK = "fadeblack"  # chapter break — through black
    FADEWHITE = "fadewhite"  # bright reveal — product hero
    DISSOLVE = "dissolve"  # texture-driven, organic
    SMOOTHLEFT = "smoothleft"  # camera-pan left
    SMOOTHRIGHT = "smoothright"  # camera-pan right
    SMOOTHUP = "smoothup"  # rising reveal
    SMOOTHDOWN = "smoothdown"  # waterfall reveal
    CIRCLEOPEN = "circleopen"  # focus pull
    CIRCLECLOSE = "circleclose"  # focus retract
    RADIAL = "radial"  # clock wipe (sparingly)
    PIXELIZE = "pixelize"  # glitch — only for tech intros
    HBLUR = "hblur"  # motion blur cross


_LOUD_KINDS = {
    TransitionKind.FADEWHITE,
    TransitionKind.PIXELIZE,
    TransitionKind.RADIAL,
}


@dataclass(slots=True)
class TransitionPlan:
    kind: TransitionKind
    duration: float  # seconds — must be < min(clip_a_tail, clip_b_head)
    offset: float  # seconds into clip_a where the transition begins

    def to_xfade(self) -> str:
        """Render the xfade filter fragment used inside ``concat_with_xfade``."""
        return f"xfade=transition={self.kind.value}:duration={self.duration:.3f}:offset={self.offset:.3f}"


@dataclass(slots=True)
class ShotSignal:
    """Cheap per-cut signal used to bias transition selection."""

    duration: float
    brightness: float = 0.5  # 0..1 estimate from probe / thumbnail
    motion: float = 0.5  # 0..1 — high means whip-pans / fast cuts
    is_chapter_break: bool = False
    is_hero: bool = False  # use white flash + hold


def select_transition(
    prev: ShotSignal,
    nxt: ShotSignal,
    *,
    max_duration: float = 0.6,
    style: Literal["editorial", "energetic", "calm"] = "editorial",
) -> TransitionPlan:
    """Pick a transition that suits the cut.

    Heuristics:
        - chapter break → fadeblack
        - hero reveal   → fadewhite (short)
        - large brightness jump → dissolve (softens flicker)
        - high motion both sides → hblur (camera continuity)
        - mid-pace cut → fade
        - calm style overrides all but chapter/hero → fade
    """
    duration = min(max_duration, max(0.15, min(prev.duration, nxt.duration) * 0.25))

    if prev.is_chapter_break or nxt.is_chapter_break:
        return TransitionPlan(TransitionKind.FADEBLACK, duration, offset=0.0)
    if nxt.is_hero:
        return TransitionPlan(TransitionKind.FADEWHITE, min(duration, 0.35), offset=0.0)
    if style == "calm":
        return TransitionPlan(TransitionKind.FADE, duration, offset=0.0)

    bright_delta = abs(prev.brightness - nxt.brightness)
    motion = (prev.motion + nxt.motion) / 2

    if bright_delta > 0.45:
        kind = TransitionKind.DISSOLVE
    elif motion > 0.7 and style == "energetic":
        kind = TransitionKind.HBLUR
    elif motion > 0.55:
        # subtle camera-aware pan; alternate direction by signal hash
        kind = (
            TransitionKind.SMOOTHLEFT
            if (int(prev.duration * 100) & 1)
            else TransitionKind.SMOOTHRIGHT
        )
    else:
        kind = TransitionKind.FADE

    if style != "energetic" and kind in _LOUD_KINDS:
        kind = TransitionKind.FADE
    return TransitionPlan(kind, duration, offset=0.0)


def build_xfade_chain(
    durations: list[float],
    transitions: list[TransitionPlan],
    *,
    video_label_prefix: str = "v",
    audio_label_prefix: str = "a",
    audio_crossfade: bool = True,
) -> tuple[str, str, str]:
    """Build the xfade + acrossfade filter_complex chain.

    Returns ``(filter_graph, final_video_label, final_audio_label)``.
    Inputs must be label-named ``[v0][v1]...`` for video and ``[a0][a1]...``
    for audio — the pipeline relabels the inputs before calling this.
    """
    if len(durations) != len(transitions) + 1:
        raise ValueError("transitions count must be len(durations) - 1")
    if len(durations) == 1:
        return "", f"[{video_label_prefix}0]", f"[{audio_label_prefix}0]"

    video_parts: list[str] = []
    audio_parts: list[str] = []
    cumulative = durations[0]
    prev_v = f"[{video_label_prefix}0]"
    prev_a = f"[{audio_label_prefix}0]"
    for idx, plan in enumerate(transitions):
        offset = cumulative - plan.duration
        next_v_in = f"[{video_label_prefix}{idx + 1}]"
        next_a_in = f"[{audio_label_prefix}{idx + 1}]"
        v_out = f"[vx{idx}]"
        a_out = f"[ax{idx}]"
        video_parts.append(
            f"{prev_v}{next_v_in}xfade=transition={plan.kind.value}:"
            f"duration={plan.duration:.3f}:offset={offset:.3f}{v_out}"
        )
        if audio_crossfade:
            audio_parts.append(
                f"{prev_a}{next_a_in}acrossfade=d={plan.duration:.3f}:c1=tri:c2=tri{a_out}"
            )
        prev_v = v_out
        prev_a = a_out
        cumulative += durations[idx + 1] - plan.duration

    chain = ";".join(video_parts + audio_parts)
    return chain, prev_v, prev_a


__all__ = [
    "TransitionKind",
    "TransitionPlan",
    "ShotSignal",
    "select_transition",
    "build_xfade_chain",
]
