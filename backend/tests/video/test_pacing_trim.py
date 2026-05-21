import pytest

from app.services.video.pacing import trim_silence_bounds


@pytest.mark.asyncio
async def test_trim_silence_bounds_returns_non_negative(synth_voice):
    head, tail = await trim_silence_bounds(str(synth_voice))
    assert head >= 0
    assert tail >= 0
