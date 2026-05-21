import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.video.beat import detect_beats


def _ffmpeg() -> str:
    bin_path = shutil.which("ffmpeg")
    if not bin_path:
        pytest.skip("ffmpeg not available")
    return bin_path


@pytest.fixture(scope="session")
def click_track_120bpm(fixtures_root: Path) -> Path:
    """A 6-second 120 BPM click — twelve sharp clicks at 0.5s spacing."""
    out = fixtures_root / "click_120.wav"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    expr = (
        "aevalsrc='"
        "0.6*exp(-200*mod(t,0.5))*sin(2*PI*880*t)"
        "':d=6:s=22050"
    )
    subprocess.run(
        [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", expr, "-ac", "1", str(out)],
        check=True,
        capture_output=True,
    )
    return out


@pytest.fixture(scope="session")
def click_track_90bpm(fixtures_root: Path) -> Path:
    """A 6-second 90 BPM click — 9 clicks at 0.667s spacing."""
    out = fixtures_root / "click_90.wav"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    expr = (
        "aevalsrc='"
        "0.6*exp(-200*mod(t,0.6667))*sin(2*PI*880*t)"
        "':d=6:s=22050"
    )
    subprocess.run(
        [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", expr, "-ac", "1", str(out)],
        check=True,
        capture_output=True,
    )
    return out


@pytest.mark.asyncio
async def test_detect_beats_120bpm(click_track_120bpm):
    grid = await detect_beats(str(click_track_120bpm))
    assert len(grid.onsets) >= 8
    # BPM rounded to nearest 4 — allow 116/120/124
    assert 110 <= grid.bpm <= 128, f"got bpm={grid.bpm}"
    # First onset within the first 0.6s
    assert grid.onsets[0] < 0.6


@pytest.mark.asyncio
async def test_detect_beats_90bpm(click_track_90bpm):
    grid = await detect_beats(str(click_track_90bpm))
    assert len(grid.onsets) >= 6
    assert 80 <= grid.bpm <= 100, f"got bpm={grid.bpm}"


@pytest.mark.asyncio
async def test_detect_beats_silent_returns_no_onsets(synth_bgm):
    """A pure tonal sine has no transient onsets — should detect ~0."""
    grid = await detect_beats(str(synth_bgm))
    # Allow a tiny number of false positives at signal start
    assert len(grid.onsets) <= 3
