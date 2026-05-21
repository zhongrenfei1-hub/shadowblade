"""MixPipeline — orchestrates the full brief → MP4 flow.

Inputs (MixRequest):
    - clips: list of source paths with optional start/end trims and signals
    - voice: voice-over track (optional)
    - bgm:   background music track (optional)
    - cues:  subtitle cues (optional)
    - brand_kit: brand colours/font/loudness target
    - preset: encode preset name ("social_9x16", ...)
    - watermark: logo path + position (optional)

Pipeline:
    1. probe every input (cached)
    2. select transitions per cut from clip signals
    3. build filter_complex: trim → normalize each clip → xfade chain
    4. mix voice + BGM with sidechain ducking (or voice-only / silence)
    5. burn-in subtitles via ASS (preserves brand font, fade)
    6. overlay watermark (scale2ref + safe-area)
    7. encode via preset (videotoolbox if available)
    8. generate cover (first hero frame + gradient + title)

Returns a :class:`MixResult` with output paths, duration, and the filter
graph string for debugging.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from app.services.video.audio import AudioBus, build_voice_bgm_mix, build_voice_only
from app.services.video.brand import BrandKit, default_kit
from app.services.video.covers import CoverSpec, generate_cover
from app.services.video.encoder import (
    EncodePreset,
    audio_codec_args,
    get_preset,
    normalize_clip_filter,
    output_path_for,
    run_ffmpeg,
    video_codec_args,
)
from app.services.video.features import detect_features
from app.services.video.probe import FFMPEG, MediaInfo, probe
from app.services.video.subtitle import Cue, SubtitleStyle, segment_utterances, write_ass, write_srt
from app.services.video.text_render import RenderedCue, render_subtitle_track
from app.services.video.transitions import (
    ShotSignal,
    TransitionKind,
    TransitionPlan,
    build_xfade_chain,
    select_transition,
)
from app.services.video.watermark import (
    WatermarkPosition,
    WatermarkSpec,
    build_watermark_chain,
)

log = logging.getLogger("shadowblade.mix")


@dataclass(slots=True)
class ClipSpec:
    path: str
    start: float = 0.0
    end: float | None = None  # None = use full clip
    brightness: float = 0.5
    motion: float = 0.5
    is_chapter_break: bool = False
    is_hero: bool = False

    def trim_duration(self, info: MediaInfo) -> float:
        end = info.duration if self.end is None else min(self.end, info.duration)
        return max(0.1, end - self.start)


@dataclass(slots=True)
class MixRequest:
    project_id: int | str
    clips: list[ClipSpec]
    voice_path: str | None = None
    bgm_path: str | None = None
    cues: list[Cue] = field(default_factory=list)
    watermark_path: str | None = None
    watermark_text: str | None = None  # fallback if no logo file
    watermark_position: str = "br"
    brand_kit: BrandKit = field(default_factory=default_kit)
    preset: str = "social_9x16"
    transition_style: str = "editorial"  # editorial | energetic | calm
    max_transition: float = 0.55
    target_lufs: float | None = None
    title: str | None = None
    cover_timestamp: float | None = None
    storage_root: str = "./storage"
    extra_filters: str = ""  # appended right before output


@dataclass(slots=True)
class MixResult:
    project_id: int | str
    output_path: Path
    cover_path: Path | None
    duration: float
    preset: str
    used_hardware: bool
    transitions: list[str]
    filter_graph: str
    ffmpeg_command: str
    runtime_seconds: float
    warnings: list[str] = field(default_factory=list)


class MixPipeline:
    """Stateless orchestrator. Construct, then call :meth:`run`."""

    def __init__(self, *, ffmpeg_bin: str = FFMPEG):
        self.ffmpeg_bin = ffmpeg_bin

    async def run(self, request: MixRequest) -> MixResult:
        started = time.monotonic()
        if not request.clips:
            raise ValueError("MixRequest.clips must not be empty")

        preset = get_preset(request.preset)
        kit = request.brand_kit
        features = detect_features()
        warnings: list[str] = []

        infos = await asyncio.gather(*(probe(c.path) for c in request.clips))
        for clip, info in zip(request.clips, infos):
            if not info.has_video:
                raise ValueError(f"clip has no video stream: {clip.path}")

        durations = [c.trim_duration(info) for c, info in zip(request.clips, infos)]
        plans = self._plan_transitions(request.clips, durations, request.max_transition,
                                       request.transition_style)
        total_duration = durations[0] + sum(
            d - p.duration for d, p in zip(durations[1:], plans)
        )

        # ---- Subtitles ---------------------------------------------------
        ass_path: Path | None = None
        png_cues: list[RenderedCue] = []
        sub_dir = Path(request.storage_root) / "mix" / str(request.project_id)
        if request.cues:
            segmented = segment_utterances(request.cues, max_chars=22, max_lines=2)
            style = kit.subtitle_style()
            style.size = self._scale_subtitle_size(preset, style.size)
            style.margin_v = self._scale_subtitle_margin(preset, style.margin_v)
            # Always write SRT + ASS sidecars
            sub_dir.mkdir(parents=True, exist_ok=True)
            write_srt(segmented, sub_dir / f"subtitles_{request.preset}.srt")
            ass_path = sub_dir / f"subtitles_{request.preset}.ass"
            write_ass(
                segmented,
                ass_path,
                style=style,
                video_w=preset.width,
                video_h=preset.height,
            )
            if not features.can_burn_subtitles:
                # Pillow PNG fallback: render each cue once, overlay later
                render = render_subtitle_track(
                    segmented,
                    sub_dir / f"sub_pngs_{request.preset}",
                    video_width=preset.width,
                    video_height=preset.height,
                    font_name=kit.font_body,
                    font_size=self._scale_subtitle_size(preset, kit.subtitle_size),
                    fill_hex=kit.secondary_color,
                    outline_hex=kit.primary_color,
                )
                png_cues = render.cues
                if not png_cues:
                    warnings.append("subtitle PNG render produced no cues")
                else:
                    warnings.append(
                        "libass missing — using Pillow PNG subtitle overlay"
                    )

        # ---- Build ffmpeg command ----------------------------------------
        input_args: list[str] = []
        for clip in request.clips:
            input_args += ["-ss", f"{clip.start:.3f}"]
            if clip.end is not None:
                input_args += ["-to", f"{clip.end:.3f}"]
            input_args += ["-i", clip.path]
        clip_count = len(request.clips)

        voice_idx: int | None = None
        if request.voice_path:
            input_args += ["-i", request.voice_path]
            voice_idx = clip_count
        bgm_idx: int | None = None
        if request.bgm_path:
            # Loop BGM to cover the timeline
            input_args += [
                "-stream_loop",
                "-1",
                "-t",
                f"{total_duration:.3f}",
                "-i",
                request.bgm_path,
            ]
            bgm_idx = clip_count + (1 if voice_idx is not None else 0)
        wm_idx: int | None = None
        if request.watermark_path:
            input_args += ["-loop", "1", "-t", f"{total_duration:.3f}", "-i", request.watermark_path]
            wm_idx = clip_count + (1 if voice_idx is not None else 0) + (
                1 if bgm_idx is not None else 0
            )

        # Subtitle PNG overlays — one input per cue, each looped to cover the
        # cue duration. Each gets an overlay+enable filter later.
        sub_png_indices: list[tuple[int, RenderedCue]] = []
        if png_cues:
            base_idx = (
                clip_count
                + (1 if voice_idx is not None else 0)
                + (1 if bgm_idx is not None else 0)
                + (1 if wm_idx is not None else 0)
            )
            for i, cue in enumerate(png_cues):
                duration_cue = max(0.05, cue.end - cue.start)
                input_args += [
                    "-loop",
                    "1",
                    "-t",
                    f"{duration_cue:.3f}",
                    "-i",
                    str(cue.png_path),
                ]
                sub_png_indices.append((base_idx + i, cue))

        norm_filter = normalize_clip_filter(
            width=preset.width, height=preset.height, fps=preset.fps
        )
        # If we have an external voice or BGM track, the clip audio is unused.
        # In that case skip building per-clip audio prep + the audio crossfade
        # to avoid dangling filter outputs.
        use_source_audio = voice_idx is None and bgm_idx is None
        graph_parts: list[str] = []
        for i in range(clip_count):
            graph_parts.append(f"[{i}:v]{norm_filter}[v{i}]")
            if use_source_audio:
                graph_parts.append(
                    f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]"
                )

        xfade_chain, final_v, final_a = build_xfade_chain(
            durations,
            plans,
            audio_crossfade=use_source_audio,
        )
        if xfade_chain:
            graph_parts.append(xfade_chain)
        if not use_source_audio:
            # No source-audio timeline label exists — drop it
            final_a = ""

        # subtitles — burn-in (libass) or Pillow PNG overlay fallback
        last_v = final_v
        if ass_path and features.can_burn_subtitles:
            graph_parts.append(
                f"{last_v}subtitles={shlex.quote(str(ass_path))}:original_size={preset.width}x{preset.height}[vsub]"
            )
            last_v = "[vsub]"
        elif sub_png_indices:
            # Place each PNG centered horizontally near the safe-area bottom
            margin_v = int(preset.height * 0.07)
            for ovl_idx, (input_idx, cue) in enumerate(sub_png_indices):
                next_label = f"[vsub{ovl_idx}]"
                graph_parts.append(
                    f"{last_v}[{input_idx}:v]overlay="
                    f"x='(main_w-overlay_w)/2':"
                    f"y='main_h-overlay_h-{margin_v}':"
                    f"enable='between(t,{cue.start:.3f},{cue.end:.3f})':"
                    f"format=auto:eof_action=pass{next_label}"
                )
                last_v = next_label

        # watermark
        if wm_idx is not None:
            wm_spec = WatermarkSpec(
                position=WatermarkPosition(request.watermark_position),
                opacity=kit.watermark_opacity,
                width_pct=kit.watermark_width_pct,
            )
            wm_chain = build_watermark_chain(
                video_label=last_v,
                logo_label=f"[{wm_idx}:v]",
                duration=total_duration,
                spec=wm_spec,
                out_label="[vmark]",
            )
            graph_parts.append(wm_chain)
            last_v = "[vmark]"

        # final pixel format
        graph_parts.append(f"{last_v}format=yuv420p[vout]")
        last_v = "[vout]"

        # Audio: pick the right mix path
        audio_out_label = self._build_audio(
            graph_parts=graph_parts,
            voice_idx=voice_idx,
            bgm_idx=bgm_idx,
            timeline_audio=final_a or "",
            duration=total_duration,
            kit=kit,
            target_lufs=request.target_lufs,
            warnings=warnings,
        )

        filter_graph = ";".join(graph_parts)

        out_path = output_path_for(request.storage_root, request.project_id, preset=request.preset)
        cmd = [
            self.ffmpeg_bin,
            "-hide_banner",
            "-y",
            *input_args,
            "-filter_complex",
            filter_graph,
            "-map",
            last_v,
            "-map",
            audio_out_label,
            *video_codec_args(preset),
            *audio_codec_args(preset),
            "-movflags",
            "+faststart",
            "-shortest",
            str(out_path),
        ]
        log.debug("ffmpeg cmd: %s", " ".join(shlex.quote(p) for p in cmd))
        rc, _stdout, stderr = await run_ffmpeg(cmd)
        if rc != 0:
            raise RuntimeError(
                f"ffmpeg encode failed (rc={rc}):\n{stderr[-2400:]}"
            )

        # Cover
        cover_path: Path | None = None
        try:
            hero_idx = next(
                (i for i, c in enumerate(request.clips) if c.is_hero), 0
            )
            hero_offset = sum(durations[:hero_idx])
            cover_path = await generate_cover(
                out_path,
                Path(request.storage_root)
                / "mix"
                / str(request.project_id)
                / "cover.jpg",
                timestamp=request.cover_timestamp
                if request.cover_timestamp is not None
                else min(total_duration - 0.4, hero_offset + 0.7),
                spec=CoverSpec(
                    width=preset.width,
                    height=preset.height,
                    primary=kit.primary_color,
                    accent=kit.accent_color,
                    title=request.title,
                ),
            )
        except RuntimeError as exc:
            warnings.append(f"cover generation failed: {exc}")

        return MixResult(
            project_id=request.project_id,
            output_path=out_path,
            cover_path=cover_path,
            duration=total_duration,
            preset=request.preset,
            used_hardware=any("h264_videotoolbox" in a for a in cmd),
            transitions=[p.kind.value for p in plans],
            filter_graph=filter_graph,
            ffmpeg_command=" ".join(shlex.quote(p) for p in cmd),
            runtime_seconds=round(time.monotonic() - started, 3),
            warnings=warnings,
        )

    # ---- helpers ---------------------------------------------------------
    def _plan_transitions(
        self,
        clips: list[ClipSpec],
        durations: list[float],
        max_duration: float,
        style: str,
    ) -> list[TransitionPlan]:
        plans: list[TransitionPlan] = []
        for i in range(len(clips) - 1):
            prev = ShotSignal(
                duration=durations[i],
                brightness=clips[i].brightness,
                motion=clips[i].motion,
                is_chapter_break=clips[i].is_chapter_break,
                is_hero=clips[i].is_hero,
            )
            nxt = ShotSignal(
                duration=durations[i + 1],
                brightness=clips[i + 1].brightness,
                motion=clips[i + 1].motion,
                is_chapter_break=clips[i + 1].is_chapter_break,
                is_hero=clips[i + 1].is_hero,
            )
            plans.append(
                select_transition(prev, nxt, max_duration=max_duration, style=style)
            )
        return plans

    def _scale_subtitle_size(self, preset: EncodePreset, base_size: int) -> int:
        """Scale subtitle size to the preset height (baseline = 1920p)."""
        return max(28, int(round(base_size * preset.height / 1920)))

    def _scale_subtitle_margin(self, preset: EncodePreset, base_margin: int) -> int:
        return max(24, int(round(base_margin * preset.height / 1920)))

    def _build_audio(
        self,
        *,
        graph_parts: list[str],
        voice_idx: int | None,
        bgm_idx: int | None,
        timeline_audio: str,
        duration: float,
        kit: BrandKit,
        target_lufs: float | None,
        warnings: list[str],
    ) -> str:
        """Wire audio inputs into the filter graph; return final audio label."""
        bus = AudioBus(
            target_lufs=target_lufs if target_lufs is not None else kit.target_lufs,
            target_tp=kit.target_tp,
        )
        if voice_idx is not None and bgm_idx is not None:
            graph_parts.append(
                build_voice_bgm_mix(
                    voice_label=f"[{voice_idx}:a]",
                    bgm_label=f"[{bgm_idx}:a]",
                    duration=duration,
                    bus=bus,
                    out_label="[aout]",
                )
            )
            return "[aout]"
        if voice_idx is not None:
            graph_parts.append(
                build_voice_only(voice_label=f"[{voice_idx}:a]", bus=bus, out_label="[aout]")
            )
            return "[aout]"
        if bgm_idx is not None:
            graph_parts.append(
                f"[{bgm_idx}:a]aresample=48000,volume={bus.bgm_gain_db:.2f}dB,"
                f"afade=t=in:st=0:d={bus.fade_in:.2f},"
                f"afade=t=out:st={max(0.0, duration - bus.fade_out):.2f}:d={bus.fade_out:.2f},"
                f"loudnorm=I={bus.target_lufs}:TP={bus.target_tp}:LRA=11[aout]"
            )
            return "[aout]"
        # Fall back to the source-audio timeline (acrossfaded already)
        if timeline_audio:
            return timeline_audio
        # No audio anywhere — generate a silent track to satisfy aac muxing
        graph_parts.append(
            f"anullsrc=channel_layout=stereo:sample_rate={bus.sample_rate}:d={duration:.3f}[asilent]"
        )
        return "[asilent]"


__all__ = ["ClipSpec", "MixRequest", "MixResult", "MixPipeline"]
