"""Audio services — TTS (edge-tts) + ASR (faster-whisper)."""

from app.services.audio.asr import ASRResult, ASRSegment, transcribe
from app.services.audio.tts import EDGE_TTS_VOICES, TTSResult, generate_audio

__all__ = [
    "EDGE_TTS_VOICES",
    "TTSResult",
    "generate_audio",
    "ASRResult",
    "ASRSegment",
    "transcribe",
]
