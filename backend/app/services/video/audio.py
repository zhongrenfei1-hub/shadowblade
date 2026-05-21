"""Professional audio mixing.

Capabilities:
    - voice + BGM mix with sidechain ducking (compress BGM when voice plays)
    - LUFS normalisation (target -14 LUFS by default, social platform default)
    - high-shelf de-mud + low-shelf warmth filters on the voice bus
    - looping BGM if it's shorter than the timeline; fade-in/out on edges
    - render to a stem (audio-only) or return a filter_complex fragment for
      pipeline composition.

All public functions are sync — they generate filter graphs / argv. The actual
ffmpeg execution lives in ``encoder.run_ffmpeg``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AudioBus:
    """Per-bus settings used by :func:`build_voice_bgm_mix`."""

    target_lufs: float = -14.0  # social-platform standard
    target_tp: float = -1.0
    voice_gain_db: float = 0.0
    bgm_gain_db: float = -14.0  # rough headroom before sidechain takes over
    duck_threshold_db: float = -28.0
    duck_ratio: float = 8.0
    duck_attack_ms: int = 10
    duck_release_ms: int = 320
    fade_in: float = 0.4
    fade_out: float = 0.6
    sample_rate: int = 48000
    channels: int = 2


def build_voice_bgm_mix(
    *,
    voice_label: str,
    bgm_label: str,
    duration: float,
    bus: AudioBus | None = None,
    out_label: str = "amix",
) -> str:
    """Return a filter_complex fragment that produces ``out_label``.

    Expects the caller to have labelled the voice and BGM streams already.
    Sidechain ducking uses ``sidechaincompress`` keyed on the voice bus —
    BGM gets squashed whenever the voice signal exceeds the threshold.
    """
    bus = bus or AudioBus()
    fade_in = max(0.0, bus.fade_in)
    fade_out = max(0.0, bus.fade_out)
    fade_out_start = max(0.0, duration - fade_out)

    voice_chain = (
        f"{voice_label}aresample={bus.sample_rate},"
        f"highpass=f=80,"
        f"lowshelf=f=180:g=1.5,"
        f"highshelf=f=8000:g=2,"
        f"acompressor=threshold=-18dB:ratio=2.5:attack=8:release=180,"
        f"volume={bus.voice_gain_db:.2f}dB"
        f"[voice_pre];"
        f"[voice_pre]asplit=2[voice_main][voice_key];"
    )
    bgm_chain = (
        f"{bgm_label}aresample={bus.sample_rate},"
        f"volume={bus.bgm_gain_db:.2f}dB,"
        f"afade=t=in:st=0:d={fade_in:.2f},"
        f"afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f}"
        f"[bgm_pre];"
    )
    duck = (
        f"[bgm_pre][voice_key]sidechaincompress="
        f"threshold={bus.duck_threshold_db}dB:"
        f"ratio={bus.duck_ratio}:"
        f"attack={bus.duck_attack_ms}:"
        f"release={bus.duck_release_ms}:"
        f"makeup=1[bgm_ducked];"
    )
    mix = (
        f"[voice_main][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=0:"
        f"weights='1 1'[mix_pre];"
    )
    loudnorm = (
        f"[mix_pre]loudnorm=I={bus.target_lufs}:TP={bus.target_tp}:LRA=11:"
        f"linear=true:print_format=summary"
        f"{out_label}"
    )
    return voice_chain + bgm_chain + duck + mix + loudnorm


def build_voice_only(
    *,
    voice_label: str,
    bus: AudioBus | None = None,
    out_label: str = "[anorm]",
) -> str:
    """Voice-only mix path (no BGM available)."""
    bus = bus or AudioBus()
    return (
        f"{voice_label}aresample={bus.sample_rate},"
        f"highpass=f=80,"
        f"lowshelf=f=180:g=1.5,"
        f"highshelf=f=8000:g=2,"
        f"acompressor=threshold=-18dB:ratio=2.5:attack=8:release=180,"
        f"volume={bus.voice_gain_db:.2f}dB,"
        f"loudnorm=I={bus.target_lufs}:TP={bus.target_tp}:LRA=11"
        f"{out_label}"
    )


def loop_input_args(path: str | Path, duration: float) -> list[str]:
    """Argv flags to loop a short audio file to cover ``duration`` seconds.

    Used as: ``ffmpeg -stream_loop -1 -t <dur> -i <bgm>``.
    """
    return ["-stream_loop", "-1", "-t", f"{max(0.1, duration):.3f}", "-i", str(path)]


def adapt_bus_to_voice_loudness(
    bus: AudioBus,
    voice_lufs: float,
    *,
    voice_target: float | None = None,
) -> AudioBus:
    """Tune the ducking threshold and BGM gain to the measured voice loudness.

    Heuristic:
        - threshold = voice_lufs + 6 dB (BGM compresses when voice is ≥ 6dB
          above its long-term average — i.e. on a syllable, not a breath).
        - bgm_gain  = -10 dB relative to the target voice loudness, so the
          BGM sits comfortably below the voice even before ducking kicks in.
        - ratio adapts: voice quieter than -22 LUFS gets a stronger duck.
    """
    target = voice_target if voice_target is not None else bus.target_lufs
    delta = target - voice_lufs
    threshold = voice_lufs + 6.0
    bgm_gain = max(-28.0, min(-6.0, target - 10.0))
    ratio = 4.0 if voice_lufs > -22 else 8.0
    return AudioBus(
        target_lufs=bus.target_lufs,
        target_tp=bus.target_tp,
        voice_gain_db=max(-6.0, min(12.0, delta)),
        bgm_gain_db=bgm_gain,
        duck_threshold_db=threshold,
        duck_ratio=ratio,
        duck_attack_ms=bus.duck_attack_ms,
        duck_release_ms=bus.duck_release_ms,
        fade_in=bus.fade_in,
        fade_out=bus.fade_out,
        sample_rate=bus.sample_rate,
        channels=bus.channels,
    )


__all__ = [
    "AudioBus",
    "build_voice_bgm_mix",
    "build_voice_only",
    "loop_input_args",
    "adapt_bus_to_voice_loudness",
]
