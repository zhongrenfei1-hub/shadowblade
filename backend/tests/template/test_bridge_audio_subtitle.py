"""Bridge tests — template audio/subtitle fields must reach the pipeline.

Layers under test:

  template (JSON) → _brand_seed_from_template → BrandPayload
                  → _build_mix_request          → BrandKit
                  → MixPipeline._build_audio    → AudioBus
                  → filter_complex string the ffmpeg child process runs
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.mix_video import ClipPayload, MixVideoRequest, _build_mix_request
from app.main import app
from app.services.template import apply_template_to_request, load_template
from app.services.template.schema import (
    Template,
    TemplateAudio,
    TemplateSubtitle,
)
from app.services.video.audio import AudioBus, build_voice_bgm_mix
from app.services.video.brand import BrandKit

client = TestClient(app)


def _empty_body(**overrides) -> MixVideoRequest:
    base = {"project_id": 1, "clips": [{"path": "/tmp/a.mp4"}]}
    base.update(overrides)
    return MixVideoRequest.model_validate(base)


# ---------- brand seeding picks up new audio fields -------------------------


def test_seed_carries_audio_bus_fields():
    tmpl = Template(
        name="t",
        audio=TemplateAudio(
            target_lufs=-16.0,
            target_tp=-1.5,
            bgm_gain_db=-8.0,
            duck_threshold_db=-30.0,
            duck_ratio=10.0,
            fade_in=0.7,
            fade_out=1.3,
        ),
    )
    out = apply_template_to_request(tmpl, _empty_body())
    b = out.brand
    assert b is not None
    assert b.target_lufs == -16.0
    assert b.target_tp == -1.5
    assert b.bgm_gain_db == -8.0
    assert b.duck_threshold_db == -30.0
    assert b.duck_ratio == 10.0
    assert b.fade_in == 0.7
    assert b.fade_out == 1.3


def test_seed_translates_subtitle_colors_into_brand_colors():
    tmpl = Template(
        name="t",
        subtitle=TemplateSubtitle(fill_color="#F5F7FB", outline_color="#0F2A4A"),
    )
    out = apply_template_to_request(tmpl, _empty_body())
    b = out.brand
    assert b is not None
    # fill → secondary (because SubtitleStyle.primary derives from secondary_color)
    assert b.secondary_color == "#F5F7FB"
    # outline → primary (because SubtitleStyle.outline_color derives from primary_color)
    assert b.primary_color == "#0F2A4A"


def test_seed_palette_fills_when_subtitle_colors_absent():
    tmpl = Template.model_validate(
        {
            "name": "t",
            "extras": {
                "brand_palette": {
                    "primary": "#111111",
                    "secondary": "#EEEEEE",
                    "accent": "#22D3B7",
                }
            },
        }
    )
    out = apply_template_to_request(tmpl, _empty_body())
    b = out.brand
    assert b.primary_color == "#111111"
    assert b.secondary_color == "#EEEEEE"
    assert b.accent_color == "#22D3B7"


def test_explicit_subtitle_colors_beat_palette():
    tmpl = Template.model_validate(
        {
            "name": "t",
            "subtitle": {"fill_color": "#ABCDEF", "outline_color": "#123456"},
            "extras": {
                "brand_palette": {
                    "primary": "#111111",
                    "secondary": "#EEEEEE",
                }
            },
        }
    )
    out = apply_template_to_request(tmpl, _empty_body())
    b = out.brand
    assert b.primary_color == "#123456"  # subtitle.outline wins over palette.primary
    assert b.secondary_color == "#ABCDEF"  # subtitle.fill wins over palette.secondary


# ---------- BrandKit → AudioBus wiring through MixPipeline ------------------


def test_brand_kit_from_dict_round_trips_audio_fields():
    kit = BrandKit.from_dict(
        {
            "bgm_gain_db": -9.0,
            "duck_threshold_db": -32.0,
            "duck_ratio": 12.0,
            "fade_in": 0.8,
            "fade_out": 1.4,
            "voice_gain_db": 1.5,
        }
    )
    assert kit.bgm_gain_db == -9.0
    assert kit.duck_threshold_db == -32.0
    assert kit.duck_ratio == 12.0
    assert kit.fade_in == 0.8
    assert kit.fade_out == 1.4
    assert kit.voice_gain_db == 1.5


def test_audio_bus_filter_string_reflects_brand_values():
    """``build_voice_bgm_mix`` reads AudioBus directly — verify the values
    we set on the brand actually appear in the filter graph string.
    """
    bus = AudioBus(
        bgm_gain_db=-8.0,
        duck_threshold_db=-28.0,
        duck_ratio=8.0,
        fade_in=0.6,
        fade_out=1.2,
        target_lufs=-16.0,
        target_tp=-1.5,
    )
    fg = build_voice_bgm_mix(
        voice_label="[1:a]", bgm_label="[2:a]", duration=10.0, bus=bus, out_label="[aout]"
    )
    # Spot-check the knobs surfaced into ffmpeg's expression language.
    assert "-8.00dB" in fg or "-8.0dB" in fg  # bgm_gain
    assert "-28.0" in fg  # duck threshold somewhere
    assert "I=-16.0" in fg or "I=-16" in fg
    assert "TP=-1.5" in fg


# ---------- product-demo template — full path lands in AudioBus -------------


def test_product_demo_brand_kit_drives_real_audio_bus():
    """End-to-end at the build layer (no ffmpeg): load template, build the
    MixRequest, then construct the same AudioBus the pipeline would.
    """
    body = MixVideoRequest.model_validate(
        {
            "project_id": "pd-bridge",
            "template": "product-demo",
            "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
        }
    )
    req = _build_mix_request(body)

    kit = req.brand_kit
    # All product-demo audio knobs survived the template→brand→kit path
    assert kit.target_lufs == -16.0
    assert kit.target_tp == -1.5
    assert kit.bgm_gain_db == -8.0
    assert kit.duck_threshold_db == -28.0
    assert kit.duck_ratio == 8.0
    assert kit.fade_in == 0.6
    assert kit.fade_out == 1.2
    # And the subtitle colour fold:
    assert kit.secondary_color == "#F5F7FB"
    assert kit.primary_color == "#0F2A4A"

    # The AudioBus the pipeline constructs from this kit:
    bus = AudioBus(
        target_lufs=kit.target_lufs,
        target_tp=kit.target_tp,
        voice_gain_db=kit.voice_gain_db,
        bgm_gain_db=kit.bgm_gain_db,
        duck_threshold_db=kit.duck_threshold_db,
        duck_ratio=kit.duck_ratio,
        fade_in=kit.fade_in,
        fade_out=kit.fade_out,
    )
    assert bus.duck_threshold_db == -28.0
    assert bus.duck_ratio == 8.0
    assert bus.fade_out == 1.2


# ---------- end-to-end: ffmpeg command string carries the values ------------


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _make_clip(path: Path, color: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:d=3,format=yuv420p",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def _make_voice(path: Path, duration: float = 3.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", "aac", str(path),
        ],
        check=True, capture_output=True,
    )


def _make_bgm(path: Path, duration: float = 8.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
            "-c:a", "aac", str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_product_demo_with_voice_and_bgm_succeeds(tmp_path, monkeypatch):
    """Real render with voice + bgm + product-demo. Verifies the entire
    audio bridge end-to-end — including sidechain ducking + fades.
    """
    voice = tmp_path / "voice.aac"
    bgm = tmp_path / "bgm.aac"
    _make_voice(voice)
    _make_bgm(bgm)
    clips = []
    for name, color in (("a", "0x0F2A4A"), ("b", "0x22D3B7")):
        p = tmp_path / f"{name}.mp4"
        _make_clip(p, color)
        clips.append({"path": str(p)})
    clips[0]["is_hero"] = True

    # Intercept the ffmpeg command so we can assert on what shipped.
    captured = {}
    from app.services.video import pipeline as pipe_mod

    real_run = pipe_mod.run_ffmpeg

    async def spy_run(cmd, *a, **kw):
        captured["cmd"] = " ".join(cmd)
        return await real_run(cmd, *a, **kw)

    monkeypatch.setattr(pipe_mod, "run_ffmpeg", spy_run)

    payload = {
        "project_id": "pd-bridge-e2e",
        "template": "product-demo",
        "clips": clips,
        "voice_path": str(voice),
        "bgm_path": str(bgm),
        "title": "Bridge Check",
    }
    r = client.post("/api/v1/mix-video/preview", json=payload)
    assert r.status_code == 200, r.text

    cmd = captured.get("cmd", "")
    # Fields that adaptive_bgm_mix does NOT touch — must propagate verbatim
    assert "I=-16" in cmd  # target_lufs (loudnorm)
    assert "TP=-1.5" in cmd  # target_tp
    # fade_out=1.2 from product-demo (in afade)
    assert "d=1.20" in cmd or "d=1.2" in cmd
    # adaptive path kicked in (voice-loudness aware) — sidechain present
    assert "sidechaincompress" in cmd


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_explicit_non_adaptive_carries_bgm_gain_and_duck_params(tmp_path, monkeypatch):
    """When adaptive_bgm_mix is OFF, bgm_gain_db / duck_threshold / duck_ratio
    must appear directly in the filter graph — verifying the brand→AudioBus
    bridge fully (without the adaptive overlay).
    """
    voice = tmp_path / "voice.aac"
    bgm = tmp_path / "bgm.aac"
    _make_voice(voice)
    _make_bgm(bgm)
    clips = []
    for name, color in (("a", "0x0F2A4A"), ("b", "0x22D3B7")):
        p = tmp_path / f"{name}.mp4"
        _make_clip(p, color)
        clips.append({"path": str(p)})
    clips[0]["is_hero"] = True

    captured = {}
    from app.services.video import pipeline as pipe_mod

    real_run = pipe_mod.run_ffmpeg

    async def spy_run(cmd, *a, **kw):
        captured["cmd"] = " ".join(cmd)
        return await real_run(cmd, *a, **kw)

    monkeypatch.setattr(pipe_mod, "run_ffmpeg", spy_run)

    payload = {
        "project_id": "pd-no-adapt",
        "template": "product-demo",
        "clips": clips,
        "voice_path": str(voice),
        "bgm_path": str(bgm),
        "adaptive_bgm_mix": False,  # explicit override → bypass adapt_bus path
    }
    r = client.post("/api/v1/mix-video/preview", json=payload)
    assert r.status_code == 200, r.text

    cmd = captured.get("cmd", "")
    # Now product-demo's bgm_gain_db=-8 lands verbatim
    assert "volume=-8.00dB" in cmd
    # duck_threshold=-28, duck_ratio=8 land verbatim in sidechaincompress
    assert "threshold=-28.0dB" in cmd  # one decimal in this filter
    assert "ratio=8.0" in cmd
    # And the fades + loudnorm too
    assert "d=0.60" in cmd  # fade_in
    assert "d=1.20" in cmd  # fade_out
    assert "I=-16" in cmd
    assert "TP=-1.5" in cmd
