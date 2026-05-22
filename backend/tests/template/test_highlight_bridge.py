"""Bridge tests — template.highlight reaches the subtitle renderers.

Coverage:
1. parser  — [词] markers identified, escapes honoured.
2. ASS     — color override generated, fallback strips markers cleanly.
3. PNG     — per-segment fill colours render with bold/underline options.
4. apply   — fields fold MixVideoRequest → MixRequest.
5. pipeline / product-demo — full path: kit.accent_color used as fallback,
   PNG manifests carry coloured pixels.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from app.api.mix_video import MixVideoRequest, _build_mix_request
from app.services.template import apply_template_to_request, load_template
from app.services.template.schema import Template, TemplateHighlight
from app.services.video.highlight import (
    HighlightSegment,
    hex_to_ass_color,
    parse_markers,
    strip_markers,
    to_ass_color_override,
)
from app.services.video.subtitle import Cue, render_ass
from app.services.video.text_render import render_subtitle_png


def _body(**overrides) -> MixVideoRequest:
    base = {"project_id": 1, "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}]}
    base.update(overrides)
    return MixVideoRequest.model_validate(base)


# ---------- parser ----------------------------------------------------------


def test_parse_markers_basic():
    segs = parse_markers("让 [SaaS 产品演示] 更专业。")
    assert segs == [
        HighlightSegment("让 ", False),
        HighlightSegment("SaaS 产品演示", True),
        HighlightSegment(" 更专业。", False),
    ]


def test_parse_markers_multiple():
    segs = parse_markers("[A] 加 [B] 等于 [C]")
    assert [s.text for s in segs] == ["A", " 加 ", "B", " 等于 ", "C"]
    assert [s.is_highlight for s in segs] == [True, False, True, False, True]


def test_parse_markers_escape():
    segs = parse_markers(r"价格 \[USD\] [优惠]")
    # \[ and \] become literal [ and ]
    assert [s.text for s in segs] == ["价格 [USD] ", "优惠"]


def test_parse_markers_no_markers():
    segs = parse_markers("纯文本")
    assert segs == [HighlightSegment("纯文本", False)]


def test_parse_markers_empty_string():
    segs = parse_markers("")
    assert segs == [HighlightSegment("", False)]


def test_strip_markers():
    assert strip_markers("让 [SaaS] 更 [快]") == "让 SaaS 更 快"
    assert strip_markers(r"\[USD\]") == "[USD]"
    assert strip_markers("none") == "none"


# ---------- ASS conversion --------------------------------------------------


def test_hex_to_ass_color_blue_to_bgr():
    # Brand accent #22D3B7 → R=22, G=D3, B=B7 → ASS &HB7D322&
    assert hex_to_ass_color("#22D3B7") == "&HB7D322&"


def test_to_ass_color_override_wraps_keywords():
    out = to_ass_color_override("让 [SaaS] 飞起来", "#22D3B7")
    assert "{\\1c&HB7D322&}" in out
    assert "SaaS" in out
    assert "{\\r}" in out
    # Plain segments untouched
    assert "让 " in out
    assert "飞起来" in out


def test_to_ass_color_override_with_bold():
    out = to_ass_color_override("[关键]", "#22D3B7", bold=True)
    assert "{\\b1}" in out
    assert "{\\b0}" in out


def test_render_ass_with_highlight_color_inlines_override():
    cues = [Cue(start=0.0, end=2.0, text="让 [SaaS] 飞起来")]
    out = render_ass(cues, highlight_color="#22D3B7")
    assert "{\\1c&HB7D322&}" in out
    assert "SaaS" in out


def test_render_ass_without_highlight_strips_markers():
    cues = [Cue(start=0.0, end=2.0, text="让 [SaaS] 飞起来")]
    out = render_ass(cues, highlight_color=None)
    assert "[SaaS]" not in out
    assert "SaaS" in out
    # No colour override emitted
    assert "{\\1c" not in out


# ---------- PNG render ------------------------------------------------------


def _sample(img: Image.Image, x_pct: float, y_pct: float) -> tuple[int, int, int, int]:
    x = int(img.width * x_pct)
    y = int(img.height * y_pct)
    return img.getpixel((x, y))


def test_render_subtitle_png_recolors_highlighted_segment():
    img = render_subtitle_png(
        "让 [SaaS] 飞",
        video_width=1280,
        video_height=720,
        font_size=80,
        fill_hex="#FFFFFF",
        outline_hex="#0F2A4A",
        outline_width=2,
        highlight_color="#22D3B7",
    )
    pixels = list(img.getdata())
    # We expect to find pixels close to the accent colour (#22D3B7 → 34,211,183)
    has_accent = any(
        abs(p[0] - 34) < 35 and abs(p[1] - 211) < 35 and abs(p[2] - 183) < 35 and p[3] > 180
        for p in pixels
    )
    assert has_accent, "highlight color #22D3B7 not detected in rendered PNG"


def test_render_subtitle_png_without_highlight_has_no_accent_pixels():
    img = render_subtitle_png(
        "让 [SaaS] 飞",
        video_width=1280,
        video_height=720,
        font_size=80,
        fill_hex="#FFFFFF",
        outline_hex="#0F2A4A",
        outline_width=2,
        highlight_color=None,
    )
    pixels = list(img.getdata())
    has_accent = any(
        abs(p[0] - 34) < 25 and abs(p[1] - 211) < 25 and abs(p[2] - 183) < 25 and p[3] > 180
        for p in pixels
    )
    assert not has_accent, "no highlight requested, but accent pixels appeared anyway"


def test_render_subtitle_png_with_underline_adds_solid_band():
    img = render_subtitle_png(
        "[关键词]",
        video_width=1280,
        video_height=720,
        font_size=80,
        fill_hex="#FFFFFF",
        outline_hex="#0F2A4A",
        outline_width=2,
        highlight_color="#22D3B7",
        highlight_underline=True,
    )
    # Look for a horizontal run of accent pixels near the bottom — the underline.
    rgba = img.convert("RGBA")
    found_run = False
    for y in range(img.height - 1, max(0, img.height - 40), -1):
        run = 0
        for x in range(img.width):
            p = rgba.getpixel((x, y))
            if (
                abs(p[0] - 34) < 30
                and abs(p[1] - 211) < 30
                and abs(p[2] - 183) < 30
                and p[3] > 200
            ):
                run += 1
                if run > 40:
                    found_run = True
                    break
            else:
                run = 0
        if found_run:
            break
    assert found_run, "underline band not detected"


# ---------- schema validation -----------------------------------------------


def test_schema_highlight_extra_field_rejected():
    with pytest.raises(ValidationError):
        TemplateHighlight.model_validate({"foo": "bar"})


# ---------- apply -----------------------------------------------------------


def test_apply_folds_highlight_fields():
    tmpl = Template(
        name="t",
        highlight=TemplateHighlight(
            enabled=True, color="#22D3B7", weight_bold=True, underline_keywords=True
        ),
    )
    out = apply_template_to_request(tmpl, _body())
    assert out.highlight_enabled is True
    assert out.highlight_color == "#22D3B7"
    assert out.highlight_bold is True
    assert out.highlight_underline is True


def test_user_override_wins_for_highlight():
    tmpl = Template(name="t", highlight=TemplateHighlight(enabled=True, color="#22D3B7"))
    body = _body(highlight_enabled=False, highlight_color="#FF00FF")
    out = apply_template_to_request(tmpl, body)
    assert out.highlight_enabled is False
    assert out.highlight_color == "#FF00FF"


# ---------- product-demo end-to-end -----------------------------------------


def test_product_demo_highlight_reaches_mix_request():
    body = MixVideoRequest.model_validate(
        {
            "project_id": "pd-hl",
            "template": "product-demo",
            "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
        }
    )
    req = _build_mix_request(body)
    assert req.highlight_enabled is True
    assert req.highlight_color == "#22D3B7"
    assert req.highlight_bold is True
    assert req.highlight_underline is False
