from app.services.llm.script_generator import SCENARIOS, detect_scenario, generate_script


def test_detect_scenario_beauty():
    s = detect_scenario("春季美容补水套餐")
    assert s.slug == "beauty"


def test_detect_scenario_nail():
    s = detect_scenario("七夕款美甲新色")
    assert s.slug == "nail"


def test_detect_scenario_fallback_default():
    s = detect_scenario("一段随便的文字没有关键词")
    assert s.slug == "default"


def test_generate_script_returns_content_and_keywords():
    out = generate_script("春季美容补水套餐", length=180)
    assert len(out.content) >= 80
    assert out.keywords
    assert out.scenario == "beauty"
    assert out.estimated_seconds > 0
    assert out.cues  # non-empty


def test_generate_script_is_deterministic():
    a = generate_script("七夕款美甲", length=180)
    b = generate_script("七夕款美甲", length=180)
    assert a.content == b.content
    assert a.keywords == b.keywords


def test_generate_script_cues_cover_full_duration():
    out = generate_script("春季美容补水套餐", length=240)
    first = out.cues[0]
    last = out.cues[-1]
    assert first["start"] == 0.0
    # Cues span ~ the estimated duration (within tolerance)
    assert last["end"] >= out.estimated_seconds * 0.85


def test_all_scenarios_have_required_fields():
    for s in SCENARIOS.values():
        assert s.openers and s.benefits and s.ctas and s.hashtags
        assert len(s.openers) >= 2
        assert len(s.benefits) >= 3
