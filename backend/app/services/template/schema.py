"""Template schema — eight feature groups, all optional, JSON-friendly.

Every field is **optional** by design: a template only overrides defaults
where it is opinionated. The apply layer treats ``None`` as "don't
touch" so users can compose templates by partial override.

The eight groups mirror the mix-video pipeline subsystems:

============== ===========================================================
Group          What the pipeline reads
============== ===========================================================
transition     ``MixRequest.transition_style``, ``max_transition``
subtitle       ``segment_utterances`` + ``BrandKit.subtitle_style`` policy
pacing         ``selector.select_clips`` + ``snap_to_beats``
audio          ``AudioBus`` (LUFS, ducking, fades) + ``adaptive_bgm_mix``
cover          ``CoverSpec`` + cover timestamp strategy
watermark      ``WatermarkSpec`` (position/opacity/width)
color          ``compose_color_chain`` (look / LUT / auto-WB)
encode         ``encoder.PRESETS`` (aspect + bitrate)
============== ===========================================================

The schema also carries lightweight metadata (``name``, ``version``,
``extends``, ``description``, ``tags``) and a free-form ``extras``
escape hatch so future pipeline features can be templated without a
schema migration.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- groups -----------------------------------------------------------------


class TemplateTransition(BaseModel):
    """Cross-shot transition policy."""

    model_config = ConfigDict(extra="forbid")

    style: Literal["editorial", "energetic", "calm"] | None = Field(
        default=None,
        description="Style hint consumed by transitions.select_transition.",
    )
    max_duration: float | None = Field(
        default=None,
        ge=0.05,
        le=2.0,
        description="Hard ceiling on any individual transition (seconds).",
    )


class TemplateSubtitle(BaseModel):
    """Burn-in subtitle policy. Brand colours/font come from BrandKit."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = Field(default=None, description="Burn subtitles into the video.")
    max_chars_per_line: int | None = Field(default=None, ge=8, le=80)
    max_lines: int | None = Field(default=None, ge=1, le=4)
    cps_warn: float | None = Field(default=None, ge=4.0, le=40.0)
    cps_fail: float | None = Field(default=None, ge=4.0, le=60.0)
    size_baseline: int | None = Field(
        default=None,
        ge=12,
        le=200,
        description="Font size before per-preset scaling (baseline = 1920p).",
    )
    margin_v_baseline: int | None = Field(default=None, ge=0, le=600)
    fill_color: str | None = Field(default=None, description="Hex like #FFFFFF.")
    outline_color: str | None = Field(default=None, description="Hex like #000000.")


class TemplatePacing(BaseModel):
    """Selector + beat-snap rules — drives shot length and BGM sync."""

    model_config = ConfigDict(extra="forbid")

    target_shot: float | None = Field(default=None, ge=0.3, le=20.0)
    min_shot: float | None = Field(default=None, ge=0.2, le=20.0)
    max_shot: float | None = Field(default=None, ge=0.4, le=30.0)
    snap_to_beats: bool | None = None
    must_include_hero: bool | None = None


class TemplateAudio(BaseModel):
    """Voice/BGM mixing policy. Maps to AudioBus + adaptive ducking."""

    model_config = ConfigDict(extra="forbid")

    target_lufs: float | None = Field(default=None, ge=-32.0, le=-6.0)
    target_tp: float | None = Field(default=None, ge=-9.0, le=0.0)
    adaptive_bgm_mix: bool | None = None
    bgm_gain_db: float | None = Field(default=None, ge=-40.0, le=12.0)
    duck_threshold_db: float | None = Field(default=None, ge=-60.0, le=0.0)
    duck_ratio: float | None = Field(default=None, ge=1.0, le=40.0)
    fade_in: float | None = Field(default=None, ge=0.0, le=10.0)
    fade_out: float | None = Field(default=None, ge=0.0, le=10.0)


