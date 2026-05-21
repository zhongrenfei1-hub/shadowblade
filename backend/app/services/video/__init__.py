"""ShadowBlade video mix engine.

Modules:
    probe       — ffprobe wrapper, media metadata (duration, fps, loudness)
    transitions — xfade-based smart transitions (fade/zoom/slide/whiteflash/blur)
    subtitle    — SRT/ASS generation with smart segmentation and brand styling
    audio       — voice + BGM mixing with sidechain ducking and LUFS normalisation
    pacing      — silencedetect-driven shot cutting and tempo planning
    watermark   — brand logo overlay with safe-area positioning
    covers      — keyframe extraction with brand gradient overlay
    brand       — brand kit loader (palette, font, voice tone)
    encoder     — encode presets (social 9:16, hero 16:9, square 1:1)
    pipeline    — MixPipeline: orchestrates the full brief → MP4 flow
"""

from app.services.video.pipeline import MixPipeline, MixRequest, MixResult

__all__ = ["MixPipeline", "MixRequest", "MixResult"]
