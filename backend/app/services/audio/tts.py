"""TTS — Microsoft Edge Neural TTS (free, no API key).

Generates Chinese voiceover at high quality without any account or budget.
Output is MP3; we transcode to WAV via ffmpeg so the rest of the pipeline can
treat it uniformly (the mix engine expects 48kHz stereo WAV input ideally).
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import edge_tts

log = logging.getLogger("shadowblade.tts")

# Curated voice menu — biased toward the most natural Chinese voices.
# Full inventory: `edge-tts --list-voices`.
EDGE_TTS_VOICES: dict[str, dict] = {
    "xiaoxiao-zh-f": {
        "id": "zh-CN-XiaoxiaoNeural",
        "label": "晓晓 · 女声 · 亲切",
        "tone": "warm",
    },
    "yunyang-zh-m": {
        "id": "zh-CN-YunyangNeural",
        "label": "云扬 · 男声 · 沉稳",
        "tone": "authoritative",
    },
    "xiaoyi-zh-f": {
        "id": "zh-CN-XiaoyiNeural",
        "label": "晓伊 · 女声 · 明亮",
        "tone": "bright",
    },
    "yunxia-zh-m": {
        "id": "zh-CN-YunxiaNeural",
        "label": "云夏 · 男声 · 年轻",
        "tone": "youthful",
    },
    "xiaoxuan-zh-f": {
        "id": "zh-CN-XiaoxuanNeural",
        "label": "晓萱 · 女声 · 知性",
        "tone": "intellectual",
    },
}


@dataclass(slots=True)
class TTSResult:
    audio_path: Path
    voice_id: str
    rate: str
    duration: float | None = None
    raw_mp3_path: Path | None = None


def _resolve_voice(voice_alias_or_id: str) -> str:
    if voice_alias_or_id in EDGE_TTS_VOICES:
        return EDGE_TTS_VOICES[voice_alias_or_id]["id"]
    # If the caller passed a full Microsoft voice id, trust it.
    return voice_alias_or_id


async def _synthesise_mp3(
    text: str,
    *,
    voice: str,
    rate: str,
    out_path: Path,
) -> None:
    """Stream edge-tts audio into ``out_path``."""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    await communicate.save(str(out_path))


async def _ffmpeg_to_wav(src: Path, dst: Path) -> None:
    """Transcode MP3 → 48kHz mono WAV for downstream mixing."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "48000",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg wav transcode failed: {err.decode(errors='ignore')[-400:]}")


async def _measure_duration(path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    out, _ = await proc.communicate()
    text = out.decode().strip()
    try:
        return float(text)
    except ValueError:
        return None


async def generate_audio(
    text: str,
    out_path: str | Path,
    *,
    voice: str = "xiaoxiao-zh-f",
    rate: str = "+0%",
    keep_mp3: bool = False,
) -> TTSResult:
    """Synthesise ``text`` to a WAV file at ``out_path``.

    ``rate`` follows edge-tts syntax: "+10%", "-15%", or "+0%".
    """
    if not text.strip():
        raise ValueError("TTS text is empty")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not on PATH — required for MP3 → WAV transcode")

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    mp3_path = target.with_suffix(".mp3")
    voice_id = _resolve_voice(voice)

    await _synthesise_mp3(text, voice=voice_id, rate=rate, out_path=mp3_path)
    await _ffmpeg_to_wav(mp3_path, target)
    duration = await _measure_duration(target)

    if not keep_mp3:
        try:
            mp3_path.unlink()
            mp3_path = None  # type: ignore[assignment]
        except OSError:
            pass

    return TTSResult(audio_path=target, voice_id=voice_id, rate=rate, duration=duration, raw_mp3_path=mp3_path)


__all__ = ["EDGE_TTS_VOICES", "TTSResult", "generate_audio"]
