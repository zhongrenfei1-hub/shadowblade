from app.services.video.subtitle import (
    Cue,
    SubtitleStyle,
    parse_srt,
    render_ass,
    render_srt,
    segment_utterances,
    smart_segment,
)


def test_smart_segment_short_cue_returns_self():
    cue = Cue(0.0, 2.0, "短句")
    out = smart_segment(cue)
    assert len(out) == 1
    assert out[0].text == "短句"


def test_smart_segment_breaks_on_tier1_punctuation():
    cue = Cue(0.0, 6.0, "今天我们要发布新一代智能腕环。它续航长达三十天，并且支持血氧监测。")
    out = smart_segment(cue, max_chars=14)
    assert len(out) >= 2
    # First piece should split at the period
    assert "新一代" in out[0].text
    # All pieces obey max char budget * lines
    for piece in out:
        for line in piece.text.split("\n"):
            assert len(line) <= 14


def test_smart_segment_preserves_total_time():
    cue = Cue(0.0, 6.0, "一二三四五六七八九十一二三四五六七八九十一二三四五六七八九十")
    pieces = smart_segment(cue, max_chars=10)
    assert pieces[0].start == 0.0
    assert pieces[-1].end >= 5.5


def test_segment_utterances_enforces_min_gap():
    cues = [
        Cue(0.0, 1.0, "AAA"),
        Cue(1.0, 2.0, "BBB"),  # touches A — should be pushed
    ]
    out = segment_utterances(cues, min_gap=0.1)
    assert out[1].start >= out[0].end + 0.099


def test_render_srt_round_trips():
    cues = [Cue(0.0, 1.0, "first"), Cue(1.5, 2.5, "second")]
    text = render_srt(cues)
    parsed = parse_srt(text)
    assert [c.text for c in parsed] == ["first", "second"]
    assert parsed[0].end == 1.0


def test_render_ass_has_brand_style():
    cues = [Cue(0.0, 1.0, "hello")]
    style = SubtitleStyle(font="Inter", size=72, outline=4)
    ass = render_ass(cues, style=style, video_w=1080, video_h=1920)
    assert "Style: Default,Inter,72" in ass
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    assert "Dialogue:" in ass
    # fade tag is present
    assert "\\fad(" in ass