class TemplateCover(BaseModel):
    """Cover image generation strategy + layout."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    style: Literal["gradient", "photo", "minimal"] | None = None
    title_required: bool | None = None
    timestamp_strategy: Literal["hero", "first", "mid", "manual"] | None = None

    # Layout knobs — picked up by covers.generate_cover via CoverSpec
    title_position: Literal[
        "bottom-center", "center", "left-center", "right-center", "top-left"
    ] | None = None
    title_max_chars: int | None = Field(default=None, ge=4, le=120)
    show_brand_strip: bool | None = None
    brand_strip_color: str | None = Field(
        default=None, description="Hex like #0F2A4A; defaults to brand primary."
    )
    brand_strip_position: Literal["left", "right", "top", "bottom"] | None = None
    brand_strip_width_pct: float | None = Field(default=None, ge=0.01, le=0.2)


class TemplateWatermark(BaseModel):
    """Logo overlay rules."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    position: Literal["tl", "tr", "bl", "br", "center"] | None = None
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    width_pct: float | None = Field(default=None, ge=0.01, le=0.6)
    require_logo: bool | None = Field(
        default=None,
        description="If true, mixing fails without a watermark_path or brand logo.",
    )


class TemplateColor(BaseModel):
    """Colour grade — preset, LUT, white-balance."""

    model_config = ConfigDict(extra="forbid")

    look: Literal[
        "natural", "warm", "cool", "cinematic", "punchy", "mono", "vintage"
    ] | None = None
    lut_path: str | None = None
    auto_white_balance: bool | None = None


class TemplateEncode(BaseModel):
    """Encoder preset (aspect + bitrate)."""

    model_config = ConfigDict(extra="forbid")

    preset: str | None = Field(
        default=None,
        description="Encoder preset name; must exist in encoder.PRESETS.",
    )


class TemplateHighlight(BaseModel):
    """Keyword highlight inside burn-in subtitles.

    User syntax in cue text: ``[关键词]`` → rendered in
    ``color`` (青绿 by default). PNG + ASS paths both supported.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    color: str | None = Field(default=None, description="Hex like #22D3B7.")
    weight_bold: bool | None = Field(
        default=None, description="Render highlighted words with heavier stroke."
    )
    underline_keywords: bool | None = Field(
        default=None, description="Draw an underline beneath highlighted segments."
    )


class TemplateVoice(BaseModel):
    """Theme-driven TTS personality.

    The same script sounds different in a marketing promo vs. a training
    explainer vs. a dance vlog. This group lets a template say *"render
    voiceover with the 'marketing' personality"* and have the TTS engine
    pick voice / rate / pitch accordingly.

    Resolution chain at runtime (highest-priority first):
        1. explicit ``voice`` / ``rate`` / ``pitch`` in the request body
        2. this template's ``voice`` / ``rate`` / ``pitch`` fields
        3. this template's ``intent`` (→ THEME_VOICE_STYLES lookup)
        4. detected scenario's ``voice_intent`` (script_generator)
        5. default preset
    """

    model_config = ConfigDict(extra="forbid")

    intent: Literal[
        "marketing",
        "product_demo",
        "training",
        "tutorial",
        "dance",
        "social",
        "game",
        "news",
        "lyrical",
        "customerservice",
        "energetic",
        "professional",
        "warm",
        "intellectual",
        "youthful",
        "calm",
        "default",
    ] | None = Field(
        default=None,
        description="High-level theme label — resolves to a VoiceStyle preset.",
    )
    voice: str | None = Field(
        default=None,
        description="Voice alias from EDGE_TTS_VOICES, e.g. 'xiaoxiao-zh-f', "
        "or a full Microsoft voice id. Overrides whatever ``intent`` picks.",
    )
    rate: str | None = Field(
        default=None,
        description="edge-tts rate string, e.g. '+12%', '-8%', '+0%'.",
    )
    pitch: str | None = Field(
        default=None,
        description="edge-tts pitch string, e.g. '+5Hz', '-3Hz', '+0Hz'.",
    )


class TemplateKenBurns(BaseModel):
    """Slow zoom/pan animation applied per clip.

    ``intensity`` is the canonical knob:
        - subtle  → max_zoom 1.08
        - medium  → max_zoom 1.18
        - strong  → max_zoom 1.30
    ``max_zoom`` overrides the intensity-derived value when provided.

    ``default_direction`` controls which built-in mode to use:
        - ``in`` / ``out`` / ``pan_left`` / ``pan_right`` — explicit
        - ``auto`` — alternate IN → PAN_RIGHT → OUT → PAN_LEFT by index
                     (see :func:`ken_burns.auto_mode`)

    ``apply_to`` decides which clips receive the effect:
        - ``all``        — every clip
        - ``low_motion`` — only clips with ``motion < 0.35`` (so high-motion
                           footage is left alone)
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    intensity: Literal["subtle", "medium", "strong"] | None = None
    default_direction: Literal["in", "out", "pan_left", "pan_right", "auto"] | None = None
    max_zoom: float | None = Field(default=None, ge=1.0, le=2.0)
    apply_to: Literal["all", "low_motion"] | None = None


