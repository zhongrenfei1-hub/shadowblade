"""ASR — faster-whisper local transcription.

Why faster-whisper:
  - CTranslate2 backend, 4–8× faster than openai/whisper on CPU
  - Quantised models keep RAM low (base is ~74MB on disk, ~150MB resident)
  - Returns word-level timestamps when ``word_timestamps=True``

Default model is ``base`` — good enough for Chinese marketing scripts.
First call downloads the model into ``~/.cache/huggingface``; subsequent calls
are warm. ``large-v3`` is the highest-accuracy option (~1.5GB).
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Iterable

log = logging.getLogger("shadowblade.asr")

_MODEL_LOCK = Lock()
_MODEL_CACHE: dict[str, object] = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")


@dataclass(slots=True)
class ASRSegment:
    start: float
    end: float
    text: str
    words: list[dict] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(slots=True)
class ASRResult:
    language: str
    language_probability: float
    duration: float
    segments: list[ASRSegment]
    model: str

    def to_srt(self) -> str:
        """Render to SRT text."""

        def ts(t: float) -> str:
            t = max(0.0, t)
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        lines: list[str] = []
        for i, seg in enumerate(self.segments, start=1):
            lines.append(str(i))
            lines.append(f"{ts(seg.start)} --> {ts(seg.end)}")
            lines.append(seg.text.strip())
            lines.append("")
        return "\n".join(lines)


def _load_model(model_name: str):
    """Lazy singleton — first call may download (~74MB for base)."""
    with _MODEL_LOCK:
        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]
        from faster_whisper import WhisperModel

        log.info("loading faster-whisper model %s", model_name)
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
        )
        _MODEL_CACHE[model_name] = model
        return model


def _transcribe_sync(
    audio_path: str,
    *,
    model_name: str,
    language: str,
    word_timestamps: bool,
    vad_filter: bool,
    initial_prompt: str | None,
) -> ASRResult:
    model = _load_model(model_name)
    segments_iter, info = model.transcribe(
        audio_path,
        language=language or None,
        word_timestamps=word_timestamps,
        vad_filter=vad_filter,
        initial_prompt=initial_prompt,
        beam_size=5,
    )
    segments: list[ASRSegment] = []
    for s in segments_iter:
        words: list[dict] = []
        if word_timestamps and getattr(s, "words", None):
            words = [
                {"start": float(w.start), "end": float(w.end), "text": w.word}
                for w in s.words
                if w.start is not None and w.end is not None
            ]
        segments.append(
            ASRSegment(
                start=float(s.start),
                end=float(s.end),
                text=s.text.strip(),
                words=words,
            )
        )
    return ASRResult(
        language=info.language,
        language_probability=float(info.language_probability),
        duration=float(info.duration),
        segments=segments,
        model=model_name,
    )


async def transcribe(
    audio_path: str | Path,
    *,
    model_name: str = "base",
    language: str = "zh",
    word_timestamps: bool = False,
    vad_filter: bool = True,
    initial_prompt: str | None = None,
) -> ASRResult:
    """Run ASR asynchronously by offloading the (CPU-bound) call to a thread.

    ``model_name``:  tiny / base / small / medium / large-v3
    ``language``:    ISO 639-1 ("zh", "en", or "" for auto-detect)
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"audio not found: {path}")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _EXECUTOR,
        lambda: _transcribe_sync(
            str(path),
            model_name=model_name,
            language=language,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            initial_prompt=initial_prompt,
        ),
    )


__all__ = ["ASRSegment", "ASRResult", "transcribe"]
