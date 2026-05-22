"""Brand Kit — Pydantic V2 request/response schemas.

The validation rules captured here are the single source of truth for both
the REST API and the mix-video pipeline. They mirror the ORM model in
:mod:`app.models.brand_kit` field-for-field but add:

* hex-colour validation (``#RGB``, ``#RRGGBB``, ``#RRGGBBAA`` — all
  normalised to upper-case ``#RRGGBB`` / ``#RRGGBBAA``);
* enum-like ``Literal`` types for ``scope`` and ``watermark_position``;
* sensible ``ge`` / ``le`` ranges for the numeric audio / subtitle /
  watermark knobs (matching the template-schema bounds so the two layers
  stay consistent);
* defensive trimming of strings (``name``, ``custom_css_snippet``);
* a ``from_attributes`` mode on ``BrandKitRead`` so we can ``model_validate``
  straight from the SQLAlchemy row.

The four-class layout — ``Base / Create / Update / Read`` — follows the
fastapi-fullstack-template convention so frontends can predict the shape
of every endpoint.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- shared helpers ---------------------------------------------------------

_HEX_RE = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def validate_hex_color(value: str) -> str:
    """Canonicalise a hex colour string.

    Accepts ``#RGB``, ``#RRGGBB``, or ``#RRGGBBAA`` (case-insensitive).
    Returns an upper-cased ``#RRGGBB`` / ``#RRGGBBAA``. Short form is
    expanded to long form (``#0F0`` → ``#00FF00``).

    Raises
    ------
    ValueError
        If the string is not a valid hex colour.
    """
    if not isinstance(value, str):
        raise ValueError("hex colour must be a string")
    v = value.strip()
    if not _HEX_RE.match(v):
        raise ValueError(
            f"invalid hex colour {value!r}; expected #RGB, #RRGGBB or #RRGGBBAA"
        )
    body = v[1:]
    if len(body) == 3:  # expand #RGB → #RRGGBB
        body = "".join(ch * 2 for ch in body)
    return "#" + body.upper()


# Reusable hex-colour annotated type — Pydantic runs the validator before
# the model assignment, so every field that uses this type is guaranteed
# to be a canonical upper-case hex string.
HexColor = Annotated[
    str,
    Field(min_length=4, max_length=9, description="Hex colour like #0F2A4A."),
]


WatermarkPosition = Literal["tl", "tr", "bl", "br", "bc", "center"]
BrandKitScope = Literal["workspace", "user"]


# --- shared base ------------------------------------------------------------


class BrandKitBase(BaseModel):
    """Fields shared by *Create* / *Update* / *Read*.

    All keys are optional on ``Update`` and have defaults on ``Create``
    so the API contract matches the ORM defaults exactly.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    name: str = Field(default="ShadowBlade · Default", min_length=1, max_length=255)

    # palette
    primary_color: HexColor = "#0F2A4A"
    secondary_color: HexColor = "#F5F7FB"
    accent_color: HexColor = "#22D3B7"
    neutral_color: HexColor = "#5A6B85"
    background_color: HexColor = "#FFFFFF"

    # typography
    font_family: str = Field(default="Inter", min_length=1, max_length=128)
    font_heading: str = Field(default="Inter", min_length=1, max_length=128)
    font_body: str = Field(default="Inter", min_length=1, max_length=128)

    # assets
    logo_url: str | None = Field(default=None, max_length=512)
    logo_mono_url: str | None = Field(default=None, max_length=512)
    intro_url: str | None = Field(default=None, max_length=512)
    outro_url: str | None = Field(default=None, max_length=512)

    # watermark
    watermark_text: str | None = Field(default=None, max_length=64)
    watermark_opacity: float = Field(default=0.78, ge=0.0, le=1.0)
    watermark_position: WatermarkPosition = "br"
    watermark_width_pct: float = Field(default=0.16, ge=0.01, le=0.6)

    # audio bus
    voice: str = Field(default="alloy-en-female", min_length=1, max_length=64)
    target_lufs: float = Field(default=-14.0, ge=-32.0, le=-6.0)
    target_tp: float = Field(default=-1.0, ge=-9.0, le=0.0)
    bgm_gain_db: float = Field(default=-14.0, ge=-40.0, le=12.0)

    # subtitle baseline (1080p)
    subtitle_size: int = Field(default=64, ge=12, le=200)
    subtitle_margin_v: int = Field(default=96, ge=0, le=600)

    # defaults
    default_template_name: str | None = Field(default=None, max_length=64)
    custom_css_snippet: str | None = Field(default=None, max_length=8000)

    # tone (editorial guidance — schema-less)
    tone: dict = Field(default_factory=dict)

    # ------ validators ------------------------------------------------------

    @field_validator(
        "primary_color",
        "secondary_color",
        "accent_color",
        "neutral_color",
        "background_color",
        mode="before",
    )
    @classmethod
    def _coerce_hex(cls, v: object) -> str:
        return validate_hex_color(v) if v is not None else v  # type: ignore[arg-type]


# --- create -----------------------------------------------------------------


class BrandKitCreate(BrandKitBase):
    """Body shape for ``POST /brand-kits`` (workspace-admin only).

    ``scope`` defaults to ``'workspace'``; pass ``'user'`` plus ``owner_id``
    to create a per-member override. ``is_active`` flags the kit as the
    effective default for its (scope, owner) tuple.
    """

    scope: BrandKitScope = "workspace"
    owner_id: int | None = None
    is_active: bool = True


# --- update -----------------------------------------------------------------


class BrandKitUpdate(BaseModel):
    """PATCH-style update — every field is optional.

    A field set to ``None`` is interpreted as *leave unchanged* (we use
    ``model_dump(exclude_unset=True)`` server-side so only the keys the
    client explicitly sent are written back).
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str | None = Field(default=None, min_length=1, max_length=255)

    primary_color: HexColor | None = None
    secondary_color: HexColor | None = None
    accent_color: HexColor | None = None
    neutral_color: HexColor | None = None
    background_color: HexColor | None = None

    font_family: str | None = Field(default=None, min_length=1, max_length=128)
    font_heading: str | None = Field(default=None, min_length=1, max_length=128)
    font_body: str | None = Field(default=None, min_length=1, max_length=128)

    logo_url: str | None = Field(default=None, max_length=512)
    logo_mono_url: str | None = Field(default=None, max_length=512)
    intro_url: str | None = Field(default=None, max_length=512)
    outro_url: str | None = Field(default=None, max_length=512)

    watermark_text: str | None = Field(default=None, max_length=64)
    watermark_opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    watermark_position: WatermarkPosition | None = None
    watermark_width_pct: float | None = Field(default=None, ge=0.01, le=0.6)

    voice: str | None = Field(default=None, min_length=1, max_length=64)
    target_lufs: float | None = Field(default=None, ge=-32.0, le=-6.0)
    target_tp: float | None = Field(default=None, ge=-9.0, le=0.0)
    bgm_gain_db: float | None = Field(default=None, ge=-40.0, le=12.0)

    subtitle_size: int | None = Field(default=None, ge=12, le=200)
    subtitle_margin_v: int | None = Field(default=None, ge=0, le=600)

    default_template_name: str | None = Field(default=None, max_length=64)
    custom_css_snippet: str | None = Field(default=None, max_length=8000)

    tone: dict | None = None
    is_active: bool | None = None

    @field_validator(
        "primary_color",
        "secondary_color",
        "accent_color",
        "neutral_color",
        "background_color",
        mode="before",
    )
    @classmethod
    def _coerce_hex(cls, v: object) -> object:
        if v is None:
            return None
        return validate_hex_color(v)  # type: ignore[arg-type]


# --- read -------------------------------------------------------------------


class BrandKitRead(BrandKitBase):
    """Wire shape for GET responses — includes server-managed fields."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,  # accept ORM instances directly
        str_strip_whitespace=True,
    )

    id: int
    workspace_id: int
    scope: BrandKitScope
    owner_id: int | None = None
    is_active: bool = True
    created_at: object | None = None  # datetime — kept loose for JSON round-trip
    updated_at: object | None = None


# --- logo upload ------------------------------------------------------------


class BrandKitLogoResponse(BaseModel):
    """Returned by ``POST /brand-kit/logo``.

    ``url`` is the public URL (already pre-pended with the static mount
    prefix) the frontend can drop straight into an ``<img>`` tag.
    ``bytes`` lets the UI display a size before re-fetching.
    """

    url: str
    bytes: int
    content_type: str
    width: int | None = None
    height: int | None = None


__all__ = [
    "BrandKitBase",
    "BrandKitCreate",
    "BrandKitLogoResponse",
    "BrandKitRead",
    "BrandKitScope",
    "BrandKitUpdate",
    "HexColor",
    "WatermarkPosition",
    "validate_hex_color",
]
