"""Multi-level inheritance + vertical-specific assertions.

Hierarchy under test:

    base   (builtin)
      └─ product-demo
            └─ product-demo-vertical
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.mix_video import MixVideoRequest, _build_mix_request
from app.main import app
from app.services.template import load_template
from app.services.template.loader import _load_cached

client = TestClient(app)


# ---------- multi-level inheritance ----------------------------------------


def test_product_demo_vertical_loads():
    _load_cached.cache_clear()
    t = load_template("product-demo-vertical", fresh=True)
    assert t.name == "product-demo-vertical"
    assert t.extends is None  # fully resolved


def test_vertical_own_fields_take_effect():
    """Fields the vertical template declares win over the parent chain."""
    t = load_template("product-demo-vertical", fresh=True)

    # encode preset overridden
    assert t.encode.preset == "social_9x16"
    # subtitle adapted for vertical
    assert t.subtitle.size_baseline == 88
    assert t.subtitle.margin_v_baseline == 260
    assert t.subtitle.max_chars_per_line == 14
    assert t.subtitle.cps_warn == 13.0
    # faster pacing
    assert t.pacing.target_shot == 2.5
    assert t.pacing.min_shot == 1.2
    assert t.pacing.max_shot == 5.0
    # cover: center title + top accent strip
    assert t.cover.title_position == "center"
    assert t.cover.title_max_chars == 16
    assert t.cover.brand_strip_position == "top"
    assert t.cover.brand_strip_color == "#22D3B7"
    # tighter transitions
    assert t.transition.max_duration == 0.4
    # bigger but less opaque watermark for vertical
    assert t.watermark.opacity == 0.55
    assert t.watermark.width_pct == 0.18


def test_vertical_inherits_unset_fields_from_product_demo():
    """Anything the vertical doesn't touch should come from product-demo."""
    t = load_template("product-demo-vertical", fresh=True)

    # color group untouched by vertical → from product-demo
    assert t.color.look == "cinematic"
    assert t.color.auto_white_balance is True
    # ken_burns untouched → from product-demo
    assert t.ken_burns.enabled is True
    assert t.ken_burns.intensity == "subtle"
    assert t.ken_burns.apply_to == "low_motion"
    # highlight untouched → from product-demo
    assert t.highlight.enabled is True
    assert t.highlight.color == "#22D3B7"
    assert t.highlight.weight_bold is True
    # transition.style untouched → from product-demo (editorial)
    assert t.transition.style == "editorial"
    # subtitle colour untouched → from product-demo
    assert t.subtitle.fill_color == "#F5F7FB"
    assert t.subtitle.outline_color == "#0F2A4A"


def test_vertical_inherits_through_chain_from_base():
    """Fields set only on base should reach the grandchild."""
    t = load_template("product-demo-vertical", fresh=True)
    # base sets subtitle.enabled=true; neither pd nor vertical touch it
    assert t.subtitle.enabled is True
    # base sets pacing.must_include_hero=true; pd doesn't touch it; vertical doesn't either
    assert t.pacing.must_include_hero is True


def test_vertical_overrides_grandparent_audio_target_lufs():
    """Vertical resets audio.target_lufs (-14, social standard) over
    product-demo's -16 (enterprise) over base's -14.
    """
    t = load_template("product-demo-vertical", fresh=True)
    assert t.audio.target_lufs == -14.0
    # But pd's other audio knobs are kept (vertical didn't touch them)
    assert t.audio.bgm_gain_db == -8.0
    assert t.audio.adaptive_bgm_mix is True
    assert t.audio.duck_threshold_db == -28.0


def test_vertical_extras_merged_with_brand_palette_inherited():
    t = load_template("product-demo-vertical", fresh=True)
    assert t.extras.get("purpose") == "product_demo_vertical"
    assert "tiktok" in t.extras.get("platforms", [])
    # brand_palette comes from product-demo via extras shallow merge
    palette = t.extras.get("brand_palette") or {}
    assert palette.get("primary") == "#0F2A4A"
    assert palette.get("accent") == "#22D3B7"


# ---------- API endpoint ---------------------------------------------------


def test_list_includes_vertical():
    r = client.get("/api/v1/templates?fresh=true")
    assert r.status_code == 200
    names = [it["name"] for it in r.json()["items"]]
    assert "product-demo-vertical" in names


def test_get_vertical_returns_resolved_doc():
    r = client.get("/api/v1/templates/product-demo-vertical?fresh=true")
    assert r.status_code == 200
    body = r.json()
    assert body["extends"] is None  # resolved
    assert body["encode"]["preset"] == "social_9x16"
    assert body["ken_burns"]["enabled"] is True  # from pd
    assert body["highlight"]["color"] == "#22D3B7"  # from pd


# ---------- MixRequest fold ------------------------------------------------


def test_vertical_folds_into_mix_request():
    body = MixVideoRequest.model_validate(
        {
            "project_id": "pdv-fold",
            "template": "product-demo-vertical",
            "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
        }
    )
    req = _build_mix_request(body)
    # vertical-specific
    assert req.preset == "social_9x16"
    assert req.max_transition == 0.4
    # inherited from pd
    assert req.color_look == "cinematic"
    assert req.ken_burns_enabled is True
    assert req.highlight_enabled is True
    assert req.highlight_color == "#22D3B7"


# ---------- real ffmpeg 9x16 render ----------------------------------------


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _make_vertical_clip(path: Path, color: str, duration: float = 2.5) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d={duration},format=yuv420p",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_vertical_preview_renders_9x16(tmp_path):
    clips = []
    for name, color in (("a", "0x0F2A4A"), ("b", "0x22D3B7"), ("c", "0xF5F7FB")):
        p = tmp_path / f"{name}.mp4"
        _make_vertical_clip(p, color)
        clips.append({"path": str(p), "motion": 0.15})
    clips[0]["is_hero"] = True

    r = client.post("/api/v1/mix-video/preview", json={
        "project_id": "pdv-e2e",
        "template": "product-demo-vertical",
        "clips": clips,
        "title": "竖屏产品演示",
        "cues": [
            {"start": 0.0, "end": 2.0, "text": "让 [SaaS] 飞起来"},
            {"start": 2.0, "end": 4.5, "text": "[3 步] 完成"},
        ],
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["preset"] == "preview_360_9x16"  # template→social_9x16 then preview downsample
    output = Path(data["output_path"])
    assert output.exists()

    # Confirm it's vertical (360x640)
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(output),
        ],
        capture_output=True, text=True, check=True,
    )
    w, h = (int(x) for x in probe.stdout.strip().split(","))
    assert h > w, f"expected vertical, got {w}x{h}"
    assert (w, h) == (360, 640)
