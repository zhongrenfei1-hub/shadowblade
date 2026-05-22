"""Schema-level tests for Settings — pure Pydantic, no DB.

Cover the validators added for:

* IETF BCP 47 language tag canonicalisation
* IANA timezone strict-set validation
* Literal enums (theme, date_format, inbox_digest, codec, aspect ratio)
* Numeric bounds (loudness LUFS, session duration, retention days)
* ``notification_preferences`` category whitelist
* IP allowlist CIDR/IP parsing
* ``allowed_export_formats`` whitelist + dedup
* App-setting dotted-path key regex
* ``extra='forbid'`` rejection of unknown fields
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.settings import (
    AppSettingCreate,
    AppSettingUpdate,
    OrganizationSettingsUpdate,
    UserProfileSettingsUpdate,
)


# --- profile ----------------------------------------------------------------


def test_profile_language_canonicalises_case():
    out = UserProfileSettingsUpdate(language="en-us")
    assert out.language == "en-US"


def test_profile_language_accepts_bare_two_letter():
    out = UserProfileSettingsUpdate(language="zh")
    assert out.language == "zh"


def test_profile_language_rejects_garbage():
    with pytest.raises(ValidationError):
        UserProfileSettingsUpdate(language="not-a-language!")


def test_profile_timezone_validates_against_iana():
    out = UserProfileSettingsUpdate(timezone="Asia/Shanghai")
    assert out.timezone == "Asia/Shanghai"


def test_profile_timezone_rejects_unknown():
    with pytest.raises(ValidationError):
        UserProfileSettingsUpdate(timezone="Atlantis/Lost")


def test_profile_theme_literal_validation():
    UserProfileSettingsUpdate(theme="dark")  # ok
    UserProfileSettingsUpdate(theme="light")  # ok
    UserProfileSettingsUpdate(theme="system")  # ok
    with pytest.raises(ValidationError):
        UserProfileSettingsUpdate(theme="midnight")


def test_profile_inbox_digest_literal():
    UserProfileSettingsUpdate(inbox_digest="off")
    UserProfileSettingsUpdate(inbox_digest="weekly")
    with pytest.raises(ValidationError):
        UserProfileSettingsUpdate(inbox_digest="hourly")


def test_profile_extra_field_rejected():
    with pytest.raises(ValidationError) as ei:
        UserProfileSettingsUpdate.model_validate(
            {"nickname": "Ava", "unknown_field": 1}
        )
    assert "unknown_field" in str(ei.value)


def test_profile_default_workspace_must_be_positive():
    with pytest.raises(ValidationError):
        UserProfileSettingsUpdate(default_workspace_id=0)


# --- organization -----------------------------------------------------------


def test_org_loudness_bounds():
    # In range.
    OrganizationSettingsUpdate(default_loudness_lufs=-14.0)
    OrganizationSettingsUpdate(default_loudness_lufs=-6.0)
    # Out of range.
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(default_loudness_lufs=-40.0)
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(default_loudness_lufs=0.0)


def test_org_session_duration_bounds():
    OrganizationSettingsUpdate(session_duration_hours=1)
    OrganizationSettingsUpdate(session_duration_hours=720)
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(session_duration_hours=0)
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(session_duration_hours=721)


def test_org_aspect_ratio_literal():
    OrganizationSettingsUpdate(default_aspect_ratio="9:16")
    OrganizationSettingsUpdate(default_aspect_ratio="16:9")
    OrganizationSettingsUpdate(default_aspect_ratio="1:1")
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(default_aspect_ratio="3:2")


def test_org_codec_literal():
    OrganizationSettingsUpdate(default_codec="h264")
    OrganizationSettingsUpdate(default_codec="prores_422_hq")
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(default_codec="av1")


def test_org_notification_preferences_whitelisted_keys():
    # Subset of NOTIFICATION_CATEGORIES is fine.
    OrganizationSettingsUpdate(
        notification_preferences={"approvals": True, "billing": False}
    )
    # Unknown category — rejected with the bad keys called out.
    with pytest.raises(ValidationError) as ei:
        OrganizationSettingsUpdate(
            notification_preferences={"unknown_bucket": True}
        )
    assert "unknown_bucket" in str(ei.value)


def test_org_notification_preferences_must_be_bool():
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(
            notification_preferences={"approvals": "yes"}
        )


def test_org_ip_allowlist_accepts_ip_and_cidr():
    out = OrganizationSettingsUpdate(
        ip_allowlist=["10.0.0.0/8", "192.168.1.42", "::1", "2001:db8::/32"]
    )
    assert "10.0.0.0/8" in out.ip_allowlist
    assert "192.168.1.42" in out.ip_allowlist


def test_org_ip_allowlist_rejects_garbage():
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(ip_allowlist=["not-an-ip"])


def test_org_export_formats_whitelist_and_dedup():
    out = OrganizationSettingsUpdate(
        allowed_export_formats=["mp4", "MP4", "webm"]
    )
    # Lowercased + deduped.
    assert out.allowed_export_formats == ["mp4", "webm"]


def test_org_export_formats_rejects_unknown():
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(allowed_export_formats=["avi"])


def test_org_retention_days_bounds():
    OrganizationSettingsUpdate(retention_days=0)
    OrganizationSettingsUpdate(retention_days=3650)
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(retention_days=-1)
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(retention_days=3651)


def test_org_language_canonicalises():
    out = OrganizationSettingsUpdate(language="ZH-cn")
    assert out.language == "zh-CN"


def test_org_default_brand_kit_id_positive_only():
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(default_brand_kit_id=0)


# --- app setting ------------------------------------------------------------


def test_app_setting_key_dotted_path():
    AppSettingCreate(key="render.max_concurrent", value=8)
    AppSettingCreate(key="feature.beta_studio_enabled", value=True)
    # Must start with a letter.
    with pytest.raises(ValidationError):
        AppSettingCreate(key="1leading_digit", value=1)
    # No spaces.
    with pytest.raises(ValidationError):
        AppSettingCreate(key="has space", value=1)


def test_app_setting_update_value_can_be_any_json():
    AppSettingUpdate(value={"nested": [1, 2, 3]})
    AppSettingUpdate(value=None)  # explicit clear
    AppSettingUpdate(value=42)
    AppSettingUpdate(value="string")


def test_app_setting_extra_field_rejected():
    with pytest.raises(ValidationError):
        AppSettingCreate.model_validate(
            {"key": "x.y", "value": 1, "stray": True}
        )
