"""Pacing — detect silences and turn an audio track into shot cuts.

We don't actually re-encode here. The pacing module returns a *plan*:
    - silence ranges
    - speech segments (the inverse)
    - suggested cut points where the editor should swap b-roll
    - shot durations rounded to a friendly beat

The pipeline can choose to honour the plan or override it (e.g. when the user
locks specific clip durations from the storyboard).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from app.services.video.probe import FFMPEG

_SILENCE_RE = re.compile(
    r"silence_(?P<kind>start|end): (?P<t>-?\d+(?:\.\d+)?)(?:\s+\|\s+silence_duration:\s+(?P<d>-?\d+(?:\.\d+)?))?"
)


@dataclass(slots=True)
class SilenceRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(slots=True)
class SpeechSegment:
    start: float
    end: float
    chars: int = 0

    @property
    def duration(self) -> float:
        return max(0.001, self.end - self.start)

    @property
    def cps(self) -> float:
        return self.chars / self.duration if self.duration else 0.0


@dataclass(slots=True)
class PacingPlan:
    silences: list[SilenceRange]
    speech: list[SpeechSegment]
    cut_points: list[float]
    shot_durations: list[float]
    style: str = "editorial"


async def detect_silences(
    audio_path: str,
    *,
    noise_db: float = -28.0,
    min_silence: float = 0.35,
) -> list[SilenceRange]:
    """Run ``silencedetect`` and parse the stderr report.

    ``min_silence`` is the minimum gap that counts as a pause. We default to
    0.35s — short enough to catch breath pauses, long enough to ignore plosive
    artifacts.
    """
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-i",
        str(audio_path),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_silence:.3f}",
        "-f",
        "null",
        "-",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _out, err = await proc.communicate()
    text = err.decode(errors="ignore")
    ranges: list[SilenceRange] = []
    start: float | None = None
    for m in _SILENCE_RE.finditer(text):
        if m.group("kind") == "start":
            start = float(m.group("t"))
        else:
            end = float(m.group("t"))
            if start is None:
                continue
            ranges.append(SilenceRange(max(0.0, start), max(0.0, end)))
            start = None
    return ranges


def speech_from_silences(
    silences: list[SilenceRange], total_duration: float
) -> list[SpeechSegment]:
    """Invert silences into speech segments, clamped to [0, total]."""
    segments: list[SpeechSegment] = []
    cursor = 0.0
    for s in sorted(silences, key=lambda r: r.start):
        if s.start > cursor + 0.05:
            segments.append(SpeechSegment(cursor, s.start))
        cursor = max(cursor, s.end)
    if cursor < total_duration - 0.05:
        segments.append(SpeechSegment(cursor, total_duration))
    return segments


def plan_cuts(
    speech: list[SpeechSegment],
    *,
    target_shot: float = 3.5,
    min_shot: float = 1.4,
    max_shot: float = 6.0,
    snap_beats: list[float] | None = None,
) -> PacingPlan:
    """Plan cuts at natural pauses, keeping shots between min/max.

    - Walks the speech segments and cuts when accumulated duration crosses
      ``target_shot`` AND a pause exists between segments.
    - Snaps to BGM beats when ``snap_beats`` is provided (used by the music-
      driven pacing mode).
    """
    cuts: list[float] = [0.0]
    acc = 0.0
    last = 0.0
    for seg in speech:
        seg_dur = seg.duration
        # If the running shot is already long and we have a pause boundary,
        # snap here.
        if acc + seg_dur > target_shot and acc >= min_shot:
            cut = seg.start
            if snap_beats:
                cut = _snap(cut, snap_beats)
            if cut - last >= min_shot:
                cuts.append(cut)
                last = cut
                acc = 0.0
        acc += seg_dur

    # Final cut at the end of the last speech segment
    if speech:
        end = speech[-1].end
        if end - last >= min_shot:
            cuts.append(end)
        else:
            cuts[-1] = end

    # Convert into durations; when a shot exceeds max_shot, split evenly so
    # each fragment stays above min_shot.
    import math

    durations: list[float] = []
    refined_cuts: list[float] = [cuts[0]]
    for i in range(1, len(cuts)):
        gap = cuts[i] - refined_cuts[-1]
        if gap <= max_shot:
            refined_cuts.append(cuts[i])
            durations.append(gap)
            continue
        pieces = max(2, math.ceil(gap / max_shot))
        piece_dur = gap / pieces
        for _ in range(pieces - 1):
            refined_cuts.append(refined_cuts[-1] + piece_dur)
            durations.append(piece_dur)
        refined_cuts.append(cuts[i])
        durations.append(gap - piece_dur * (pieces - 1))

    return PacingPlan(
        silences=[],
        speech=speech,
        cut_points=refined_cuts,
        shot_durations=durations,
    )


def _snap(t: float, beats: list[float], tolerance: float = 0.25) -> float:
    """Snap a cut point to the nearest beat if within tolerance."""
    if not beats:
        return t
    nearest = min(beats, key=lambda b: abs(b - t))
    return nearest if abs(nearest - t) <= tolerance else t


async def plan_from_audio(
    audio_path: str,
    *,
    target_shot: float = 3.5,
    min_shot: float = 1.4,
    max_shot: float = 6.0,
    noise_db: float = -28.0,
    min_silence: float = 0.35,
) -> PacingPlan:
    """Convenience: probe → silences → speech → plan."""
    from app.services.video.probe import probe

    info = await probe(audio_path)
    silences = await detect_silences(
        audio_path, noise_db=noise_db, min_silence=min_silence
    )
    speech = speech_from_silences(silences, info.duration)
    plan = plan_cuts(
        speech, target_shot=target_shot, min_shot=min_shot, max_shot=max_shot
    )
    plan.silences = silences
    return plan


async def trim_silence_bounds(
    audio_path: str,
    *,
    noise_db: float = -38.0,
    min_silence: float = 0.25,
) -> tuple[float, float]:
    """Find leading + trailing silence to trim from a voice track.

    Returns ``(trim_start, trim_end)`` — seconds to remove from the head and
    tail respectively. Always non-negative and bounded by the file length.
    """
    from app.services.video.probe import probe

    info = await probe(audio_path)
    silences = await detect_silences(
        audio_path, noise_db=noise_db, min_silence=min_silence
    )
    if not silences:
        return 0.0, 0.0
    trim_start = 0.0
    trim_end = 0.0
    leading = silences[0]
    if leading.start <= 0.05:
        trim_start = max(0.0, leading.end - 0.05)
    trailing = silences[-1]
    if trailing.end >= info.duration - 0.1:
        trim_end = max(0.0, info.duration - trailing.start - 0.05)
    return trim_start, trim_end


__all__ = [
    "SilenceRange",
    "SpeechSegment",
    "PacingPlan",
    "detect_silences",
    "speech_from_silences",
    "plan_cuts",
    "plan_from_audio",
    "trim_silence_bounds",
]
