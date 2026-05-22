"""Tests for theme-driven voice resolution.

Covers the VoiceStyle dataclass, THEME_VOICE_STYLES map, and the
``resolve_voice_style`` helper. These run offline — no edge-tts call.
"""

from __future__ import annotations

import pytest

from app.services.audio.tts import (
    EDGE_TTS_VOICES,
    THEME_VOICE_STYLES,
    VoiceStyle,
    resolve_voice_style,
)
from app.services.llm.script_generator import SCENARIOS, generate_script


# ─── THEME_VOICE_STYLES table ─────────────────────────────────────────


def test_all_themes_resolve_to_known_voices():
    """Every preset must reference a voice that's actually in EDGE_TTS_VOICES."""
    for theme, style in THEME_VOICE_STYLES.items():
        assert style.voice in EDGE_TTS_VOICES, (
            f"theme {theme!r} references unknown voice {style.voice!r}"
        )


def test_required_themes_present():
    for theme in (
        "marketing",
        "product_demo",
        "training",
        "tutorial",
        "dance",
        "social",
        "game",
        "default",
    ):
        assert theme in THEME_VOICE_STYLES, f"missing theme: {theme}"


def test_themes_are_audibly_different():
    """No two presets should be identical — that defeats the point of the
    differentiation system."""
    seen: dict[tuple[str, str, str], str] = {}
    for theme, style in THEME_VOICE_STYLES.items():
        key = (style.voice, style.rate, style.pitch)
        # 'default' is allowed to collide with one tone alias ('warm') by design
        if key in seen and theme not in {"default", "warm"} and seen[key] not in {"default", "warm"}:
            pytest.fail(
                f"theme {theme!r} has the same (voice, rate, pitch) as {seen[key]!r}"
            )
        seen.setdefault(key, theme)


# ─── resolve_voice_style ──────────────────────────────────────────────


def test_resolve_known_intent():
    s = resolve_voice_style("marketing")
    assert s.voice == "xiaoyi-zh-f"
    assert s.rate == "+18%"
    assert s.pitch == "+5Hz"


def test_resolve_is_case_insensitive():
    a = resolve_voice_style("MARKETING")
    b = resolve_voice_style("Marketing")
    c = resolve_voice_style("marketing")
    assert a == b == c


def test_resolve_normalises_hyphen_underscore():
    """Both ``product-demo`` and ``product_demo`` should land on the same
    preset — frontend can use either spelling."""
    a = resolve_voice_style("product-demo")
    b = resolve_voice_style("product_demo")
    assert a == b
    assert a.voice == "yunyang-zh-m"


def test_resolve_unknown_falls_back_to_default():
    s = resolve_voice_style("not-a-real-theme")
    assert s == THEME_VOICE_STYLES["default"]


def test_resolve_empty_string_falls_back():
    assert resolve_voice_style("") == THEME_VOICE_STYLES["default"]
    assert resolve_voice_style(None) == THEME_VOICE_STYLES["default"]


# ─── VoiceStyle.merge ─────────────────────────────────────────────────


def test_voice_style_merge_override_wins():
    base = VoiceStyle("xiaoxiao-zh-f", "+0%", "+0Hz", "default")
    over = VoiceStyle("yunyang-zh-m", "+5%", "-2Hz", "professional")
    out = base.merge(over)
    assert out.voice == "yunyang-zh-m"
    assert out.rate == "+5%"
    assert out.pitch == "-2Hz"
    assert out.intent == "professional"


def test_voice_style_merge_none_returns_self():
    base = VoiceStyle("xiaoyi-zh-f", "+10%", "+3Hz", "marketing")
    assert base.merge(None) is base


def test_voice_style_merge_empty_field_keeps_base():
    base = VoiceStyle("xiaoxiao-zh-f", "+0%", "+0Hz", "default")
    partial = VoiceStyle("", "+10%", "", "")  # only rate is set
    out = base.merge(partial)
    assert out.voice == "xiaoxiao-zh-f"  # kept base
    assert out.rate == "+10%"  # took override
    assert out.pitch == "+0Hz"  # kept base


# ─── Scenario → voice_intent wiring ───────────────────────────────────


def test_every_scenario_has_voice_intent():
    for slug, sc in SCENARIOS.items():
        assert sc.voice_intent, f"scenario {slug!r} missing voice_intent"
        # And it must resolve to something
        s = resolve_voice_style(sc.voice_intent)
        assert s.voice in EDGE_TTS_VOICES


def test_script_inherits_scenario_intent():
    """The generated Script carries the scenario's voice_intent forward —
    that's how the audio pipeline knows what flavour to use."""
    script = generate_script("春季美容补水套餐", length=160)
    assert script.scenario == "beauty"
    assert script.voice_intent == "warm"

    script2 = generate_script("健身私教减脂塑形", length=160)
    assert script2.scenario == "fitness"
    assert script2.voice_intent == "energetic"


# ─── Template voice block ─────────────────────────────────────────────


def test_template_voice_block_loads():
    from app.services.template import load_template

    for tmpl_name, expected_intent in (
        ("marketing", "marketing"),
        ("training", "training"),
        ("tutorial", "tutorial"),
        ("dance", "dance"),
        ("game", "game"),
        ("product-demo", "product_demo"),
    ):
        t = load_template(tmpl_name)
        assert t.voice.intent == expected_intent, (
            f"template {tmpl_name!r}.voice.intent expected {expected_intent!r}, "
            f"got {t.voice.intent!r}"
        )