# --- root document ----------------------------------------------------------


class Template(BaseModel):
    """A versioned, declarative rule set for mix-video."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=64, description="Unique slug.")
    version: str = Field(default="1.0.0", description="Semver-ish, for diagnostics.")
    description: str = Field(default="", max_length=400)
    extends: str | None = Field(
        default=None,
        description="Parent template slug; this template overlays on top.",
    )
    tags: list[str] = Field(default_factory=list, max_length=16)

    transition: TemplateTransition = Field(default_factory=TemplateTransition)
    subtitle: TemplateSubtitle = Field(default_factory=TemplateSubtitle)
    pacing: TemplatePacing = Field(default_factory=TemplatePacing)
    audio: TemplateAudio = Field(default_factory=TemplateAudio)
    cover: TemplateCover = Field(default_factory=TemplateCover)
    watermark: TemplateWatermark = Field(default_factory=TemplateWatermark)
    color: TemplateColor = Field(default_factory=TemplateColor)
    encode: TemplateEncode = Field(default_factory=TemplateEncode)
    ken_burns: TemplateKenBurns = Field(default_factory=TemplateKenBurns)
    highlight: TemplateHighlight = Field(default_factory=TemplateHighlight)
    voice: TemplateVoice = Field(default_factory=TemplateVoice)

    extras: dict[str, object] = Field(
        default_factory=dict,
        description="Free-form bag for future pipeline knobs (no validation).",
    )

    def merged_with(self, child: "Template") -> "Template":
        """Return a new Template = ``self`` overlaid by ``child``.

        Child fields that are ``None`` keep the parent's value. Used by
        the loader to resolve ``extends``.
        """
        parent_data = self.model_dump()
        child_data = child.model_dump()

        merged = dict(parent_data)
        # Group-level merge: any non-None field on the child wins.
        for group_name in (
            "transition",
            "subtitle",
            "pacing",
            "audio",
            "cover",
            "watermark",
            "color",
            "encode",
            "ken_burns",
            "highlight",
            "voice",
        ):
            parent_group = parent_data.get(group_name) or {}
            child_group = child_data.get(group_name) or {}
            out = dict(parent_group)
            for k, v in child_group.items():
                if v is not None:
                    out[k] = v
            merged[group_name] = out

        # Metadata: child wins for name/version/description/tags/extras
        merged["name"] = child_data["name"]
        merged["version"] = child_data.get("version") or parent_data.get("version", "1.0.0")
        merged["description"] = child_data.get("description") or parent_data.get(
            "description", ""
        )
        merged["extends"] = None  # already resolved
        merged["tags"] = list(dict.fromkeys(parent_data.get("tags", []) + child_data.get("tags", [])))
        merged["extras"] = {**parent_data.get("extras", {}), **child_data.get("extras", {})}

        return Template.model_validate(merged)


__all__ = [
    "Template",
    "TemplateTransition",
    "TemplateSubtitle",
    "TemplatePacing",
    "TemplateAudio",
    "TemplateCover",
    "TemplateWatermark",
    "TemplateColor",
    "TemplateEncode",
    "TemplateKenBurns",
    "TemplateHighlight",
    "TemplateVoice",
]
