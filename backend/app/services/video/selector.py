"""Smart material selector.

Given a script (cue list or total seconds), a candidate clip pool, and a
target shot length, decide how many clips to use and how long each shot
should be. Honours min/max shot bounds, prefers using hero clips first,
distributes chapter breaks evenly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class CandidateClip:
    path: str
    duration: float
    is_hero: bool = False
    is_chapter_break: bool = False
    brightness: float = 0.5
    motion: float = 0.5
    score: float = 0.0  # quality / relevance score; higher = picked first


@dataclass(slots=True)
class ShotChoice:
    clip: CandidateClip
    use_duration: float  # how much of the clip to use
    start: float = 0.0
    end: float | None = None  # None = start..start+use_duration


@dataclass(slots=True)
class SelectionPlan:
    shots: list[ShotChoice]
    total_duration: float
    used_hero_count: int
    used_chapter_break_count: int


def select_clips(
    candidates: list[CandidateClip],
    *,
    target_total: float,
    target_shot: float = 3.5,
    min_shot: float = 1.4,
    max_shot: float = 6.0,
    must_include_hero: bool = True,
) -> SelectionPlan:
    """Pick a sequence of clips matching ``target_total`` total length.

    Strategy:
        1. Sort by ``score`` desc (hero gets a +1 bias).
        2. Decide shot count = clamp(target/target_shot, ceil/floor) so we
           hit min/max bounds.
        3. Each shot gets ``target_total / shot_count`` seconds, clamped.
        4. If a candidate's duration < shot duration, use its full length and
           reduce shot duration accordingly.
        5. Ensure at least one hero clip is used when requested.
    """
    if not candidates:
        return SelectionPlan(shots=[], total_duration=0.0, used_hero_count=0,
                             used_chapter_break_count=0)
    if target_total <= 0:
        return SelectionPlan(shots=[], total_duration=0.0, used_hero_count=0,
                             used_chapter_break_count=0)

    # Compute desired shot count
    raw = target_total / target_shot
    shot_count = max(1, int(round(raw)))
    shot_count = max(math.ceil(target_total / max_shot), shot_count)
    shot_count = min(math.floor(target_total / min_shot) or 1, shot_count)
    shot_count = max(1, shot_count)
    shot_count = min(shot_count, len(candidates))

    # Rank: hero first, then by score
    ranked = sorted(
        candidates,
        key=lambda c: (1 if c.is_hero else 0, c.score, -abs(c.brightness - 0.5)),
        reverse=True,
    )
    picked: list[CandidateClip] = ranked[:shot_count]

    if must_include_hero and not any(c.is_hero for c in picked):
        hero = next((c for c in ranked if c.is_hero), None)
        if hero:
            picked[-1] = hero

    # Distribute durations
    shots: list[ShotChoice] = []
    remaining = target_total
    pending = list(picked)
    while pending:
        c = pending.pop(0)
        slots_left = len(pending) + 1
        ideal = remaining / slots_left
        use = min(c.duration, max(min_shot, min(max_shot, ideal)))
        shots.append(ShotChoice(clip=c, use_duration=round(use, 3), end=round(use, 3)))
        remaining -= use
        if remaining <= 0:
            break

    return SelectionPlan(
        shots=shots,
        total_duration=round(sum(s.use_duration for s in shots), 3),
        used_hero_count=sum(1 for s in shots if s.clip.is_hero),
        used_chapter_break_count=sum(1 for s in shots if s.clip.is_chapter_break),
    )


__all__ = ["CandidateClip", "ShotChoice", "SelectionPlan", "select_clips"]
