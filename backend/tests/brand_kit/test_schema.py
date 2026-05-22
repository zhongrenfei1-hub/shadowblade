"""Brand Kit Pydantic schema validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.brand_kit import (
    BrandKitBase,
    BrandKitCreate,
    BrandKitUpdate,
    validate_hex_color,
)


# --- hex colour helper ------------------------------------------------------


def test_hex_color_accepts_six_digit_uppercase():
    assert validate_hex_color("#0F2A4A") == "#0F2A4A"


def test_hex_color_canonicalises_lowercase_to_upper():
    assert validate_hex_color("#0f2a4a") == "#0F2A4A"


def test_hex_color_expands_short_form():
    assert validate_hex_color("#0F0") == "#00FF00"
    assert validate_hex_color("#abc") == "#AABBCC"


def test_hex_color_accepts_alpha_channel():
    assert validate_hex_color("#0F2A4A80") == "#0F2A4A80"


def test_hex_color_rejects_missing_hash():
    with pytest.raises(ValueError, match="invalid hex"):
        validate_hex_color("0F2A4A")


def test_hex_color_rejects_seven_digits():
    with pytest.raises(ValueError, match="invalid hex"):
        validate_hex_color("#0F2A4A1")


def test_hex_color_rejects_non_string():
    with pytest.raises(ValueError, match="must be a string"):
        validate_hex_color(0x0F2A4A)  # type: ignore[arg-type]


def test_hex_color_rejects_bad_characters():
    with pytest.raises(ValueError, match="invalid hex"):
        validate_hex_color("#GG00FF")


# --- BrandKitBase ------------------------------------------------------------


def test_base_defaults_match_dataclass_brand_kit():
    """The Pydantic defaults must agree with the dataclass BrandKit so the
    pipeline doesn't see two different 'no-op' baselines.
    """
    base = BrandKitBase()
    assert base.primary_color == "#0F2A4A"
    assert base.secondary_color == "#F5F7FB"
    assert base.accent_color == "#22D3B7"
    assert base.watermark_position == "br"
    assert base.watermark_opacity == pytest.approx(0.78)
    assert base.target_lufs == pytest.approx(-14.0)


def test_base_normalises_lowercase_colors():
    base = BrandKitBase(primary_color="#0f2a4a", accent_color="#22d3b7")
    assert base.primary_color == "#0F2A4A"
    assert base.accent_color == "#22D3B7"


def test_base_rejects_invalid_watermark_position():
    with pytest.raises(ValidationError):
        BrandKitBase(watermark_position="middle")  # type: ignore[arg-type]


def test_base_rejects_out_of_range_opacity():
    with pytest.raises(ValidationError):
        BrandKitBase(watermark_opacity=1.5)


def test_base_forbids_unknown_fields():
    """extra='forbid' protects the frontend from drifting schemas silently."""
    with pytest.raises(ValidationError):
        BrandKitBase(unknown_field="oops")  # type: ignore[call-arg]


def test_base_strips_whitespace_on_name():
    base = BrandKitBase(name="  Acme  ")
    assert base.name == "Acme"


def test_base_clamps_subtitle_size_range():
    BrandKitBase(subtitle_size=12)  # lower bound ok
    BrandKitBase(subtitle_size=200)  # upper bound ok
    with pytest.raises(ValidationError):
        BrandKitBase(subtitle_size=11)
    with pytest.raises(ValidationError):
        BrandKitBase(subtitle_size=201)


# --- BrandKitCreate ---------------------------------------------------------


def test_create_defaults_to_workspace_scope():
    payload = BrandKitCreate()
    assert payload.scope == "workspace"
    assert payload.owner_id is None
    assert payload.is_active is True


def test_create_with_user_scope_accepts_owner():
    payload = BrandKitCreate(scope="user", owner_id=42)
    assert payload.scope == "user"
    assert payload.owner_id == 42


def test_create_rejects_invalid_scope():
    with pytest.raises(ValidationError):
        BrandKitCreate(scope="org")  # type: ignore[arg-type]


# --- BrandKitUpdate ---------------------------------------------------------


def test_update_all_fields_optional():
    """The update schema must round-trip an empty body so the PUT endpoint
    can no-op when the caller only wants to bump ``updated_at``.
    """
    patch = BrandKitUpdate()
    assert patch.model_dump(exclude_unset=True) == {}


def test_update_canonicalises_hex_on_patch():
    patch = BrandKitUpdate(primary_color="#aabbcc")
    assert patch.primary_color == "#AABBCC"
    # Field not present in input shouldn't appear in the diff
    assert "secondary_color" not in patch.model_dump(exclude_unset=True)


def test_update_rejects_invalid_hex():
    with pytest.raises(ValidationError):
        BrandKitUpdate(primary_color="not a colour")


def test_update_keeps_only_set_keys():
    patch = BrandKitUpdate(name="New Name", target_lufs=-16.0)
    diff = patch.model_dump(exclude_unset=True)
    assert diff == {"name": "New Name", "target_lufs": -16.0}


def test_update_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        BrandKitUpdate(workspace_id=5)  # type: ignore[call-arg]


def test_update_validates_watermark_position_literal():
    BrandKitUpdate(watermark_position="tl")
    with pytest.raises(ValidationError):
        BrandKitUpdate(watermark_position="middle")  # type: ignore[arg-type]
