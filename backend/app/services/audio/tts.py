"""TTS — Microsoft Edge Neural TTS (free, no API key).

Generates Chinese voiceover at high quality without any account or budget.
Output is MP3; we transcode to WAV via ffmpeg so the rest of the pipeline can
treat it uniformly (the mix engine expects 48kHz stereo WAV input ideally).

Theme-driven voice differentiation
-----------------------------------
The same script should sound different depending on what kind of video it
ends up in. A marketing promo wants energetic + fast + bright; a tutorial
wants clear + slightly slow + neutral; a training piece wants warm +
steady + lower-pitched.

We achieve this by combining three independent edge-tts knobs:

  * voice    — 5 distinct timbres (晓晓 / 云扬 / 晓伊 / 云夏 / 晓萱)
  * rate     — speech speed (-50% … +100%)
  * pitch    — fundamental frequency (-50Hz … +50Hz)

A :class:`VoiceStyle` packages all three. :func:`resolve_voice_style` picks
one from a theme/intent string ("marketing", "training", "tutorial", …),
so callers can stay on the high level and let the audio engine decide the
mechanics.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import edge_tts

log = logging.getLogger("shadowblade.tts")

# Curated voice menu — biased toward the most natural Chinese voices.
# Full inventory: `edge-tts --list-voices`.
#
# ``styles`` lists the express-as SSML styles Microsoft officially supports
# for each voice (https://learn.microsoft.com/azure/ai-services/speech-service/
# language-support#voice-styles-and-roles). edge-tts doesn't (yet) wrap
# mstts:express-as natively, but we keep the list for future use and to
# document what each timbre is capable of.
EDGE_TTS_VOICES: dict[str, dict] = {
    "xiaoxiao-zh-f": {
        "id": "zh-CN-XiaoxiaoNeural",
        "label": "晓晓 · 女声 · 亲切",
        "tone": "warm",
        "styles": (
            "assistant", "chat", "cheerful", "sad", "angry", "fearful",
            "disgruntled", "serious", "affectionate", "gentle", "depressed",
            "embarrassed", "empathetic", "envious", "lyrical",
            "customerservice", "newscast", "poetry-reading",
        ),
    },
    "yunyang-zh-m": {
        "id": "zh-CN-YunyangNeural",
        "label": "云扬 · 男声 · 沉稳",
        "tone": "authoritative",
        "styles": ("customerservice", "narration-professional", "newscast-casual"),
    },
    "xiaoyi-zh-f": {
        "id": "zh-CN-XiaoyiNeural",
        "label": "晓伊 · 女声 · 明亮",
        "tone": "bright",
        "styles": (
            "cheerful", "sad", "angry", "fearful", "disgruntled",
            "serious", "affectionate", "gentle", "embarrassed",
        ),
    },
    "yunxia-zh-m": {
        "id": "zh-CN-YunxiaNeural",
        "label": "云夏 · 男声 · 年轻",
        "tone": "youthful",
        "styles": ("calm", "fearful", "cheerful", "disgruntled", "serious"),
    },
    "xiaoxuan-zh-f": {
        "id": "zh-CN-XiaoxuanNeural",
        "label": "晓萱 · 女声 · 知性",
        "tone": "intellectual",
        "styles": (
            "cheerful", "sad", "angry", "fearful", "disgruntled",
            "serious", "gentle", "depressed",
        ),
    },
}


# ─── VoiceStyle: voice + rate + pitch bundled together ─────────────────


@dataclass(slots=True, frozen=True)
class VoiceStyle:
    """Bundle of edge-tts knobs that together define a "voice personality".

    The same script produced with two different :class:`VoiceStyle` instances
    will sound audibly different — different timbre (voice), different pace
    (rate), different register (pitch).

    Fields
    ------
    voice
        Alias from :data:`EDGE_TTS_VOICES` (e.g. ``"xiaoxiao-zh-f"``) or a
        full Microsoft voice id (e.g. ``"zh-CN-XiaoxiaoNeural"``).
    rate
        edge-tts rate string. ``"+0%"`` = normal; ``"+25%"`` = 25% faster.
        Valid range roughly ``-50%`` … ``+100%``.
    pitch
        edge-tts pitch string. ``"+0Hz"`` = normal; ``"+8Hz"`` = brighter,
        ``"-3Hz"`` = lower / warmer. Valid range ``-50Hz`` … ``+50Hz``.
    intent
        Optional label describing where this style came from (theme name,
        scenario slug). Just for logs / debugging — not used by edge-tts.
    """

    voice: str = "xiaoxiao-zh-f"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    intent: str = ""

    def merge(self, override: "VoiceStyle | None") -> "VoiceStyle":
        """Return a new VoiceStyle where ``override`` wins for non-defaults.

        Used by the request → brand → template → scenario precedence chain.
        Treats *any* non-empty / non-default field on ``override`` as a
        deliberate choice and lets it through.
        """
        if override is None:
            return self
        return VoiceStyle(
            voice=override.voice or self.voice,
            rate=override.rate or self.rate,
            pitch=override.pitch or self.pitch,
            intent=override.intent or self.intent,
        )


# ─── Theme → VoiceStyle map ────────────────────────────────────────────
#
# These are the personality presets. Pick by passing the intent name to
# :func:`resolve_voice_style`. Each preset is hand-tuned so the resulting
# audio is clearly distinguishable from its neighbours.
#
# Picking rules:
#   * marketing      明亮 + 快 + 偏高 → 有感染力
#   * product_demo   沉稳 + 适中 + 标准 → 专业可信
#   * training       知性 + 稍慢 + 偏低 → 沉稳易懂
#   * tutorial       亲切 + 稍慢 + 标准 → 清晰示范
#   * dance / social 明亮 + 很快 + 高 → 节奏感
#   * game           年轻 + 快 + 偏高 → 活力
#   * news           沉稳 + 标准 + 标准 → 权威
#   * lyrical        亲切 + 稍慢 + 标准 → 抒情
#   * customerservice 亲切 + 适中 + 标准 → 客服感
#   * default        亲切 + 标准 + 标准
THEME_VOICE_STYLES: dict[str, VoiceStyle] = {
    "marketing":       VoiceStyle("xiaoyi-zh-f",   "+18%", "+5Hz",  "marketing"),
    "product_demo":    VoiceStyle("yunyang-zh-m",  "+4%",  "+0Hz",  "product_demo"),
    "training":        VoiceStyle("xiaoxuan-zh-f", "-8%",  "-3Hz",  "training"),
    "tutorial":        VoiceStyle("xiaoxiao-zh-f", "-4%",  "+0Hz",  "tutorial"),
    "dance":           VoiceStyle("xiaoyi-zh-f",   "+28%", "+8Hz",  "dance"),
    "social":          VoiceStyle("xiaoyi-zh-f",   "+15%", "+4Hz",  "social"),
    "game":            VoiceStyle("yunxia-zh-m",   "+16%", "+5Hz",  "game"),
    "news":            VoiceStyle("yunyang-zh-m",  "+0%",  "+1Hz",  "news"),
    "lyrical":         VoiceStyle("xiaoxiao-zh-f", "-6%",  "+0Hz",  "lyrical"),
    "customerservice": VoiceStyle("xiaoxiao-zh-f", "+2%",  "+0Hz",  "customerservice"),
    # Tone-driven aliases — match the ``tone`` field on EDGE_TTS_VOICES so
    # callers can ask for an *adjective* and still land somewhere sensible.
    # Kept distinct from the theme presets above so unit tests catch
    # accidental collisions.
    "energetic":       VoiceStyle("xiaoyi-zh-f",   "+22%", "+6Hz",  "energetic"),
    "professional":    VoiceStyle("yunyang-zh-m",  "+2%",  "+0Hz",  "professional"),
    "warm":            VoiceStyle("xiaoxiao-zh-f", "+0%",  "+0Hz",  "warm"),
    "intellectual":    VoiceStyle("xiaoxuan-zh-f", "-4%",  "-1Hz",  "intellectual"),
    "youthful":        VoiceStyle("yunxia-zh-m",   "+10%", "+3Hz",  "youthful"),
    "calm":            VoiceStyle("yunyang-zh-m",  "-6%",  "-2Hz",  "calm"),
    "default":         VoiceStyle("xiaoxiao-zh-f", "+0%",  "+0Hz",  "default"),
}


def resolve_voice_style(intent: str | None, *, fallback: str = "default") -> VoiceStyle:
    """Pick a VoiceStyle for the given intent / theme / scenario name.

    Returns the ``default`` preset when ``intent`` is missing or unknown.
    Lookup is case-insensitive; underscores and hyphens are interchangeable
    so callers can use either spelling.
    """
    if not intent:
        return THEME_VOICE_STYLES[fallback]
    key = intent.strip().lower().replace("-", "_")
    if key in THEME_VOICE_STYLES:
        return THEME_VOICE_STYLES[key]
    # Friendly fallback: log once at debug so unknown intents are visible
    log.debug("unknown voice intent %r — falling back to %s", intent, fallback)
    return THEME_VOICE_STYLES[fallback]


# ─── TTS execution ────────────────────────────────────────────────────


@dataclass(slots=True)
class TTSResult:
    audio_path: Path
    voice_id: str
    rate: str
    pitch: str = "+0Hz"
    duration: float | None = None
    raw_mp3_path: Path | None = None
    style: VoiceStyle | None = None


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
    pitch: str,
    out_path: Path,
) -> None:
    """Stream edge-tts audio into ``out_path``."""
    communicate = edge_tts.Communicate(
        text=text, voice=voice, rate=rate, pitch=pitch
    )
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
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    style: VoiceStyle | None = None,
    keep_mp3: bool = False,
) -> TTSResult:
    """Synthesise ``text`` to a WAV file at ``out_path``.

    Either pass a :class:`VoiceStyle` via ``style=`` (recommended — keeps
    voice/rate/pitch consistent), or pass individual ``voice``/``rate``/
    ``pitch`` overrides. Individual overrides win if both are supplied.

    Parameters
    ----------
    text
        The script to read aloud. Empty / whitespace strings raise
        ``ValueError``.
    out_path
        Destination WAV path. Parent dirs are created if missing.
    voice, rate, pitch
        edge-tts knobs. See :class:`VoiceStyle` for the units.
    style
        Preset bundle. When given, its values are used as the base; any
        explicit ``voice``/``rate``/``pitch`` argument overrides the
        corresponding style field.
    keep_mp3
        If True, the intermediate MP3 isn't deleted (handy for debugging).
    """
    if not text.strip():
        raise ValueError("TTS text is empty")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not on PATH — required for MP3 → WAV transcode")

    base_style = style or THEME_VOICE_STYLES["default"]
    final_voice = voice or base_style.voice
    final_rate = rate or base_style.rate
    final_pitch = pitch or base_style.pitch
    final_style = VoiceStyle(final_voice, final_rate, final_pitch, base_style.intent)

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    mp3_path = target.with_suffix(".mp3")
    voice_id = _resolve_voice(final_voice)

    await _synthesise_mp3(
        text,
        voice=voice_id,
        rate=final_rate,
        pitch=final_pitch,
        out_path=mp3_path,
    )
    await _ffmpeg_to_wav(mp3_path, target)
    duration = await _measure_duration(target)

    if not keep_mp3:
        try:
            mp3_path.unlink()
            mp3_path = None  # type: ignore[assignment]
        except OSError:
            pass

    return TTSResult(
        audio_path=target,
        voice_id=voice_id,
        rate=final_rate,
        pitch=final_pitch,
        duration=duration,
        raw_mp3_path=mp3_path,
        style=final_style,
    )


__all__ = [
    "EDGE_TTS_VOICES",
    "THEME_VOICE_STYLES",
    "VoiceStyle",
    "TTSResult",
    "generate_audio",
    "resolve_voice_style",
]
