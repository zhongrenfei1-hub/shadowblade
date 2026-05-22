"""Lock-in tests for the product-demo template.

Three layers of coverage:
1. Schema/inheritance — values match the design brief and `extends: base`
   is correctly resolved.
2. Apply — folding into ``MixVideoRequest`` populates the pipeline knobs
   the template is responsible for (color/preset/lufs/etc).
3. End-to-end — a real ffmpeg render via ``POST /mix-video/preview``.
   Skipped automatically when ffmpeg is unavailable.
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
from app.services.template.loader import _load_cached

client = TestClient(app)


# ---------- schema / inheritance --------------------------------------------


def test_product_demo_loads_and_resolves_extends():
    _load_cached.cache_clear()
    t = load_template("product-demo", fresh=True)

    assert t.name == "product-demo"
    assert t.extends is None  # base merged in

    # Design brief assertions
    assert t.transition.style == "editorial"
    assert t.transition.max_duration == 0.6

    assert t.subtitle.size_baseline == 72
    assert t.subtitle.max_chars_per_line == 18
    assert t.subtitle.fill_color == "#F5F7FB"
    assert t.subtitle.outline_color == "#0F2A4A"
    assert t.subtitle.cps_warn == 12.0

    assert t.pacing.target_shot == 4.5
    assert t.pacing.min_shot == 2.0
    assert t.pacing.max_shot == 8.0
    assert t.pacing.must_include_hero is True

    assert t.audio.target_lufs == -16.0
    assert t.audio.adaptive_bgm_mix is True
    assert t.audio.duck_threshold_db == -28.0
    assert t.audio.duck_ratio == 8.0

    assert t.cover.style == "photo"
    assert t.cover.title_required is True

    assert t.watermark.position == "br"
    assert t.watermark.opacity == 0.62
    assert t.watermark.width_pct == 0.13

    assert t.color.look == "cinematic"
    assert t.color.auto_white_balance is True

    assert t.encode.preset == "hero_16x9"


def test_product_demo_promotes_ken_burns_to_first_class_group():
    t = load_template("product-demo", fresh=True)
    # ken_burns is now a first-class template group, not buried in extras
    assert t.ken_burns.enabled is True
    assert t.ken_burns.intensity == "subtle"
    assert t.ken_burns.default_direction == "auto"
    assert t.ken_burns.max_zoom == 1.08
    assert t.ken_burns.apply_to == "low_motion"
    # extras must NOT still carry it
    assert "ken_burns" not in t.extras


def test_product_demo_extras_carry_brand_palette_and_purpose():
    t = load_template("product-demo", fresh=True)
    palette = t.extras.get("brand_palette") or {}
    assert palette.get("primary") == "#0F2A4A"
    assert palette.get("accent") == "#22D3B7"
    assert t.extras.get("purpose") == "product_demo"


# ---------- apply layer -----------------------------------------------------


def test_product_demo_folds_into_mix_video_request():
    t = load_template("product-demo", fresh=True)
    body = MixVideoRequest(
        project_id="pd-1",
        clips=[ClipPayload(path="/tmp/a.mp4"), ClipPayload(path="/tmp/b.mp4")],
    )
    out = apply_template_to_request(t, body)

    # Pipeline-mapped fields populated from template
    assert out.preset == "hero_16x9"
    assert out.color_look == "cinematic"
    assert out.auto_white_balance is True
    assert out.adaptive_bgm_mix is True
    assert out.transition_style == "editorial"
    assert out.max_transition == 0.6
    assert out.watermark_position == "br"

    # Brand seeded from template's audio/watermark group
    assert out.brand is not None
    assert out.brand.target_lufs == -16.0
    assert out.brand.watermark_opacity == 0.62
    assert out.brand.watermark_width_pct == 0.13


def test_product_demo_user_explicit_still_wins():
    t = load_template("product-demo", fresh=True)
    body = MixVideoRequest(
        project_id="pd-1",
        clips=[ClipPayload(path="/tmp/a.mp4"), ClipPayload(path="/tmp/b.mp4")],
        preset="social_9x16",  # user picks vertical despite template default
        color_look="warm",
    )
    out = apply_template_to_request(t, body)
    assert out.preset == "social_9x16"
    assert out.color_look == "warm"
    # Other knobs the user didn't touch still come from the template:
    assert out.adaptive_bgm_mix is True


# ---------- API endpoints ---------------------------------------------------


def test_get_template_endpoint_returns_product_demo():
    r = client.get("/api/v1/templates?fresh=true")
    assert r.status_code == 200
    names = {it["name"] for it in r.json()["items"]}
    assert "product-demo" in names


def test_get_one_template_endpoint_returns_resolved_doc():
    r = client.get("/api/v1/templates/product-demo?fresh=true")
    assert r.status_code == 200
    body = r.json()
    assert body["extends"] is None
    assert body["encode"]["preset"] == "hero_16x9"
    assert body["ken_burns"]["intensity"] == "subtle"


# ---------- real ffmpeg render ---------------------------------------------


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _make_lavfi_clip(path: Path, color: str, duration: float = 3.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:d={duration},format=yuv420p",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_product_demo_preview_end_to_end(tmp_path):
    """Render a 3-clip lavfi preview using template=product-demo."""
    clips = []
    for name, color in (("a", "0x0F2A4A"), ("b", "0x22D3B7"), ("c", "0xF5F7FB")):
        p = tmp_path / f"{name}.mp4"
        _make_lavfi_clip(p, color)
        clips.append({"path": str(p)})
    clips[0]["is_hero"] = True

    payload = {
        "project_id": "pd-pytest",
        "template": "product-demo",
        "clips": clips,
        "title": "ShadowBlade · Product Demo",
    }
    r = client.post("/api/v1/mix-video/preview", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    # Preview pathway forces preset → preview_360_16x9 (because template
    # set social_16x9 and the preview endpoint downsamples by aspect).
    assert data["preset"] == "preview_360_16x9"
    assert data["duration"] > 0
    # editorial style → fade-family transitions
    for tr in data["transitions"]:
        assert tr in {"fade", "fadeblack", "fadewhite", "dissolve"}, tr

    output = Path(data["output_path"])
    assert output.exists()
    assert output.stat().st_size > 1024

    # Confirm a valid h264 + aac container
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,height",
            "-of", "default=nw=1",
            str(output),
        ],
        capture_output=True, text=True, check=True,
    )
    out = probe.stdout
    assert "codec_type=video" in out
    assert "codec_name=h264" in out
    assert "codec_type=audio" in out
    # 360p preview height
    assert "height=360" in out
