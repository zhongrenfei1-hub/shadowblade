"""Brand Kit injection into MixVideoRequest + Template merge tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.api.mix_video import BrandPayload, MixVideoRequest
from app.services.template import (
    apply_brand_and_template,
    apply_brand_kit_to_request,
    load_template,
)
from app.services.video.brand import BrandKit


# A minimal stand-in for the ORM row — what apply_brand_kit_to_request reads
# from. SimpleNamespace lets us pass an arbitrary attribute bag without
# pulling SQLAlchemy into a unit test.
def _fake_kit(**overrides):
    base = dict(
        name="Acme",
        primary_color="#101728",
        secondary_color="#FFFFFF",
        accent_color="#FF7849",
        font_heading="Inter Display",
        font_body="Inter",
        watermark_text=None,
        watermark_opacity=0.62,
        watermark_position="tl",
        watermark_width_pct=0.18,
        target_lufs=-16.0,
        target_tp=-1.5,
        bgm_gain_db=-8.0,
        subtitle_size=72,
        subtitle_margin_v=132,
        logo_url="/static/storage/brand_kits/1/acme.png",
        default_template_name=None,
        voice="alloy-en-female",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _baseline_request(**overrides) -> MixVideoRequest:
    payload = {
        "project_id": "demo",
        "clips": [{"path": "/tmp/clip.mp4"}],
    }
    payload.update(overrides)
    return MixVideoRequest.model_validate(payload)


# --- apply_brand_kit_to_request --------------------------------------------


def test_kit_seeds_brand_payload_when_user_omits_it():
    body = _baseline_request()
    out = apply_brand_kit_to_request(_fake_kit(), body)
    assert out.brand is not None
    assert out.brand.primary_color == "#101728"
    assert out.brand.accent_color == "#FF7849"
    assert out.brand.target_lufs == pytest.approx(-16.0)
    assert out.brand.subtitle_size == 72


def test_kit_does_not_clobber_user_supplied_colors():
    body = _baseline_request(brand={"primary_color": "#000000"})
    out = apply_brand_kit_to_request(_fake_kit(), body)
    # user-explicit primary stays, but kit fills the rest
    assert out.brand.primary_color == "#000000"
    assert out.brand.accent_color == "#FF7849"


def test_kit_watermark_path_falls_back_to_logo_url():
    body = _baseline_request()
    out = apply_brand_kit_to_request(_fake_kit(), body)
    assert out.watermark_path == "/static/storage/brand_kits/1/acme.png"


def test_kit_watermark_path_respects_user_value():
    body = _baseline_request(watermark_path="/tmp/my-logo.png")
    out = apply_brand_kit_to_request(_fake_kit(), body)
    assert out.watermark_path == "/tmp/my-logo.png"


def test_kit_watermark_position_used_when_user_keeps_default():
    body = _baseline_request()  # leaves watermark_position default 'br'
    out = apply_brand_kit_to_request(_fake_kit(), body)
    assert out.watermark_position == "tl"


def test_kit_does_not_override_explicit_watermark_position():
    body = _baseline_request(watermark_position="bc")
    out = apply_brand_kit_to_request(_fake_kit(), body)
    assert out.watermark_position == "bc"


def test_kit_default_template_name_seeds_template_field():
    body = _baseline_request()
    out = apply_brand_kit_to_request(
        _fake_kit(default_template_name="product-demo"),
        body,
    )
    assert out.template == "product-demo"


def test_kit_default_template_name_not_overriding_user_template():
    body = _baseline_request(template="hero-launch")
    out = apply_brand_kit_to_request(
        _fake_kit(default_template_name="product-demo"),
        body,
    )
    assert out.template == "hero-launch"


def test_none_kit_passes_through_unchanged():
    body = _baseline_request()
    out = apply_brand_kit_to_request(None, body)
    assert out.brand is None  # nothing seeded


def test_dict_kit_also_works():
    """The merge helper accepts plain dicts (e.g. from fixtures)."""
    body = _baseline_request()
    kit = {
        "primary_color": "#000000",
        "accent_color": "#FFFFFF",
        "logo_url": "/tmp/d.png",
        "watermark_position": "bl",
    }
    out = apply_brand_kit_to_request(kit, body)
    assert out.brand.primary_color == "#000000"
    assert out.brand.accent_color == "#FFFFFF"
    assert out.watermark_position == "bl"
    assert out.watermark_path == "/tmp/d.png"


# --- combined precedence ----------------------------------------------------


def test_brand_then_template_precedence():
    """User → kit → template precedence, against a real template."""
    tmpl = load_template("product-demo", fresh=True)
    body = _baseline_request()
    out = apply_brand_and_template(
        brand_kit=_fake_kit(accent_color="#FF00FF"),
        template=tmpl,
        body=body,
    )
    # Kit (already in body.brand from the brand merge) wins over template
    # palette hints — kit's accent_color survives.
    assert out.brand.accent_color == "#FF00FF"
    # Template still fills request-level fields the kit doesn't touch.
    assert out.transition_style == "editorial"
    assert out.ken_burns_enabled is True


def test_user_brand_beats_kit_beats_template():
    tmpl = load_template("product-demo", fresh=True)
    body = _baseline_request(brand={"accent_color": "#123456"})
    out = apply_brand_and_template(
        brand_kit=_fake_kit(accent_color="#FF00FF"),
        template=tmpl,
        body=body,
    )
    # User > kit > template
    assert out.brand.accent_color == "#123456"


# --- product-demo end-to-end ------------------------------------------------


def test_product_demo_template_full_brand_path():
    """End-to-end on the real product-demo template, no DB.

    Confirms that the template + brand kit pipeline together produces a
    fully-populated MixVideoRequest with the demo palette, Ken Burns
    enabled, and the highlight policy on.
    """
    tmpl = load_template("product-demo", fresh=True)
    kit = _fake_kit(
        primary_color="#0F2A4A",
        secondary_color="#F5F7FB",
        accent_color="#22D3B7",
        logo_url="/static/storage/brand_kits/1/acme-logo.png",
        default_template_name="product-demo",
    )
    body = _baseline_request(template="product-demo")
    out = apply_brand_and_template(brand_kit=kit, template=tmpl, body=body)

    # palette flows through (kit values match the product-demo defaults)
    assert out.brand.primary_color == "#0F2A4A"
    assert out.brand.secondary_color == "#F5F7FB"
    assert out.brand.accent_color == "#22D3B7"
    # template-level features turn on
    assert out.ken_burns_enabled is True
    assert out.ken_burns_intensity == "subtle"
    assert out.highlight_enabled is True
    assert out.color_look == "cinematic"
    # watermark gets the kit's logo + the template's policy
    assert out.watermark_path == "/static/storage/brand_kits/1/acme-logo.png"
    assert out.brand.watermark_opacity == pytest.approx(kit.watermark_opacity)


def test_brand_kit_subtitle_style_matches_palette():
    """BrandKit dataclass round-trips kit colours into ASS-format subtitle."""
    kit = BrandKit(
        primary_color="#0F2A4A",
        accent_color="#22D3B7",
        secondary_color="#F5F7FB",
        font_body="Inter",
    )
    style = kit.subtitle_style()
    # ASS encodes #RRGGBB as &HAABBGGRR; secondary_color #F5F7FB → &H00FBF7F5
    assert style.primary == "&H00FBF7F5"
    assert style.font == "Inter"


def test_brand_kit_from_orm_uses_workspace_defaults():
    """``BrandKit.from_orm`` survives a row with the new schema."""
    row = _fake_kit()
    kit = BrandKit.from_orm(row)
    assert kit.primary_color == "#101728"
    assert kit.accent_color == "#FF7849"
    assert kit.subtitle_size == 72
    assert kit.watermark_position == "tl"
    assert kit.logo_url == "/static/storage/brand_kits/1/acme.png"
