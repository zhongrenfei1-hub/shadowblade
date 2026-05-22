"""Apply: user-explicit-wins merge semantics."""

from __future__ import annotations

from app.api.mix_video import ClipPayload, MixVideoRequest
from app.services.template import apply_template_to_request
from app.services.template.schema import (
    Template,
    TemplateAudio,
    TemplateColor,
    TemplateEncode,
    TemplateTransition,
    TemplateWatermark,
)


def _minimal_body(**overrides) -> MixVideoRequest:
    base = {
        "project_id": 1,
        "clips": [{"path": "/tmp/a.mp4"}, {"path": "/tmp/b.mp4"}],
    }
    base.update(overrides)
    return MixVideoRequest.model_validate(base)


def _tmpl(**parts) -> Template:
    return Template(name="t", **parts)


def test_template_fills_field_user_omitted():
    body = _minimal_body()
    tmpl = _tmpl(transition=TemplateTransition(style="energetic", max_duration=0.6))
    out = apply_template_to_request(tmpl, body)
    assert out.transition_style == "energetic"
    assert out.max_transition == 0.6


def test_user_explicit_wins_over_template():
    body = _minimal_body(transition_style="calm")
    tmpl = _tmpl(transition=TemplateTransition(style="energetic"))
    out = apply_template_to_request(tmpl, body)
    assert out.transition_style == "calm"  # user wins


def test_user_explicit_matches_default_still_wins():
    # Even when the explicit value equals the dataclass default,
    # it must be treated as user-set — Pydantic's model_fields_set
    # is the source of truth.
    body = MixVideoRequest.model_validate(
        {
            "project_id": 1,
            "clips": [{"path": "/tmp/a.mp4"}],
            "transition_style": "editorial",  # explicit, equals default
        }
    )
    tmpl = _tmpl(transition=TemplateTransition(style="energetic"))
    out = apply_template_to_request(tmpl, body)
    assert out.transition_style == "editorial"


def test_none_template_field_does_not_overwrite():
    body = _minimal_body()
    tmpl = _tmpl(transition=TemplateTransition(style=None))  # nothing to fill
    out = apply_template_to_request(tmpl, body)
    # default carries through
    assert out.transition_style == body.transition_style


def test_brand_seeded_from_template_when_user_omits_brand():
    body = _minimal_body()
    tmpl = _tmpl(
        audio=TemplateAudio(target_lufs=-16.0),
        watermark=TemplateWatermark(opacity=0.5, width_pct=0.2, position="tr"),
    )
    out = apply_template_to_request(tmpl, body)
    assert out.brand is not None
    assert out.brand.target_lufs == -16.0
    assert out.brand.watermark_opacity == 0.5
    assert out.brand.watermark_width_pct == 0.2
    assert out.brand.watermark_position == "tr"


def test_brand_seed_skipped_when_user_passed_brand():
    body = _minimal_body(brand={"primary_color": "#000000"})
    tmpl = _tmpl(audio=TemplateAudio(target_lufs=-16.0))
    out = apply_template_to_request(tmpl, body)
    assert out.brand is not None
    assert out.brand.primary_color == "#000000"
    # Template's audio.target_lufs not folded into the user-supplied brand
    assert out.brand.target_lufs is None


def test_color_and_encode_groups_apply():
    body = _minimal_body()
    tmpl = _tmpl(
        color=TemplateColor(look="warm", auto_white_balance=True),
        encode=TemplateEncode(preset="social_16x9"),
    )
    out = apply_template_to_request(tmpl, body)
    assert out.color_look == "warm"
    assert out.auto_white_balance is True
    assert out.preset == "social_16x9"
