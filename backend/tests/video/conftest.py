"""Shared fixtures — synthesise sample clips with ffmpeg's built-in sources."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import pytest


def _ffmpeg() -> str:
    bin_path = shutil.which("ffmpeg")
    if not bin_path:
        pytest.skip("ffmpeg not available in PATH")
    return bin_path


def _generate(cmd: list[str]) -> None:
    import subprocess

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg setup failed: {r.stderr[-400:]}")


@pytest.fixture(scope="session")
def fixtures_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("sb_video_fixtures")
    return root


@pytest.fixture(scope="session")
def synth_clip_a(fixtures_root: Path) -> Path:
    """A 3s 16:9 colourful test clip with a 440Hz tone."""
    out = fixtures_root / "clip_a.mp4"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    _generate(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=30:duration=3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def synth_clip_b(fixtures_root: Path) -> Path:
    out = fixtures_root / "clip_b.mp4"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    _generate(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "smptebars=size=640x360:rate=30:duration=2.5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=523:duration=2.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def synth_clip_c(fixtures_root: Path) -> Path:
    out = fixtures_root / "clip_c.mp4"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    _generate(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x0F2A4A:size=640x360:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def synth_voice(fixtures_root: Path) -> Path:
    """7-second 'voice' track: sine tone with intermittent silences so
    silencedetect / pacing has gaps to find."""
    out = fixtures_root / "voice.wav"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    # Concatenate sine + silence + sine + silence + sine
    _generate(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "aevalsrc='if(lt(mod(t,2.4),1.7), 0.18*sin(2*PI*220*t), 0)':d=8:s=48000",
            "-ac",
            "1",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def synth_bgm(fixtures_root: Path) -> Path:
    out = fixtures_root / "bgm.wav"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    _generate(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=110:duration=10:sample_rate=48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
    )
    return out


@pytest.fixture(scope="session")
def synth_logo(fixtures_root: Path) -> Path:
    out = fixtures_root / "logo.png"
    if out.exists():
        return out
    ffmpeg = _ffmpeg()
    _generate(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x22D3B7:size=120x60:rate=1:duration=1",
            "-frames:v",
            "1",
            str(out),
        ]
    )
    return out


@pytest.fixture
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# Ensure tests find the backend package — pytest runs from repo root.
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SHADOWBLADE_STORAGE_ROOT", "./storage")
