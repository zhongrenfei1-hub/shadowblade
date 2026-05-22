"""product-demo-tutorial: a 3-level extends chain + 教程 specifics.

Hierarchy:
    base → product-demo → product-demo-tutorial
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
from app.services.template.loader import _force_rescan_for_tests

client = TestClient(app)


# ---------- inheritance ----------------------------------------------------


def test_tutorial_loads_and_resolves():
    _force_rescan_for_tests()
    t = load_template("product-demo-tutorial", fresh=True)
    assert t.name == "product-demo-tutorial"
    assert t.extends is None


def test_tutorial_own_fields():
    t = load_template("product-demo-tutorial", fresh=True)
    # Slower pace
    assert t.transition.style == "calm"
    assert t.transition.max_duration == 0.7
    assert t.pacing.target_shot == 6.0
    assert t.pacing.max_shot == 12.0
    # Bigger subtitles, stricter CPS
    assert t.subtitle.size_baseline == 78
    assert t.subtitle.max_chars_per_line == 16
    assert t.subtitle.cps_warn == 11.0
    # Deeper ducking for tutorial voice clarity
    assert t.audio.duck_threshold_db == -32.0
    assert t.audio.duck_ratio == 10.0
    assert t.audio.fade_out == 1.6
    # Stronger ken_burns for emphasis
    assert t.ken_burns.intensity == "medium"
    assert t.ken_burns.max_zoom == 1.18
    assert t.ken_burns.apply_to == "all"
    # Underlined keywords for didactic emphasis
    assert t.highlight.underline_keywords is True


def test_tutorial_inherits_from_product_demo():
    t = load_template("product-demo-tutorial", fresh=True)
    # Stays horizontal
    assert t.encode.preset == "hero_16x9"
    # Cinematic look from pd
    assert t.color.look == "cinematic"
    # Highlight colour + bold from pd (tutorial only added underline)
    assert t.highlight.color == "#22D3B7"
    assert t.highlight.weight_bold is True
    # Watermark policy from pd
    assert t.watermark.position == "br"
    # Target loudness from pd
    assert t.audio.target_lufs == -16.0


def test_tutorial_carries_step_numbering_extras():
    t = load_template("product-demo-tutorial", fresh=True)
    sn = t.extras.get("step_numbering")
    assert sn is not None
    assert sn.get("enabled") is True
    assert sn.get("format") == "{n}/{total}"
    # brand_palette透传 from pd
    palette = t.extras.get("brand_palette") or {}
    assert palette.get("accent") == "#22D3B7"


# ---------- API endpoint --------------------------------------------------


def test_get_tutorial_returns_resolved_doc():
    r = client.get("/api/v1/templates/product-demo-tutorial?fresh=true")
    assert r.status_code == 200
    body = r.json()
    assert body["extends"] is None
    assert body["encode"]["preset"] == "hero_16x9"
    assert body["ken_burns"]["intensity"] == "medium"
    assert body["highlight"]["underline_keywords"] is True


def test_tutorial_folds_into_mix_request():
    body = MixVideoRequest.model_validate(
        {
            "project_id": "tut-1",
            "template": "product-demo-tutorial",
            "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
        }
    )
    req = _build_mix_request(body)
    assert req.preset == "hero_16x9"
    assert req.transition_style == "calm"
    assert req.max_transition == 0.7
    assert req.ken_burns_enabled is True
    assert req.ken_burns_intensity == "medium"
    assert req.ken_burns_max_zoom == 1.18
    assert req.ken_burns_apply_to == "all"
    assert req.highlight_underline is True


# ---------- real ffmpeg ---------------------------------------------------


def _ffmpeg() -> bool:
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


@pytest.mark.skipif(not _ffmpeg(), reason="ffmpeg not on PATH")
def test_tutorial_preview_renders_horizontal_with_medium_ken_burns(tmp_path, monkeypatch):
    clips = []
    for i, (name, color) in enumerate((("a", "0x0F2A4A"), ("b", "0x22D3B7"))):
        p = tmp_path / f"{name}.mp4"
        _make_clip(p, color)
        clips.append({"path": str(p), "motion": 0.2})  # apply_to=all anyway
    clips[0]["is_hero"] = True

    captured = {}
    from app.services.video import pipeline as pipe_mod
    real_run = pipe_mod.run_ffmpeg

    async def spy(cmd, *a, **k):
        captured["cmd"] = " ".join(cmd)
        return await real_run(cmd, *a, **k)

    monkeypatch.setattr(pipe_mod, "run_ffmpeg", spy)

    r = client.post("/api/v1/mix-video/preview", json={
        "project_id": "tut-e2e",
        "template": "product-demo-tutorial",
        "clips": clips,
        "title": "Tutorial Demo",
        "cues": [
            {"start": 0.0, "end": 2.5, "text": "Step [1/3]: 打开仪表盘"},
            {"start": 2.5, "end": 5.5, "text": "Step [2/3]: 点击 [创建项目]"},
        ],
    })
    assert r.status_code == 200, r.text
    data = r.json()
    # tutorial → hero_16x9 → preview_360_16x9
    assert data["preset"] == "preview_360_16x9"

    cmd = captured.get("cmd", "")
    # medium ken_burns → max_zoom 1.18 in zoompan expression
    assert "zoompan" in cmd
    assert "1.18" in cmd
    # apply_to=all → both clips have zoompan
    assert cmd.count("zoompan") == 2
