"""Bridge tests — template.cover layout fields reach CoverSpec.

Coverage:
1. schema: Literal/bounds validation on new layout fields.
2. apply: layout fields fold through MixVideoRequest → MixRequest.
3. covers._title_xy helper: position keyword → (x, y) expression.
4. End-to-end via real ffmpeg: drawbox + drawtext appear in the cover
   generation command with the right coordinates and colour.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.mix_video import ClipPayload, MixVideoRequest, _build_mix_request
from app.main import app
from app.services.template import apply_template_to_request, load_template
from app.services.template.schema import Template, TemplateCover
from app.services.video.covers import CoverSpec, _title_xy, generate_cover

client = TestClient(app)


def _body(**overrides) -> MixVideoRequest:
    base = {"project_id": 1, "clips": [{"path": "/tmp/a.mp4"}]}
    base.update(overrides)
    return MixVideoRequest.model_validate(base)


# ---------- schema ----------------------------------------------------------


def test_schema_cover_invalid_title_position_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateCover.model_validate({"title_position": "diagonal"})


def test_schema_cover_invalid_strip_position_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateCover.model_validate({"brand_strip_position": "inside"})


def test_schema_cover_strip_width_bounded():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateCover.model_validate({"brand_strip_width_pct": 0.9})


def test_schema_cover_title_max_chars_bounded():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TemplateCover.model_validate({"title_max_chars": 999})


# ---------- apply ------------------------------------------------------------


def test_apply_folds_all_cover_layout_fields():
    tmpl = Template(
        name="t",
        cover=TemplateCover(
            title_position="left-center",
            title_max_chars=22,
            show_brand_strip=True,
            brand_strip_color="#0F2A4A",
            brand_strip_position="left",
            brand_strip_width_pct=0.05,
        ),
    )
    out = apply_template_to_request(tmpl, _body())
    assert out.cover_title_position == "left-center"
    assert out.cover_title_max_chars == 22
    assert out.cover_show_brand_strip is True
    assert out.cover_brand_strip_color == "#0F2A4A"
    assert out.cover_brand_strip_position == "left"
    assert out.cover_brand_strip_width_pct == 0.05


def test_apply_user_cover_field_beats_template():
    tmpl = Template(
        name="t",
        cover=TemplateCover(show_brand_strip=True, brand_strip_position="left"),
    )
    body = _body(cover_show_brand_strip=False, cover_brand_strip_position="bottom")
    out = apply_template_to_request(tmpl, body)
    assert out.cover_show_brand_strip is False
    assert out.cover_brand_strip_position == "bottom"


# ---------- _title_xy helper ------------------------------------------------


@pytest.mark.parametrize(
    "position,expected_x,expected_y",
    [
        ("bottom-center", "(w-text_w)/2", "h-th-h*0.12"),
        ("center", "(w-text_w)/2", "(h-text_h)/2"),
        ("left-center", "w*0.07", "(h-text_h)/2"),
        ("right-center", "w-text_w-w*0.07", "(h-text_h)/2"),
        ("top-left", "w*0.07", "h*0.10"),
    ],
)
def test_title_xy_helper(position, expected_x, expected_y):
    x, y = _title_xy(position)
    assert x == expected_x
    assert y == expected_y


# ---------- product-demo specific -------------------------------------------


def test_product_demo_cover_layout_lands_in_mix_request():
    body = MixVideoRequest.model_validate(
        {
            "project_id": "pd-cover",
            "template": "product-demo",
            "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
        }
    )
    req = _build_mix_request(body)
    assert req.cover_title_position == "left-center"
    assert req.cover_title_max_chars == 22
    assert req.cover_show_brand_strip is True
    assert req.cover_brand_strip_color == "#0F2A4A"
    assert req.cover_brand_strip_position == "left"


# ---------- real ffmpeg: cover bytes contain the strip + title --------------


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _make_clip(path: Path, color: str, duration: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:d={duration},format=yuv420p",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
        ],
        check=True, capture_output=True,
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_cover_with_brand_strip_renders_left_strip(tmp_path):
    """Generate a 1920x1080 cover with a left brand strip + left-center title.
    Sample the left-edge column — it must be dominated by the strip colour
    (deep blue 0F2A4A), and the right edge must remain source colour.
    """
    src = tmp_path / "src.mp4"
    _make_clip(src, "0xCCCCCC")  # neutral grey source
    out_path = tmp_path / "cover.jpg"

    asyncio.run(
        generate_cover(
            src,
            out_path,
            timestamp=1.0,
            spec=CoverSpec(
                width=1920,
                height=1080,
                primary="#0F2A4A",
                accent="#22D3B7",
                title="ShadowBlade Demo",
                title_position="left-center",
                title_max_chars=22,
                show_brand_strip=True,
                brand_strip_color="#0F2A4A",
                brand_strip_position="left",
                brand_strip_width_pct=0.05,
            ),
        )
    )

    assert out_path.exists()
    assert out_path.stat().st_size > 2048

    # Sample the left-strip area and the right-half area; the strip
    # average should be much closer to #0F2A4A than the source grey is.
    def avg(area: str) -> tuple[int, int, int]:
        r = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", str(out_path),
                "-vf", f"crop={area},scale=1:1",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
            ],
            capture_output=True, check=True,
        )
        b = r.stdout
        return (b[0], b[1], b[2])

    strip_rgb = avg("48:1080:0:0")  # 48 px wide stripe, full height, left edge
    right_rgb = avg("1500:1080:200:0")  # 1500 px wide area starting at x=200
    # Strip should be very dark blue-ish (R<60, G<70, B<120ish but R<G<B)
    assert strip_rgb[0] < 60, f"strip R too high: {strip_rgb}"
    assert strip_rgb[2] > strip_rgb[0], f"strip not blue-leaning: {strip_rgb}"
    # Right area should still resemble grey-ish source (R>120 typically)
    assert right_rgb[0] > 90, f"right R too low (strip leaked?): {right_rgb}"


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not on PATH")
def test_product_demo_full_render_writes_cover_with_strip(tmp_path):
    """Full mix-video preview path with product-demo — cover must exist."""
    clips = []
    for name, color in (("a", "0x808080"), ("b", "0xAAAAAA")):
        p = tmp_path / f"{name}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:d=3,format=yuv420p",
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                str(p),
            ], check=True, capture_output=True,
        )
        clips.append({"path": str(p), "motion": 0.2})
    clips[0]["is_hero"] = True

    r = client.post("/api/v1/mix-video/preview", json={
        "project_id": "pd-cover-e2e",
        "template": "product-demo",
        "clips": clips,
        "title": "Cover With Strip",
    })
    assert r.status_code == 200, r.text
    cover_path = Path(r.json()["cover_path"])
    assert cover_path.exists()
    assert cover_path.stat().st_size > 2048
