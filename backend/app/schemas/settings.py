"""Settings — Pydantic V2 request/response schemas.

Three sibling families mirror the ORM tables in
:mod:`app.models.settings`:

* :class:`UserProfileSettingsBase` / *Update* / *Read* — personal prefs.
* :class:`OrganizationSettingsBase` / *Update* / *Read* — workspace defaults.
* :class:`AppSettingCreate` / *Update* / *Read* — KV global settings.

The four-class layout (Base + Create + Update + Read) matches the
``BrandKit`` schemas so the frontend can predict shapes consistently.
``OrganizationSettings`` has no public *Create* class because the row is
auto-materialised on first read — clients only ever PATCH.

Validation rules captured here:

* IETF BCP 47 language tags via a regex (e.g. ``zh-CN``, ``en-US``, ``zh``).
* IANA timezone names checked with :mod:`zoneinfo`.
* ``Literal`` enums for ``theme`` / ``date_format`` / ``inbox_digest`` /
  ``default_codec`` / ``default_aspect_ratio`` / etc.
* ``ge``/``le`` ranges for ``session_duration_hours``, ``retention_days``,
  ``default_loudness_lufs`` (mirroring brand kit bounds for consistency).
* IP allowlist entries validated as CIDR-or-IP strings.
* ``notification_preferences`` keys must be a subset of
  :data:`app.models.notification.NOTIFICATION_CATEGORIES`.

Errors raised through Pydantic produce the standard FastAPI 422 envelope —
no custom error handler is required.
"""

from __future__ import annotations

import re
from ipaddress import ip_address, ip_network
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import NOTIFICATION_CATEGORIES

# --- shared helpers ---------------------------------------------------------

# IETF BCP 47 — language[-script][-region]. The region part is optional so
# bare ``zh`` is accepted as well as ``zh-CN``. Script subtags are rare in
# our UI translations so we don't whitelist them — the regex is permissive
# enough to pass any plausible tag without inviting injection.
_BCP47_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z]{2,4}){0,2}$")

# Whitelisted timezone set is computed once at import. ``available_timezones``
# scans the tzdata bundled with the Python runtime, so the check works in
# every deploy without a network call.
_TIMEZONES: frozenset[str] = frozenset(available_timezones())


def _canonical_language(value: str) -> str:
    """Canonicalise a BCP 47 tag: ``en-us`` → ``en-US``, ``zh`` stays ``zh``.

    Splits on ``-``, lowercases the first subtag, uppercases the second
    (region), and leaves the third (variant) alone. This mirrors the
    casing convention every i18n library expects.
    """
    if not isinstance(value, str):
        raise ValueError("language must be a string")
    v = value.strip()
    if not _BCP47_RE.match(v):
        raise ValueError(
            f"invalid language tag {value!r}; expected BCP 47 (e.g. 'zh-CN')"
        )
    parts = v.split("-")
    parts[0] = parts[0].lower()
    if len(parts) >= 2:
        parts[1] = parts[1].upper()
    return "-".join(parts)


def _validate_timezone(value: str) -> str:
    """Ensure ``value`` is a known IANA timezone (e.g. ``Asia/Shanghai``).

    Raises plain :class:`ValueError` so the failure bubbles through Pydantic
    as a regular 422 — ``ZoneInfoNotFoundError`` inherits from KeyError and
    would otherwise escape the validation envelope.
    """
    if not isinstance(value, str):
        raise ValueError("timezone must be a string")
    v = value.strip()
    if v not in _TIMEZONES:
        raise ValueError(f"unknown timezone {value!r}")
    return v


def _validate_cidr_or_ip(value: str) -> str:
    """Accept either ``10.0.0.0/8`` or a bare ``10.0.0.42`` string.

    Bare IPs are widened to ``/32`` (IPv4) or ``/128`` (IPv6) by the
    application layer; here we only validate the syntax so the schema
    keeps round-tripping the user's original input.
    """
    if not isinstance(value, str):
        raise ValueError("ip allowlist entry must be a string")
    v = value.strip()
    try:
        if "/" in v:
            ip_network(v, strict=False)
        else:
            ip_address(v)
    except ValueError as exc:
        raise ValueError(f"invalid CIDR / IP {value!r}: {exc}") from exc
    return v


# --- shared literal aliases -------------------------------------------------

Theme = Literal["system", "light", "dark"]
DateFormat = Literal["iso", "us", "eu"]
InboxDigest = Literal["off", "daily", "weekly"]
VideoCodec = Literal["h264", "h265", "prores_422_hq"]
AspectRatio = Literal["9:16", "16:9", "1:1", "4:5"]


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------


