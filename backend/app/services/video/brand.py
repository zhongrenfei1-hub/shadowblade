"""Brand kit loader — provides colours, fonts, subtitle style.

The kit can come from the DB (BrandKit model), an inline dict, or the
fixtures fallback. This module hides the source — the pipeline just asks for
a :class:`BrandKit` and uses its fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.video.subtitle import SubtitleStyle


def _hex_to_ass(hex_color: str, alpha: int = 0) -> str:
    """Convert ``#RRGGBB`` (or ``#RRGGBBAA``) to ASS ``&HAABBGGRR``."""
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
    primary_color: str = "#0F2A4A"
    accent_color: str = "#22D3B7"
    secondary_color: str = "#F5F7FB"
    font_heading: str = "PingFang SC"
    font_body: str = "PingFang SC"
    voice_name: str = "alloy-en-female"
    target_lufs: float = -14.0
    target_tp: float = -1.0
    subtitle_size: int = 64
    subtitle_outline: float = 3.0
    subtitle_margin_v: int = 96
    watermark_opacity: float = 0.78
    watermark_position: str = "br"  # see WatermarkPosition values
    watermark_width_pct: float = 0.16
    extra: dict = field(default_factory=dict)

    def subtitle_style(self) -> SubtitleStyle:
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

    @classmethod
    def from_dict(cls, data: dict) -> "BrandKit":
        return cls(
            name=data.get("name", "ShadowBlade · Default"),
            primary_color=data.get("primary_color", "#0F2A4A"),
            accent_color=data.get("accent_color", "#22D3B7"),
            secondary_color=data.get("secondary_color", "#F5F7FB"),
            font_heading=data.get("font_heading", "PingFang SC"),
            font_body=data.get("font_body", "PingFang SC"),
            voice_name=data.get("voice", "alloy-en-female"),
            target_lufs=float(data.get("target_lufs", -14.0)),
            target_tp=float(data.get("target_tp", -1.0)),
            subtitle_size=int(data.get("subtitle_size", 64)),
            subtitle_outline=float(data.get("subtitle_outline", 3.0)),
            subtitle_margin_v=int(data.get("subtitle_margin_v", 96)),
            watermark_opacity=float(data.get("watermark_opacity", 0.78)),
            watermark_position=str(data.get("watermark_position", "br")),
            watermark_width_pct=float(data.get("watermark_width_pct", 0.16)),
            extra=data.get("extra", {}) or {},
        )


def default_kit() -> BrandKit:
    return BrandKit()


__all__ = ["BrandKit", "default_kit"]
