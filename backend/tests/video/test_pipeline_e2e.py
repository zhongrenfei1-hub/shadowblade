"""End-to-end mix pipeline test.

Builds a 3-clip mix with voice + BGM + subtitles + watermark, encoded at
preview 360 resolution, and verifies the output MP4 is valid and roughly the
expected duration.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.video.brand import BrandKit
from app.services.video.pipeline import ClipSpec, MixPipeline, MixRequest
from app.services.video.probe import probe
from app.services.video.subtitle import Cue


@pytest.mark.asyncio
async def test_full_mix_pipeline_produces_mp4(
    tmp_path,
    synth_clip_a,
    synth_clip_b,
    synth_clip_c,
    synth_voice,
    synth_bgm,
    synth_logo,
):
    req = MixRequest(
        project_id="e2e-1",
        clips=[
            ClipSpec(
                path=str(synth_clip_a),
                end=2.5,
                brightness=0.5,
                motion=0.3,
                is_hero=True,
            ),
            ClipSpec(
                path=str(synth_clip_b),
                end=2.0,
                brightness=0.85,
                motion=0.65,
            ),
            ClipSpec(
                path=str(synth_clip_c),
                end=1.6,
                brightness=0.15,
                motion=0.4,
                is_chapter_break=True,
            ),
        ],
        voice_path=str(synth_voice),
        bgm_path=str(synth_bgm),
        cues=[
            Cue(0.2, 1.8, "新一代智能腕环来了"),
            Cue(2.4, 4.0, "续航三十天"),
            Cue(4.2, 5.8, "全场景健康监测"),
        ],
        watermark_path=str(synth_logo),
        watermark_position="br",
        brand_kit=BrandKit(
            name="Test",
            primary_color="#0F2A4A",
            accent_color="#22D3B7",
            secondary_color="#F5F7FB",
            font_body="Helvetica",
            subtitle_size=72,
        ),
        preset="preview_360_9x16",
        transition_style="editorial",
        max_transition=0.45,
        target_lufs=-16.0,
        title="新一代智能腕环",
        storage_root=str(tmp_path),
    )

    result = await MixPipeline().run(req)

    assert result.output_path.exists()
    assert result.output_path.stat().st_size > 5_000  # not empty
    assert result.duration == pytest.approx(2.5 + 2.0 + 1.6, abs=1.0)
    assert len(result.transitions) == 2
    # Verify the produced video is playable
    info = await probe(result.output_path)
    assert info.has_video
    assert info.has_audio
    assert info.duration > 3.0
    assert info.duration < 8.0
    # Cover should be a JPEG
    if result.cover_path:
        assert result.cover_path.exists()
        assert result.cover_path.stat().st_size > 1_000

    print(f"\nE2E output: {result.output_path}")
    print(f"E2E cover: {result.cover_path}")
    print(f"E2E runtime: {result.runtime_seconds}s")
    print(f"E2E transitions: {result.transitions}")


@pytest.mark.asyncio
async def test_mix_pipeline_without_audio_inputs(
    tmp_path, synth_clip_a, synth_clip_b
):
    """Pipeline must still work without voice/BGM (uses acrossfade timeline)."""
    req = MixRequest(
        project_id="e2e-noaudio",
        clips=[
            ClipSpec(path=str(synth_clip_a), end=2.0),
            ClipSpec(path=str(synth_clip_b), end=1.5),
        ],
        preset="preview_360_16x9",
        storage_root=str(tmp_path),
    )
    result = await MixPipeline().run(req)
    info = await probe(result.output_path)
    assert info.has_video
    assert info.duration == pytest.approx(2.0 + 1.5 - 0.3, abs=0.8)


@pytest.mark.asyncio
async def test_mix_pipeline_calm_style_uses_only_fades(tmp_path, synth_clip_a, synth_clip_b):
    req = MixRequest(
        project_id="e2e-calm",
        clips=[
            ClipSpec(path=str(synth_clip_a), end=2.0, brightness=0.05),
            ClipSpec(path=str(synth_clip_b), end=2.0, brightness=0.95),
        ],
        transition_style="calm",
        preset="preview_360_16x9",
        storage_root=str(tmp_path),
    )
    result = await MixPipeline().run(req)
    assert result.transitions == ["fade"]