class UserProfileSettingsBase(BaseModel):
    """Fields shared by *Update* / *Read*.

    Defaults mirror :class:`app.models.settings.UserProfileSettings` so
    the API contract and the DB defaults stay in lock-step.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=512)
    bio: str | None = Field(default=None, max_length=2000)

    language: str = Field(default="zh-CN", max_length=16)
    timezone: str = Field(default="Asia/Shanghai", max_length=48)
    date_format: DateFormat = "iso"
    theme: Theme = "system"

    email_notifications_enabled: bool = True
    desktop_notifications_enabled: bool = True
    mention_notifications_enabled: bool = True
    inbox_digest: InboxDigest = "weekly"
    sound_enabled: bool = False

    default_workspace_id: int | None = Field(default=None, ge=1)

    keyboard_shortcuts_enabled: bool = True
    autosave_drafts: bool = True

    @field_validator("language", mode="before")
    @classmethod
    def _coerce_language(cls, v: object) -> object:
        return _canonical_language(v) if v is not None else v  # type: ignore[arg-type]

    @field_validator("timezone", mode="before")
    @classmethod
    def _coerce_timezone(cls, v: object) -> object:
        return _validate_timezone(v) if v is not None else v  # type: ignore[arg-type]


class UserProfileSettingsUpdate(BaseModel):
    """PATCH body — every field optional, ``None`` means *leave unchanged*.

    The endpoint uses ``model_dump(exclude_unset=True)`` so only the keys
    the caller actually sent are written back.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=512)
    bio: str | None = Field(default=None, max_length=2000)

    language: str | None = Field(default=None, max_length=16)
    timezone: str | None = Field(default=None, max_length=48)
    date_format: DateFormat | None = None
    theme: Theme | None = None

    email_notifications_enabled: bool | None = None
    desktop_notifications_enabled: bool | None = None
    mention_notifications_enabled: bool | None = None
    inbox_digest: InboxDigest | None = None
    sound_enabled: bool | None = None

    default_workspace_id: int | None = Field(default=None, ge=1)

    keyboard_shortcuts_enabled: bool | None = None
    autosave_drafts: bool | None = None

    @field_validator("language", mode="before")
    @classmethod
    def _coerce_language(cls, v: object) -> object:
        if v is None:
            return None
        return _canonical_language(v)  # type: ignore[arg-type]

    @field_validator("timezone", mode="before")
    @classmethod
    def _coerce_timezone(cls, v: object) -> object:
        if v is None:
            return None
        return _validate_timezone(v)  # type: ignore[arg-type]


