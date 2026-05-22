"""Brand kit loader — palette, fonts, watermark/audio/subtitle defaults.

The pipeline only ever sees this dataclass. Three loaders convert from the
caller-friendly shapes:

* :meth:`BrandKit.from_dict`    — JSON body / brand payload
* :meth:`BrandKit.from_orm`     — DB row (``app.models.brand_kit.BrandKit``)
* :func:`default_kit`           — process-wide fallback

A ``BrandKit`` is intentionally *flat* (no nested groups). Every field
maps directly to one knob on ``MixRequest``, ``AudioBus``, ``WatermarkSpec``
or ``SubtitleStyle`` — the indirection happens in
:func:`app.services.template.apply.apply_brand_kit_to_request`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.video.subtitle import SubtitleStyle


def _hex_to_ass(hex_color: str, alpha: int = 0) -> str:
    """Convert ``#RRGGBB`` (or ``#RRGGBBAA``) to ASS ``&HAABBGGRR``.

    The ASS subtitle format encodes colours as ``&HAABBGGRR`` — note the
    *alpha-first, byte-reversed* order. We accept either 6-digit or 8-digit
    hex strings; if the input lacks alpha, the caller's ``alpha`` argument
    is used (0 = fully opaque).
    """
    h = hex_color.lstrip("#")
    if len(h) == 8:
        r, g, b, a = h[0:2], h[2:4], h[4:6], h[6:8]
    elif len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        a = f"{alpha:02X}"
    else:
        return "&H00FFFFFF"
    return f"&H{a.upper()}{b.upper()}{g.upper()}{r.upper()}"


@dataclass(slots=True)
class BrandKit:
    name: str = "ShadowBlade · Default"

    # palette
    primary_color: str = "#0F2A4A"
    accent_color: str = "#22D3B7"
    secondary_color: str = "#F5F7FB"
    neutral_color: str = "#5A6B85"
    background_color: str = "#FFFFFF"

    # typography
    font_heading: str = "PingFang SC"
    font_body: str = "PingFang SC"

    # audio bus
    voice_name: str = "alloy-en-female"
    target_lufs: float = -14.0
    target_tp: float = -1.0
    bgm_gain_db: float = -14.0
    voice_gain_db: float = 0.0
    duck_threshold_db: float = -28.0
    duck_ratio: float = 8.0
    fade_in: float = 0.4
    fade_out: float = 0.6

    # subtitle baseline (1080p)
    subtitle_size: int = 64
    subtitle_outline: float = 3.0
    subtitle_margin_v: int = 96

    # watermark — see WatermarkPosition for allowed positions
    watermark_text: str | None = None
    watermark_opacity: float = 0.78
    watermark_position: str = "br"
    watermark_width_pct: float = 0.16

    # logos & intros/outros
    logo_url: str | None = None
    logo_mono_url: str | None = None
    intro_url: str | None = None
    outro_url: str | None = None

    # defaults for the mix-video request
    default_template_name: str | None = None
    custom_css_snippet: str | None = None

    extra: dict = field(default_factory=dict)

    # ------ derived helpers -------------------------------------------------

    def subtitle_style(self) -> SubtitleStyle:
        """Convert the brand palette into an ASS-ready ``SubtitleStyle``."""
        return SubtitleStyle(
            font=self.font_body,
            size=self.subtitle_size,
            primary=_hex_to_ass(self.secondary_color),
            secondary=_hex_to_ass(self.accent_color),
            outline_color=_hex_to_ass(self.primary_color, alpha=0x40),
            back_color=_hex_to_ass(self.primary_color, alpha=0x80),
            outline=self.subtitle_outline,
            margin_v=self.subtitle_margin_v,
        )

    # ------ loaders ---------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandKit":
        """Build a kit from a plain dict (API body, fixtures, JSON file).

        Unknown keys land in ``extra`` so callers can persist whatever they
        like alongside the canonical fields without a schema migration.
        Aliases (``voice`` ↔ ``voice_name``) are normalised for ergonomics.
        """
        known = {
            "name",
            "primary_color",
            "accent_color",
            "secondary_color",
            "neutral_color",
            "background_color",
            "font_heading",
            "font_body",
            "voice_name",
            "target_lufs",
            "target_tp",
            "bgm_gain_db",
            "voice_gain_db",
            "duck_threshold_db",
            "duck_ratio",
            "fade_in",
            "fade_out",
            "subtitle_size",
            "subtitle_outline",
            "subtitle_margin_v",
            "watermark_text",
            "watermark_opacity",
            "watermark_position",
            "watermark_width_pct",
            "logo_url",
            "logo_mono_url",
            "intro_url",
            "outro_url",
            "default_template_name",
            "custom_css_snippet",
        }
        # ``voice`` is the ORM/API field name; ``voice_name`` is the
        # internal dataclass name. Map across.
        d = dict(data)
        if "voice" in d and "voice_name" not in d:
            d["voice_name"] = d.pop("voice")
        extras_in = d.pop("extra", None) or {}
        kit_args: dict[str, Any] = {}
        for key in known:
            if key in d and d[key] is not None:
                kit_args[key] = d[key]
        # Everything else is preserved in ``extra``.
        leftover = {k: v for k, v in d.items() if k not in known and v is not None}
        merged_extras = {**leftover, **extras_in}
        return cls(**kit_args, extra=merged_extras)

    @classmethod
    def from_orm(cls, row: Any) -> "BrandKit":
        """Build a kit from a SQLAlchemy ``BrandKit`` row.

        The ORM uses ``font_family`` to mean *both* heading and body when
        only one is specified — but the dataclass keeps the split. We
        fall back to ``font_family`` for either side that's missing.
        """
        font_family = getattr(row, "font_family", None) or "Inter"
        return cls(
            name=row.name,
            primary_color=row.primary_color,
            secondary_color=getattr(row, "secondary_color", "#F5F7FB"),
            accent_color=row.accent_color,
            neutral_color=getattr(row, "neutral_color", "#5A6B85"),
            background_color=getattr(row, "background_color", "#FFFFFF"),
            font_heading=getattr(row, "font_heading", None) or font_family,
            font_body=getattr(row, "font_body", None) or font_family,
            voice_name=getattr(row, "voice", "alloy-en-female"),
            target_lufs=float(getattr(row, "target_lufs", -14.0)),
            target_tp=float(getattr(row, "target_tp", -1.0)),
            bgm_gain_db=float(getattr(row, "bgm_gain_db", -14.0)),
            subtitle_size=int(getattr(row, "subtitle_size", 64)),
            subtitle_margin_v=int(getattr(row, "subtitle_margin_v", 96)),
            watermark_text=getattr(row, "watermark_text", None),
            watermark_opacity=float(getattr(row, "watermark_opacity", 0.78)),
            watermark_position=getattr(row, "watermark_position", "br"),
            watermark_width_pct=float(getattr(row, "watermark_width_pct", 0.16)),
            logo_url=getattr(row, "logo_url", None),
            logo_mono_url=getattr(row, "logo_mono_url", None),
            intro_url=getattr(row, "intro_url", None),
            outro_url=getattr(row, "outro_url", None),
            default_template_name=getattr(row, "default_template_name", None),
            custom_css_snippet=getattr(row, "custom_css_snippet", None),
            extra=dict(getattr(row, "tone", None) or {}),
        )


def default_kit() -> BrandKit:
    return BrandKit()


__all__ = ["BrandKit", "default_kit", "_hex_to_ass"]
