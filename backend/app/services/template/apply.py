"""Merge a Template — and optionally a stored Brand Kit — into a MixVideoRequest.

Policy — *user-explicit wins, then brand kit, then template, then defaults*:

1. The user's JSON payload is the ground truth. If a field appears in
   ``model_fields_set`` (Pydantic v2: present in the request body even
   if its value equals the default), we never overwrite it.
2. A workspace/user Brand Kit (from the DB) fills any remaining holes —
   palette, fonts, voice, watermark policy, default template.
3. The template fills whatever the brand kit left blank.
4. Anything still missing keeps its dataclass default.

This module is intentionally small and stateless so it can be unit
tested without spinning up FastAPI or ffmpeg.

Public functions:

* :func:`apply_template_to_request`   — Template only → MixVideoRequest
* :func:`apply_brand_kit_to_request`  — BrandKit only → MixVideoRequest
* :func:`apply_brand_and_template`    — both, in the correct precedence order
* :func:`apply_template_to_mix_request` — dataclass-level merge (CLI/tests)
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from app.services.template.schema import Template

if TYPE_CHECKING:  # pragma: no cover — import cycle avoidance
    from app.api.mix_video import BrandPayload, MixVideoRequest
    from app.services.video.pipeline import MixRequest

log = logging.getLogger("shadowblade.template.apply")


# Every BrandPayload field that has a matching attribute on the DB / dataclass
# BrandKit. Used by :func:`apply_brand_kit_to_request` to flow stored kit
# values into the per-request ``brand`` payload.
_BRAND_KIT_FIELDS: tuple[str, ...] = (
    "name",
    "primary_color",
    "accent_color",
    "secondary_color",
    "font_heading",
    "font_body",
    "target_lufs",
    "target_tp",
    "subtitle_size",
    "subtitle_margin_v",
    "watermark_opacity",
    "watermark_position",
    "watermark_width_pct",
    "bgm_gain_db",
    "voice_gain_db",
    "duck_threshold_db",
    "duck_ratio",
    "fade_in",
    "fade_out",
)


# Mapping: MixVideoRequest field name → (template group, template attribute)
_REQUEST_FIELD_MAP: dict[str, tuple[str, str]] = {
    "transition_style": ("transition", "style"),
    "max_transition": ("transition", "max_duration"),
    "preset": ("encode", "preset"),
    "color_look": ("color", "look"),
    "lut_path": ("color", "lut_path"),
    "auto_white_balance": ("color", "auto_white_balance"),
    "snap_to_beats": ("pacing", "snap_to_beats"),
    "target_lufs": ("audio", "target_lufs"),
    "adaptive_bgm_mix": ("audio", "adaptive_bgm_mix"),
    "watermark_position": ("watermark", "position"),
    "ken_burns_enabled": ("ken_burns", "enabled"),
    "ken_burns_intensity": ("ken_burns", "intensity"),
    "ken_burns_direction": ("ken_burns", "default_direction"),
    "ken_burns_max_zoom": ("ken_burns", "max_zoom"),
    "ken_burns_apply_to": ("ken_burns", "apply_to"),
    "cover_title_position": ("cover", "title_position"),
    "cover_title_max_chars": ("cover", "title_max_chars"),
    "cover_show_brand_strip": ("cover", "show_brand_strip"),
    "cover_brand_strip_color": ("cover", "brand_strip_color"),
    "cover_brand_strip_position": ("cover", "brand_strip_position"),
    "cover_brand_strip_width_pct": ("cover", "brand_strip_width_pct"),
    "highlight_enabled": ("highlight", "enabled"),
    "highlight_color": ("highlight", "color"),
    "highlight_bold": ("highlight", "weight_bold"),
    "highlight_underline": ("highlight", "underline_keywords"),
}


def _template_value(template: Template, group: str, attr: str) -> Any:
    grp = getattr(template, group, None)
    if grp is None:
        return None
    return getattr(grp, attr, None)


def apply_template_to_request(
    template: Template,
    body: "MixVideoRequest",
) -> "MixVideoRequest":
    """Return a new ``MixVideoRequest`` with template defaults applied.

    Fields the user did not include in their JSON body are filled from
    the template; everything else passes through unchanged.
    """
    user_set = body.model_fields_set
    data = body.model_dump()
    changed: list[str] = []

    for field, (group, attr) in _REQUEST_FIELD_MAP.items():
        if field in user_set:
            continue
        value = _template_value(template, group, attr)
        if value is None:
            continue
        data[field] = value
        changed.append(field)

    # Brand defaults: only seed brand fields when user didn't pass one
    if "brand" not in user_set or data.get("brand") is None:
        brand_seed = _brand_seed_from_template(template)
        if brand_seed:
            data["brand"] = brand_seed
            changed.append("brand")

    if changed:
        log.debug("template %s applied: filled %s", template.name, changed)

    # Defer the runtime import to keep this module test-friendly
    from app.api.mix_video import MixVideoRequest

    return MixVideoRequest.model_validate(data)


def _brand_seed_from_template(template: Template) -> dict | None:
    """Translate template subtitle/audio/watermark/extras groups into a
    BrandPayload-shaped dict. Returns ``None`` if there's nothing to seed.

    Mapping rules:
        subtitle.fill_color    → brand.secondary_color   (SubtitleStyle.primary)
        subtitle.outline_color → brand.primary_color     (SubtitleStyle.outline)
        subtitle.size_baseline → brand.subtitle_size
        subtitle.margin_v_baseline → brand.subtitle_margin_v
        audio.target_lufs/tp/gains/fade/duck → brand.<same name>
        watermark.opacity/width_pct/position → brand.watermark_*
        extras.brand_palette.primary/secondary/accent → brand.*_color
    """
    fields: dict[str, Any] = {}

    sub = template.subtitle
    if sub.size_baseline is not None:
        fields["subtitle_size"] = sub.size_baseline
    if sub.margin_v_baseline is not None:
        fields["subtitle_margin_v"] = sub.margin_v_baseline
    if sub.fill_color is not None:
        # Subtitle fill is rendered FROM brand.secondary_color in brand.subtitle_style()
        fields["secondary_color"] = sub.fill_color
    if sub.outline_color is not None:
        fields["primary_color"] = sub.outline_color

    aud = template.audio
    if aud.target_lufs is not None:
        fields["target_lufs"] = aud.target_lufs
    if aud.target_tp is not None:
        fields["target_tp"] = aud.target_tp
    if aud.bgm_gain_db is not None:
        fields["bgm_gain_db"] = aud.bgm_gain_db
    if aud.duck_threshold_db is not None:
        fields["duck_threshold_db"] = aud.duck_threshold_db
    if aud.duck_ratio is not None:
        fields["duck_ratio"] = aud.duck_ratio
    if aud.fade_in is not None:
        fields["fade_in"] = aud.fade_in
    if aud.fade_out is not None:
        fields["fade_out"] = aud.fade_out

    wm = template.watermark
    if wm.opacity is not None:
        fields["watermark_opacity"] = wm.opacity
    if wm.width_pct is not None:
        fields["watermark_width_pct"] = wm.width_pct
    if wm.position is not None:
        fields["watermark_position"] = wm.position

    # extras.brand_palette overrides ONLY where subtitle.{fill,outline}_color
    # did not already provide a value — explicit subtitle colours take
    # priority over the palette hint.
    palette = (template.extras or {}).get("brand_palette") or {}
    if isinstance(palette, dict):
        if palette.get("primary") and "primary_color" not in fields:
            fields["primary_color"] = palette["primary"]
        if palette.get("secondary") and "secondary_color" not in fields:
            fields["secondary_color"] = palette["secondary"]
        if palette.get("accent"):
            fields["accent_color"] = palette["accent"]

    return fields or None


def apply_template_to_mix_request(
    template: Template, request: "MixRequest"
) -> "MixRequest":
    """Same merge semantics but at the pipeline level — used by callers
    that construct ``MixRequest`` directly (CLI, tests). User-explicit
    detection is impossible at this layer so the template ONLY fills
    fields that still hold their dataclass default.

    For the API path, prefer :func:`apply_template_to_request` which has
    access to Pydantic's ``model_fields_set``.
    """
    from dataclasses import fields as dc_fields

    from app.services.video.pipeline import MixRequest

    defaults: dict[str, Any] = {}
    for f in dc_fields(MixRequest):
        if f.default is not f.default_factory and f.default is not None:
            defaults[f.name] = f.default

    template_fills: dict[str, Any] = {}
    for field, (group, attr) in _REQUEST_FIELD_MAP.items():
        # MixRequest uses the same field names as MixVideoRequest for these knobs
        if not hasattr(request, field):
            continue
        current = getattr(request, field)
        default = defaults.get(field, None)
        if current != default:
            continue  # user customised — leave alone
        value = _template_value(template, group, attr)
        if value is None:
            continue
        template_fills[field] = value

    if not template_fills:
        return request

    new = MixRequest(**{**request.__dict__, **template_fills})
    log.debug("template %s applied to MixRequest: %s", template.name, list(template_fills))
    return new


def _kit_value(kit: Any, attr: str) -> Any:
    """Read ``attr`` from either a dict or an object kit, returning ``None``
    when the attribute is absent or the value is empty.

    ORM rows expose ``voice`` while the dataclass uses ``voice_name``; we
    map the alias both ways so callers don't have to care which they got.
    """
    if isinstance(kit, dict):
        if attr in kit:
            return kit.get(attr)
        if attr == "voice_name":
            return kit.get("voice")
        return None
    if hasattr(kit, attr):
        return getattr(kit, attr)
    if attr == "voice_name" and hasattr(kit, "voice"):
        return getattr(kit, "voice")
    return None


def apply_brand_kit_to_request(
    brand_kit: Any,
    body: "MixVideoRequest",
) -> "MixVideoRequest":
    """Fold a stored Brand Kit into a MixVideoRequest.

    Policy:
        * Fields the user already supplied are never overwritten — we
          honour ``body.model_fields_set`` from Pydantic v2.
        * The ``brand`` payload is seeded with kit colours/fonts/audio/
          watermark knobs (only those the user did not pass).
        * ``watermark_path`` falls back to ``kit.logo_url``.
        * ``watermark_position`` falls back to ``kit.watermark_position``.
        * ``template`` (the name) is populated from
          ``kit.default_template_name`` so the user can omit it entirely.

    The kit can be either an ORM row (``app.models.brand_kit.BrandKit``)
    or a plain dict — :func:`_kit_value` handles both.

    Crucially we return a copy that only marks the *changed* fields as
    user-set, so a subsequent :func:`apply_template_to_request` can still
    overlay its defaults onto whatever the kit left untouched.
    """
    if brand_kit is None:
        return body

    user_set = body.model_fields_set
    update: dict[str, Any] = {}

    # ---- brand payload seed ---------------------------------------------
    if "brand" in user_set and body.brand is not None:
        # Start from the user's brand payload (it's already set), only fill
        # gaps the kit can cover.
        brand_seed: dict[str, Any] = body.brand.model_dump()
    else:
        brand_seed = {}

    for field in _BRAND_KIT_FIELDS:
        if field in brand_seed and brand_seed.get(field) is not None:
            continue  # already populated by user
        value = _kit_value(brand_kit, field)
        if value is None:
            continue
        brand_seed[field] = value

    if brand_seed:
        # Build the BrandPayload here (rather than via model_validate on the
        # whole request) so only ``brand`` is added to model_fields_set.
        from app.api.mix_video import BrandPayload

        update["brand"] = BrandPayload.model_validate(brand_seed)

    # ---- watermark_path: kit.logo_url is the default logo ---------------
    if "watermark_path" not in user_set and not body.watermark_path:
        logo = _kit_value(brand_kit, "logo_url")
        if logo:
            update["watermark_path"] = logo

    # ---- watermark_position: kit overrides only if user didn't set it --
    if "watermark_position" not in user_set:
        pos = _kit_value(brand_kit, "watermark_position")
        if pos and body.watermark_position == "br":
            update["watermark_position"] = pos

    # ---- template: pre-fill from kit.default_template_name --------------
    if "template" not in user_set and not body.template:
        default_tmpl = _kit_value(brand_kit, "default_template_name")
        if default_tmpl:
            update["template"] = default_tmpl

    if not update:
        return body

    log.debug("brand-kit applied: filled %s", list(update))
    # model_copy preserves the *original* model_fields_set and adds only the
    # keys in ``update`` — so downstream template merging still sees every
    # other field as "not user-set".
    return body.model_copy(update=update)


def apply_brand_and_template(
    *,
    brand_kit: Any | None,
    template: Template | None,
    body: "MixVideoRequest",
) -> "MixVideoRequest":
    """Combined entry point — brand kit first, then template.

    The order matters: applying the brand kit *first* means the template
    only fills holes the kit also left blank, and ``template`` itself
    (resolved from ``kit.default_template_name``) can be picked up by the
    caller before the template merge runs.
    """
    out = body
    if brand_kit is not None:
        out = apply_brand_kit_to_request(brand_kit, out)
    if template is not None:
        out = apply_template_to_request(template, out)
    return out


__all__ = [
    "apply_brand_kit_to_request",
    "apply_brand_and_template",
    "apply_template_to_mix_request",
    "apply_template_to_request",
]