class UserProfileSettingsRead(UserProfileSettingsBase):
    """Wire shape for GET — includes server-managed fields."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    user_id: int
    created_at: object | None = None
    updated_at: object | None = None


# ---------------------------------------------------------------------------
# Organization settings
# ---------------------------------------------------------------------------


def _validate_notification_prefs(value: dict) -> dict:
    """Enforce ``notification_preferences`` key/value shape.

    Keys must be a subset of :data:`NOTIFICATION_CATEGORIES`; values must
    be plain booleans. We raise per-bad-key with a list so the UI can
    surface every offender at once.
    """
    if not isinstance(value, dict):
        raise ValueError("notification_preferences must be an object")
    bad_keys: list[str] = []
    bad_values: list[str] = []
    for k, v in value.items():
        if k not in NOTIFICATION_CATEGORIES:
            bad_keys.append(k)
        if not isinstance(v, bool):
            bad_values.append(k)
    if bad_keys:
        raise ValueError(
            f"unknown notification categor{'y' if len(bad_keys) == 1 else 'ies'}: "
            f"{sorted(bad_keys)}; expected subset of {list(NOTIFICATION_CATEGORIES)}"
        )
    if bad_values:
        raise ValueError(
            f"notification_preferences values must be booleans; offenders: {bad_values}"
        )
    return value


def _validate_ip_allowlist(value: list) -> list:
    if not isinstance(value, list):
        raise ValueError("ip_allowlist must be a list")
    return [_validate_cidr_or_ip(entry) for entry in value]


def _validate_export_formats(value: list) -> list:
    allowed = {"mp4", "mov", "webm", "mkv", "gif"}
    if not isinstance(value, list):
        raise ValueError("allowed_export_formats must be a list")
    cleaned: list[str] = []
    bad: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            bad.append(repr(entry))
            continue
        lower = entry.strip().lower()
        if lower not in allowed:
            bad.append(entry)
        else:
            cleaned.append(lower)
    if bad:
        raise ValueError(
            f"unknown export formats {bad}; expected subset of {sorted(allowed)}"
        )
    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for entry in cleaned:
        if entry not in seen:
            seen.add(entry)
            deduped.append(entry)
    return deduped


class OrganizationSettingsBase(BaseModel):
    """Shared base for org-settings serialisation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    display_name: str | None = Field(default=None, max_length=128)
    region: str = Field(default="eu-central-1", min_length=1, max_length=32)
    timezone: str = Field(default="UTC", max_length=48)
    language: str = Field(default="zh-CN", max_length=16)

    default_brand_kit_id: int | None = Field(default=None, ge=1)
    default_template_slug: str | None = Field(default=None, max_length=64)
    default_aspect_ratio: AspectRatio = "9:16"
    default_voice: str = Field(default="alloy-en-female", min_length=1, max_length=64)

    default_codec: VideoCodec = "h264"
    default_loudness_lufs: float = Field(default=-14.0, ge=-32.0, le=-6.0)
    video_watermark_enabled: bool = True
    watermark_drafts_only: bool = False
    auto_render_on_approval: bool = True
    public_preview_links_enabled: bool = False

    sso_provider: str | None = Field(default=None, max_length=32)
    force_mfa: bool = False
    session_duration_hours: int = Field(default=12, ge=1, le=720)
    ip_allowlist_enabled: bool = False
    ip_allowlist: list[str] = Field(default_factory=list)

    notification_preferences: dict = Field(default_factory=dict)
    brand_drift_warning_enabled: bool = True

    allowed_export_formats: list[str] = Field(default_factory=list)
    retention_days: int = Field(default=0, ge=0, le=3650)

    @field_validator("language", mode="before")
    @classmethod
    def _coerce_language(cls, v: object) -> object:
        return _canonical_language(v) if v is not None else v  # type: ignore[arg-type]

    @field_validator("timezone", mode="before")
    @classmethod
    def _coerce_timezone(cls, v: object) -> object:
        return _validate_timezone(v) if v is not None else v  # type: ignore[arg-type]

    @field_validator("notification_preferences", mode="before")
    @classmethod
    def _coerce_notifications(cls, v: object) -> object:
        if v is None:
            return {}
        return _validate_notification_prefs(v)  # type: ignore[arg-type]

    @field_validator("ip_allowlist", mode="before")
    @classmethod
    def _coerce_ip_allowlist(cls, v: object) -> object:
        if v is None:
            return []
        return _validate_ip_allowlist(v)  # type: ignore[arg-type]

    @field_validator("allowed_export_formats", mode="before")
    @classmethod
    def _coerce_export_formats(cls, v: object) -> object:
        if v is None:
            return []
        return _validate_export_formats(v)  # type: ignore[arg-type]


class OrganizationSettingsUpdate(BaseModel):
    """PATCH body for org settings — every field optional."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    display_name: str | None = Field(default=None, max_length=128)
    region: str | None = Field(default=None, min_length=1, max_length=32)
    timezone: str | None = Field(default=None, max_length=48)
    language: str | None = Field(default=None, max_length=16)

    default_brand_kit_id: int | None = Field(default=None, ge=1)
    default_template_slug: str | None = Field(default=None, max_length=64)
    default_aspect_ratio: AspectRatio | None = None
    default_voice: str | None = Field(default=None, min_length=1, max_length=64)

    default_codec: VideoCodec | None = None
    default_loudness_lufs: float | None = Field(default=None, ge=-32.0, le=-6.0)
    video_watermark_enabled: bool | None = None
    watermark_drafts_only: bool | None = None
    auto_render_on_approval: bool | None = None
    public_preview_links_enabled: bool | None = None

    sso_provider: str | None = Field(default=None, max_length=32)
    force_mfa: bool | None = None
    session_duration_hours: int | None = Field(default=None, ge=1, le=720)
    ip_allowlist_enabled: bool | None = None
    ip_allowlist: list[str] | None = None

    notification_preferences: dict | None = None
    brand_drift_warning_enabled: bool | None = None

    allowed_export_formats: list[str] | None = None
    retention_days: int | None = Field(default=None, ge=0, le=3650)

    @field_validator("language", mode="before")
    @classmethod
    def _coerce_language(cls, v: object) -> object:
        if v is None:
            return None
        return _canonical_language(v)  # type: ignore[arg-type]

    @field_validator("timezone", mode="before")
    @classmethod
    def _coerce_timezone(cls, v: object) -> object:
        if v is None:
            return None
        return _validate_timezone(v)  # type: ignore[arg-type]

    @field_validator("notification_preferences", mode="before")
    @classmethod
    def _coerce_notifications(cls, v: object) -> object:
        if v is None:
            return None
        return _validate_notification_prefs(v)  # type: ignore[arg-type]

    @field_validator("ip_allowlist", mode="before")
    @classmethod
    def _coerce_ip_allowlist(cls, v: object) -> object:
        if v is None:
            return None
        return _validate_ip_allowlist(v)  # type: ignore[arg-type]

    @field_validator("allowed_export_formats", mode="before")
    @classmethod
    def _coerce_export_formats(cls, v: object) -> object:
        if v is None:
            return None
        return _validate_export_formats(v)  # type: ignore[arg-type]


class OrganizationSettingsRead(OrganizationSettingsBase):
    """Wire shape for GET responses."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    workspace_id: int
    created_at: object | None = None
    updated_at: object | None = None


