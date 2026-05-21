import pytest

from app.services.video.subtitle import Cue, load_srt, render_srt, write_srt


def test_load_srt_round_trip(tmp_path):
    cues = [Cue(0.0, 1.5, "hello"), Cue(2.0, 4.5, "world line two")]
    path = tmp_path / "test.srt"
    write_srt(cues, path)

    parsed = load_srt(path)
    assert [c.text for c in parsed] == ["hello", "world line two"]
    assert parsed[1].start == 2.0
    assert parsed[1].end == 4.5


def test_load_srt_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_srt(tmp_path / "nope.srt")


def test_cue_subtext_default_empty():
    c = Cue(0.0, 1.0, "main")
    assert c.subtext == ""


def test_cue_subtext_explicit():
    c = Cue(0.0, 1.0, "main", subtext="caption")
    assert c.subtext == "caption"
