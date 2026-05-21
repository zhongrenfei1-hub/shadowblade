import shutil

import pytest

from app.services.audio.tts import EDGE_TTS_VOICES, generate_audio


pytestmark = pytest.mark.asyncio


def _online_skip():
    """Skip TTS tests when offline — edge-tts hits an MS endpoint."""
    import socket

    try:
        socket.create_connection(("speech.platform.bing.com", 443), timeout=3)
        return False
    except OSError:
        return True


@pytest.mark.skipif(_online_skip(), reason="offline — edge-tts unreachable")
async def test_generate_audio_writes_wav(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")
    out = tmp_path / "voice.wav"
    result = await generate_audio("你好，这是一段测试语音。", out, voice="xiaoxiao-zh-f")
    assert result.audio_path.exists()
    assert result.audio_path.stat().st_size > 5_000
    assert result.voice_id.startswith("zh-CN-")
    assert result.duration and result.duration > 0.5


def test_voice_catalog_includes_main_options():
    keys = set(EDGE_TTS_VOICES)
    assert {"xiaoxiao-zh-f", "yunyang-zh-m"}.issubset(keys)
    for v in EDGE_TTS_VOICES.values():
        assert v["id"].startswith("zh-CN-")