# ---------------------------------------------------------------------------
# App settings (global key/value)
# ---------------------------------------------------------------------------

# Dotted-path key, e.g. ``"render.max_concurrent"``. Letters, digits, ``.``,
# ``_``, ``-`` allowed; must start with a letter; capped at 128 chars to
# match the column.
_APP_SETTING_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,127}$")


class AppSettingBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    key: Annotated[str, Field(min_length=1, max_length=128)]
    value: object
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool = False

    @field_validator("key", mode="before")
    @classmethod
    def _validate_key(cls, v: object) -> object:
        if not isinstance(v, str):
            raise ValueError("app setting key must be a string")
        s = v.strip()
        if not _APP_SETTING_KEY_RE.match(s):
            raise ValueError(
                f"invalid app setting key {v!r}; expected dotted-path "
                "(letters, digits, '.', '_', '-'; must start with a letter)"
            )
        return s


class AppSettingCreate(AppSettingBase):
    """Body for ``POST /api/v1/settings/app`` — admin only."""


class AppSettingUpdate(BaseModel):
    """PATCH body for an app setting — every field except key is optional."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: object | None = None
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool | None = None


class AppSettingRead(AppSettingBase):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    updated_by: int | None = None
    created_at: object | None = None
    updated_at: object | None = None


# ---------------------------------------------------------------------------
# Effective render defaults (read-only, computed)
# ---------------------------------------------------------------------------


class EffectiveRenderDefaults(BaseModel):
    """Result of :func:`app.services.settings.resolver.resolve_render_defaults`.

    The mix-video and template framework consume this struct to fold the
    org/profile defaults into a pipeline request.
    """

    model_config = ConfigDict(extra="forbid")

    workspace_id: int
    user_id: int | None = None
    brand_kit_id: int | None = None
    template_slug: str | None = None
    aspect_ratio: AspectRatio = "9:16"
    voice: str = "alloy-en-female"
    codec: VideoCodec = "h264"
    loudness_lufs: float = -14.0
    watermark_enabled: bool = True
    watermark_drafts_only: bool = False
    language: str = "zh-CN"
    timezone: str = "UTC"


# ---------------------------------------------------------------------------
# Aggregate list view (``GET /api/v1/settings``)
# ---------------------------------------------------------------------------


class SettingsBundle(BaseModel):
    """The aggregate payload returned by ``GET /api/v1/settings``.

    Useful for one-shot loading of the entire settings page without
    serial waterfall requests. Either side can be ``None`` when the
    caller lacks the right scope (e.g. anonymous reads get no profile).
    """

    model_config = ConfigDict(extra="forbid")

    profile: UserProfileSettingsRead | None = None
    organization: OrganizationSettingsRead | None = None
    effective: EffectiveRenderDefaults | None = None


__all__ = [
    "AppSettingBase",
    "AppSettingCreate",
    "AppSettingRead",
    "AppSettingUpdate",
    "AspectRatio",
    "DateFormat",
    "EffectiveRenderDefaults",
    "InboxDigest",
    "OrganizationSettingsBase",
    "OrganizationSettingsRead",
    "OrganizationSettingsUpdate",
    "SettingsBundle",
    "Theme",
    "UserProfileSettingsBase",
    "UserProfileSettingsRead",
    "UserProfileSettingsUpdate",
    "VideoCodec",
]
