"""BGM beat detection — pure-Python tempo + onset estimator.

We avoid heavy DSP libraries (librosa, aubio) so the engine stays lean. The
algorithm:

    1. Decode audio to a low-rate mono float32 stream via ffmpeg.
    2. Compute frame-by-frame energy (RMS in ~10ms hops).
    3. Spectral-flux-style onset: take the positive change in energy,
       smooth by a small moving average, then peak-pick above a local
       median + delta threshold with a refractory period.
    4. Tempo (BPM): histogram inter-onset intervals around the most common
       value in [60..200] BPM, return the best mode.

Accuracy is "good enough for editorial cuts" — not concert-grade, but
sufficient for snapping shot cuts to a beat. The output is consumable by
:func:`pacing.plan_cuts` via its ``snap_beats`` argument.
"""

from __future__ import annotations

import asyncio
import struct
from dataclasses import dataclass

from app.services.video.probe import FFMPEG


@dataclass(slots=True)
class BeatGrid:
    bpm: float
    onsets: list[float]  # seconds
    duration: float

    @property
    def confidence(self) -> float:
        """0..1 — how strongly the BPM dominates the IOI histogram."""
        if not self.onsets or len(self.onsets) < 4:
            return 0.0
        return min(1.0, len(self.onsets) / max(8.0, self.duration / 0.5))


async def _decode_audio_pcm(
    audio_path: str,
    *,
    sample_rate: int = 11025,
) -> tuple[bytes, int]:
    """Pull mono PCM s16le at a low rate. Returns (raw_bytes, sample_rate)."""
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-i",
        str(audio_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "-",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"beat detector decode failed: {err.decode(errors='ignore')[-200:]}"
        )
    return out, sample_rate


def _rms_envelope(pcm: bytes, *, hop_samples: int) -> list[float]:
    """RMS energy per hop window."""
    if not pcm:
        return []
    samples = struct.unpack_from(f"<{len(pcm) // 2}h", pcm)
    envelope: list[float] = []
    for start in range(0, len(samples), hop_samples):
        chunk = samples[start : start + hop_samples]
        if not chunk:
            break
        # Mean-square / 32768^2 normalised; sqrt at end
        ms = sum(s * s for s in chunk) / len(chunk)
        envelope.append((ms ** 0.5) / 32768.0)
    return envelope


def _flux(envelope: list[float]) -> list[float]:
    out: list[float] = [0.0]
    for i in range(1, len(envelope)):
        out.append(max(0.0, envelope[i] - envelope[i - 1]))
    return out


def _moving_average(values: list[float], window: int) -> list[float]:
    if window <= 1 or not values:
        return values[:]
    out: list[float] = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= window:
            acc -= values[i - window]
        out.append(acc / min(window, i + 1))
    return out


def _peak_pick(
    flux: list[float],
    *,
    hop_seconds: float,
    refractory_seconds: float = 0.18,
    delta: float = 0.005,
    median_window: int = 24,
) -> list[float]:
    """Return onset times (seconds). Strict-greater left, ≥ on the right to
    survive plateaus introduced by smoothing."""
    if not flux:
        return []
    onsets: list[float] = []
    last_onset_idx = -10_000
    refractory = int(refractory_seconds / hop_seconds)
    half_w = max(1, median_window // 2)
    for i in range(1, len(flux) - 1):
        if flux[i] <= flux[i - 1] or flux[i] < flux[i + 1]:
            continue
        # Plateau: collapse to the first index, skip if not the leading edge
        if flux[i] == flux[i + 1] and i > 0 and flux[i] == flux[i - 1]:
            continue
        if i - last_onset_idx < refractory:
            continue
        lo = max(0, i - half_w)
        hi = min(len(flux), i + half_w + 1)
        window = flux[lo:hi]
        if not window:
            continue
        s = sorted(window)
        median = s[len(s) // 2]
        if flux[i] >= median + delta and flux[i] > 0:
            onsets.append(i * hop_seconds)
            last_onset_idx = i
    return onsets


def _estimate_bpm(onsets: list[float]) -> float:
    if len(onsets) < 4:
        return 0.0
    iois = [onsets[i] - onsets[i - 1] for i in range(1, len(onsets)) if onsets[i] > onsets[i - 1]]
    iois = [v for v in iois if 0.25 <= v <= 1.0]  # 60..240 BPM
    if not iois:
        return 0.0
    # Histogram 5 BPM bins
    histogram: dict[int, int] = {}
    for v in iois:
        bpm = 60.0 / v
        bucket = int(round(bpm / 4.0))  # 4-BPM resolution
        histogram[bucket] = histogram.get(bucket, 0) + 1
    best_bucket = max(histogram, key=lambda k: histogram[k])
    return float(best_bucket * 4)


async def detect_beats(
    audio_path: str,
    *,
    refractory_seconds: float = 0.18,
    delta: float = 0.014,
    hop_ms: int = 10,
) -> BeatGrid:
    """Pure-Python beat detection. Returns BPM + onset timestamps."""
    pcm, sr = await _decode_audio_pcm(audio_path)
    hop_samples = max(1, int(sr * hop_ms / 1000))
    envelope = _rms_envelope(pcm, hop_samples=hop_samples)
    flux = _flux(envelope)
    # No smoothing: flux from a 10ms RMS envelope is already band-limited
    # enough, and smoothing creates plateaus that defeat strict peak picking.
    hop_seconds = hop_samples / sr
    onsets = _peak_pick(
        flux,
        hop_seconds=hop_seconds,
        refractory_seconds=refractory_seconds,
        delta=delta,
    )
    bpm = _estimate_bpm(onsets)
    duration = len(envelope) * hop_seconds
    return BeatGrid(bpm=bpm, onsets=onsets, duration=duration)


def beat_grid_to_seconds(grid: BeatGrid, target_duration: float) -> list[float]:
    """Useful for tests: filter onsets to [0, target_duration]."""
    return [t for t in grid.onsets if 0.0 <= t <= target_duration]


__all__ = ["BeatGrid", "detect_beats", "beat_grid_to_seconds"]
