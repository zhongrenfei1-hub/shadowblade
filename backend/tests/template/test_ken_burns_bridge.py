"""Bridge tests — template.ken_burns must land in the ffmpeg filter graph.

Layers under test:

  template (JSON) → apply._REQUEST_FIELD_MAP → MixVideoRequest.ken_burns_*
                  → _build_mix_request                 → MixRequest.ken_burns_*
                  → MixPipeline._ken_burns_for_clip    → zoompan filter string
                  → filter_complex the ffmpeg child runs
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.mix_video import ClipPayload, MixVideoRequest
from app.main import app
from app.services.template import apply_template_to_request, load_template
from app.services.template.schema import Template, TemplateKenBurns
from app.services.video.ken_burns import KenBurnsMode
from app.services.video.pipeline import ClipSpec, MixPipeline, MixRequest
from app.services.video.brand import default_kit
from app.services.video.encoder import get_preset

client = TestClient(app)


def _body(**overrides) -> MixVideoRequest:
    base = {"project_id": 1, "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}]}
    base.update(overrides)
    return MixVideoRequest.model_validate(base)


# ---------- schema ----------------------------------------------------------


def test_schema_ken_burns_invalid_intensity_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateKenBurns.model_validate({"intensity": "extreme"})


def test_schema_ken_burns_invalid_direction_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateKenBurns.model_validate({"default_direction": "diagonal"})


def test_schema_ken_burns_max_zoom_bounded():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateKenBurns.model_validate({"max_zoom": 5.0})


# ---------- apply layer -----------------------------------------------------


def test_apply_folds_ken_burns_fields():
    tmpl = Template(
        name="t",
        ken_burns=TemplateKenBurns(
            enabled=True,
            intensity="medium",
            default_direction="pan_left",
            max_zoom=1.22,
            apply_to="low_motion",
        ),
    )
    out = apply_template_to_request(tmpl, _body())
    assert out.ken_burns_enabled is True
    assert out.ken_burns_intensity == "medium"
    assert out.ken_burns_direction == "pan_left"
    assert out.ken_burns_max_zoom == 1.22
    assert out.ken_burns_apply_to == "low_motion"


def test_apply_user_explicit_ken_burns_wins():
    tmpl = Template(
        name="t",
        ken_burns=TemplateKenBurns(
            enabled=True, intensity="strong", default_direction="in"
        ),
    )
    body = _body(ken_burns_enabled=False, ken_burns_intensity="subtle")
    out = apply_template_to_request(tmpl, body)
    assert out.ken_burns_enabled is False  # user disabled it
    assert out.ken_burns_intensity == "subtle"


# ---------- pipeline filter resolution --------------------------------------


def _mk_request(**knobs) -> MixRequest:
    return MixRequest(
        project_id="kb",
        clips=[
            ClipSpec(path="/tmp/a.mp4", motion=0.2),
            ClipSpec(path="/tmp/b.mp4", motion=0.8),
        ],
        brand_kit=default_kit(),
        **knobs,
    )


def test_pipeline_skips_ken_burns_when_disabled():
    pipe = MixPipeline()
    req = _mk_request(ken_burns_enabled=False)
    out = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=0, duration=3.0,
        request=req, preset=get_preset("hero_16x9"),
    )
    assert out is None


def test_pipeline_emits_zoompan_when_enabled_all():
    pipe = MixPipeline()
    req = _mk_request(
        ken_burns_enabled=True,
        ken_burns_intensity="subtle",
        ken_burns_direction="in",
        ken_burns_apply_to="all",
    )
    chain = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=0, duration=3.0,
        request=req, preset=get_preset("hero_16x9"),
    )
    assert chain is not None
    assert "zoompan" in chain
    # subtle → max_zoom 1.08 → zoom_end appears in the increment expression
    assert "1.08" in chain
    # hero_16x9 → 1920x1080 → zoompan s=1920x1080
    assert "s=1920x1080" in chain


def test_pipeline_intensity_maps_to_zoom():
    pipe = MixPipeline()
    preset = get_preset("hero_16x9")
    for intensity, expected_zoom in (
        ("subtle", "1.08"),
        ("medium", "1.18"),
        ("strong", "1.3"),
    ):
        req = _mk_request(
            ken_burns_enabled=True, ken_burns_intensity=intensity,
            ken_burns_direction="in", ken_burns_apply_to="all",
        )
        chain = pipe._ken_burns_for_clip(
            clip=req.clips[0], clip_index=0, duration=3.0,
            request=req, preset=preset,
        )
        assert chain is not None
        assert expected_zoom in chain, f"intensity {intensity}: expected {expected_zoom} in {chain[:200]}"


def test_pipeline_max_zoom_overrides_intensity():
    pipe = MixPipeline()
    req = _mk_request(
        ken_burns_enabled=True,
        ken_burns_intensity="subtle",  # would imply 1.08
        ken_burns_max_zoom=1.25,
        ken_burns_direction="in",
        ken_burns_apply_to="all",
    )
    chain = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=0, duration=3.0,
        request=req, preset=get_preset("hero_16x9"),
    )
    assert chain is not None
    assert "1.25" in chain


def test_pipeline_auto_direction_alternates_by_index():
    """auto_mode order: IN, PAN_RIGHT, OUT, PAN_LEFT — verify clip 0 and 2."""
    pipe = MixPipeline()
    preset = get_preset("hero_16x9")
    req = _mk_request(
        ken_burns_enabled=True,
        ken_burns_direction="auto",
        ken_burns_apply_to="all",
    )
    c0 = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=0, duration=3.0, request=req, preset=preset,
    )
    c1 = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=1, duration=3.0, request=req, preset=preset,
    )
    c2 = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=2, duration=3.0, request=req, preset=preset,
    )
    # index 0 → IN  →  x = "iw/2-(iw/zoom/2)" centered, no on-based drift
    assert "on/" not in c0  # IN/OUT are centered, no horizontal drift
    # index 1 → PAN_RIGHT  →  contains on-based drift to the right
    assert "on/" in c1 and "iw*0.06" in c1
    # index 2 → OUT  →  zoom expression starts at zoom_end (uses if(eq(on,0),..))
    assert "if(eq(on,0)" in c2


def test_pipeline_low_motion_skips_high_motion_clip():
    pipe = MixPipeline()
    preset = get_preset("hero_16x9")
    req = _mk_request(
        ken_burns_enabled=True,
        ken_burns_direction="in",
        ken_burns_apply_to="low_motion",
    )
    # clip[0].motion = 0.2 (low) → applied
    c0 = pipe._ken_burns_for_clip(
        clip=req.clips[0], clip_index=0, duration=3.0, request=req, preset=preset,
    )
    # clip[1].motion = 0.8 (high) → skipped
    c1 = pipe._ken_burns_for_clip(
        clip=req.clips[1], clip_index=1, duration=3.0, request=req, preset=preset,
    )
    assert c0 is not None
    assert c1 is None


# ---------- product-demo end-to-end through build_mix_request --------------


def test_product_demo_ken_burns_reaches_mix_request():
    body = MixVideoRequest.model_validate(
        {
            "project_id": "pd-kb",
            "template": "product-demo",
            "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
        }
    )
    from app.api.mix_video import _build_mix_request

    req = _build_mix_request(body)
    assert req.ken_burns_enabled is True
    assert req.ken_burns_intensity == "subtle"
    assert req.ken_burns_direction == "auto"
    assert req.ken_burns_max_zoom == 1.08
    assert req.ken_burns_apply_to == "low_motion"


# ---------- real ffmpeg render ---------------------------------------------


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _make_clip(path: Path, color: str, duration: float = 3.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:d={duration},format=yuv420p",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_product_demo_ken_burns_present_in_ffmpeg_command(tmp_path, monkeypatch):
    """product-demo + low-motion clips → ffmpeg command must contain zoompan."""
    clips = []
    for i, (name, color) in enumerate((("a", "0x0F2A4A"), ("b", "0x22D3B7"))):
        p = tmp_path / f"{name}.mp4"
        _make_clip(p, color)
        clips.append({"path": str(p), "motion": 0.15})  # low motion → eligible
    clips[0]["is_hero"] = True

    captured = {}
    from app.services.video import pipeline as pipe_mod

    real_run = pipe_mod.run_ffmpeg

    async def spy_run(cmd, *a, **kw):
        captured["cmd"] = " ".join(cmd)
        return await real_run(cmd, *a, **kw)

    monkeypatch.setattr(pipe_mod, "run_ffmpeg", spy_run)

    payload = {
        "project_id": "pd-kb-e2e",
        "template": "product-demo",
        "clips": clips,
        "title": "Ken Burns Demo",
    }
    r = client.post("/api/v1/mix-video/preview", json=payload)
    assert r.status_code == 200, r.text

    cmd = captured.get("cmd", "")
    # zoompan present
    assert "zoompan" in cmd
    # subtle intensity → zoom_end 1.08 surfaces in the zoom expression
    assert "1.08" in cmd
    # output ended up at preview_360_16x9 → 640x360
    assert "s=640x360" in cmd


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_product_demo_ken_burns_skips_high_motion_clip(tmp_path, monkeypatch):
    """A clip with motion ≥ 0.35 under apply_to=low_motion should NOT
    get its norm_filter replaced. The ffmpeg command should still
    contain normalize_clip_filter for the high-motion clip while keeping
    zoompan for the low-motion one.
    """
    clips = []
    for i, (name, color, motion) in enumerate((
        ("a", "0x0F2A4A", 0.15),  # low → eligible
        ("b", "0x22D3B7", 0.85),  # high → skipped
    )):
        p = tmp_path / f"{name}.mp4"
        _make_clip(p, color)
        clips.append({"path": str(p), "motion": motion})
    clips[0]["is_hero"] = True

    captured = {}
    from app.services.video import pipeline as pipe_mod

    real_run = pipe_mod.run_ffmpeg

    async def spy_run(cmd, *a, **kw):
        captured["cmd"] = " ".join(cmd)
        return await real_run(cmd, *a, **kw)

    monkeypatch.setattr(pipe_mod, "run_ffmpeg", spy_run)

    r = client.post("/api/v1/mix-video/preview", json={
        "project_id": "pd-kb-mixed",
        "template": "product-demo",
        "clips": clips,
    })
    assert r.status_code == 200, r.text

    cmd = captured.get("cmd", "")
    # Exactly one zoompan (low-motion clip only); other clip uses pad/scale normalize.
    assert cmd.count("zoompan") == 1
    # The skipped clip should appear in normalize form (pad= present)
    assert "pad=640:360" in cmd
