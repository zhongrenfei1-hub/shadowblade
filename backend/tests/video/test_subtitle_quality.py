from app.services.video.subtitle import (
    Cue,
    adaptive_font_size,
    score_subtitles,
)


def test_score_subtitles_flags_high_cps():
    cues = [Cue(0.0, 1.0, "这是一句二十个字的非常密集的字幕内容真的很多字非常长")]
    report = score_subtitles(cues)
    assert report.cues == 1
    codes = {i.code for i in report.issues}
    assert "cps_too_high" in codes or "cps_high" in codes
    assert report.is_ok is False or any(i.severity == "fail" for i in report.issues)


def test_score_subtitles_clean_pass():
    cues = [
        Cue(0.0, 2.0, "你好"),
        Cue(2.2, 4.0, "今天发布"),
    ]
    report = score_subtitles(cues)
    fail = [i for i in report.issues if i.severity == "fail"]
    assert not fail


def test_score_subtitles_detects_overlap():
    cues = [Cue(0.0, 2.0, "A"), Cue(1.5, 2.5, "B")]
    report = score_subtitles(cues)
    assert any(i.code == "overlap" for i in report.issues)


def test_adaptive_font_size_scales_down_for_long_cue():
    short = Cue(0.0, 2.0, "短")
    long_text = "这是一段非常非常长非常长的字幕需要缩小字号才能放进画面里" * 2
    long = Cue(0.0, 2.0, long_text)
    assert adaptive_font_size(short, base_size=64) == 64
    scaled = adaptive_font_size(long, base_size=64)
    assert scaled < 64
    assert scaled >= int(64 * 0.65)
