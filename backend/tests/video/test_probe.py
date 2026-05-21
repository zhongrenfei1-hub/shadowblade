import pytest

from app.services.video.probe import probe, measure_loudness


@pytest.mark.asyncio
async def test_probe_returns_basic_metadata(synth_clip_a):
    info = await probe(synth_clip_a)
    assert info.has_video
    assert info.has_audio
    assert info.duration == pytest.approx(3.0, abs=0.2)
    assert info.width == 640
    assert info.height == 360
    assert info.fps == pytest.approx(30.0, abs=0.1)
    assert info.video_codec == "h264"


@pytest.mark.asyncio
async def test_probe_with_loudness(synth_clip_a):
    info = await probe(synth_clip_a, with_loudness=True)
    assert info.loudness_i is not None
    assert -70.0 < info.loudness_i < 0.0


@pytest.mark.asyncio
async def test_measure_loudness_direct(synth_voice):
    i, tp, lra = await measure_loudness(synth_voice)
    assert i < 0
    assert tp < 6  # dBTP — should not blow up
