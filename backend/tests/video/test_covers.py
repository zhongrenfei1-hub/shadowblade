import pytest

from app.services.video.covers import CoverSpec, generate_cover
from app.services.video.probe import probe


@pytest.mark.asyncio
async def test_generate_cover_writes_jpeg(synth_clip_a, tmp_path):
    out = tmp_path / "cover.jpg"
    result = await generate_cover(
        synth_clip_a,
        out,
        timestamp=1.0,
        spec=CoverSpec(width=540, height=960, title="HERO"),
    )
    assert result.exists()
    assert result.stat().st_size > 2_000


@pytest.mark.asyncio
async def test_generate_cover_via_thumbnail_selection(synth_clip_a, tmp_path):
    out = tmp_path / "cover_auto.jpg"
    await generate_cover(
        synth_clip_a,
        out,
        timestamp=None,
        spec=CoverSpec(width=720, height=720),  # square
    )
    assert out.exists()
