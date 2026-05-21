"""End-to-end AI video pipeline endpoints.

Aligns with the upstream Shadowblade worker contract:
  POST /generate-script    (LLM-replacement: smart_template scenario bank)
  POST /generate-audio     (TTS: edge-tts free, no key)
  POST /generate-subtitle  (ASR: faster-whisper local)
  POST /generate-cover     (ffmpeg keyframe + brand gradient)
  POST /generate-video     (one-click: topic → MP4)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.audio.asr import transcribe
from app.services.audio.tts import EDGE_TTS_VOICES, generate_audio
from app.services.llm.script_generator import SCENARIOS, generate_script
from app.services.video.covers import CoverSpec, generate_cover
from app.services.video.pipeline import ClipSpec, MixPipeline, MixRequest
from app.services.video.subtitle import Cue

log = logging.getLogger("shadowblade.api.generate")
router = APIRouter(prefix="/generate", tags=["generate"])

# In-process pipeline registry — keyed by uuid, stores per-step state.
_JOBS: dict[str, dict] = {}


def _work_dir(name: str) -> Path:
    root = Path(settings.storage_root) / "work" / name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _final_dir(name: str) -> Path:
    root = Path(settings.storage_root) / "final" / name
    root.mkdir(parents=True, exist_ok=True)
    return root


# ─── /generate-script ──────────────────────────────────────────────────


class ScriptRequest(BaseModel):
    topic: str = Field(..., description="主题，如「春季美容补水套餐」")
    language: str = "zh-CN"
    length: int = Field(default=220, ge=60, le=600, description="目标字符数")


class ScriptResponse(BaseModel):
    content: str
    keywords: str
    scenario: str
    estimated_seconds: float
    cues: list[dict]


@router.post("/script", response_model=ScriptResponse)
async def post_generate_script(body: ScriptRequest):
    script = generate_script(body.topic, length=body.length, language=body.language)
    return ScriptResponse(
        content=script.content,
        keywords=script.keywords,
        scenario=script.scenario,
        estimated_seconds=script.estimated_seconds,
        cues=script.cues,
    )


@router.get("/scenarios")
async def list_scenarios():
    return {
        "items": [
            {"slug": s.slug, "label": s.label, "keywords": list(s.keywords)}
            for s in SCENARIOS.values()
        ]
    }


# ─── /generate-audio (TTS) ─────────────────────────────────────────────


class AudioRequest(BaseModel):
    text: str
    voice: str = "xiaoxiao-zh-f"
    rate: str = "+0%"
    output_filename: str | None = None


class AudioResponse(BaseModel):
    audio_file: str
    voice_id: str
    duration_seconds: float | None
    relative_url: str


@router.post("/audio", response_model=AudioResponse)
async def post_generate_audio(body: AudioRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is empty")
    job = uuid.uuid4().hex[:10]
    filename = body.output_filename or f"voice_{job}.wav"
    out_path = _work_dir("tts") / filename
    try:
        result = await generate_audio(
            body.text,
            out_path,
            voice=body.voice,
            rate=body.rate,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AudioResponse(
        audio_file=str(result.audio_path),
        voice_id=result.voice_id,
        duration_seconds=result.duration,
        relative_url=f"/static/storage/{result.audio_path.relative_to(Path(settings.storage_root))}",
    )


@router.get("/voices")
async def list_voices():
    return {
        "items": [
            {"alias": k, **v} for k, v in EDGE_TTS_VOICES.items()
        ]
    }


# ─── /generate-subtitle (ASR) ──────────────────────────────────────────


class SubtitleRequest(BaseModel):
    audio_file: str
    language: str = "zh"
    model_name: str = "base"
    word_timestamps: bool = False
    initial_prompt: str | None = None


class SubtitleSegment(BaseModel):
    start: float
    end: float
    text: str


class SubtitleResponse(BaseModel):
    subtitle_file: str
    language: str
    duration: float
    model: str
    segments: list[SubtitleSegment]
    relative_url: str


@router.post("/subtitle", response_model=SubtitleResponse)
async def post_generate_subtitle(body: SubtitleRequest):
    src = Path(body.audio_file)
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"audio not found: {src}")
    try:
        result = await transcribe(
            src,
            model_name=body.model_name,
            language=body.language,
            word_timestamps=body.word_timestamps,
            initial_prompt=body.initial_prompt,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    out_dir = _work_dir("srt")
    srt_path = out_dir / f"{src.stem}.srt"
    srt_path.write_text(result.to_srt(), encoding="utf-8")
    rel = srt_path.relative_to(Path(settings.storage_root))
    return SubtitleResponse(
        subtitle_file=str(srt_path),
        language=result.language,
        duration=round(result.duration, 3),
        model=result.model,
        segments=[
            SubtitleSegment(start=s.start, end=s.end, text=s.text)
            for s in result.segments
        ],
        relative_url=f"/static/storage/{rel}",
    )


# ─── /generate-cover ───────────────────────────────────────────────────


class CoverRequest(BaseModel):
    video_file: str
    timestamp: float | None = 3.0
    width: int = 1080
    height: int = 1920
    primary_color: str = "#0F2A4A"
    accent_color: str = "#22D3B7"
    title: str | None = None


class CoverResponse(BaseModel):
    cover_file: str
    relative_url: str


@router.post("/cover", response_model=CoverResponse)
async def post_generate_cover(body: CoverRequest):
    src = Path(body.video_file)
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"video not found: {src}")
    out_dir = _final_dir("covers")
    out = out_dir / f"{src.stem}.jpg"
    try:
        result = await generate_cover(
            src,
            out,
            timestamp=body.timestamp,
            spec=CoverSpec(
                width=body.width,
                height=body.height,
                primary=body.primary_color,
                accent=body.accent_color,
                title=body.title,
            ),
        )
    except (RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    rel = result.relative_to(Path(settings.storage_root))
    return CoverResponse(
        cover_file=str(result),
        relative_url=f"/static/storage/{rel}",
    )


# ─── /generate-video (one-click end-to-end) ───────────────────────────


class GenerateVideoRequest(BaseModel):
    topic: str = Field(..., description="商家主题，例「春季美容补水套餐」")
    clip_paths: list[str] = Field(..., description="本地视频素材路径列表")
    voice: str = "xiaoxiao-zh-f"
    rate: str = "+0%"
    asr_model: str = "base"
    skip_asr: bool = Field(
        default=False,
        description="True 时跳过 whisper，直接用脚本的均匀切分作为字幕（更快）",
    )
    bgm_path: str | None = None
    watermark_path: str | None = None
    title: str | None = None
    preset: str = "social_9x16"
    color_look: str | None = "cinematic"
    auto_white_balance: bool = True
    adaptive_bgm_mix: bool = True
    length: int = 220


class GenerateVideoResponse(BaseModel):
    job_id: str
    status: str
    steps: dict
    output: dict | None = None
    error: str | None = None


@router.post("", response_model=GenerateVideoResponse)
async def post_generate_video(body: GenerateVideoRequest, background_tasks: BackgroundTasks):
    """Kick off the full topic → MP4 pipeline as a background job."""
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "status": "queued",
        "steps": {
            "script": "pending",
            "tts": "pending",
            "asr": "pending",
            "mix": "pending",
            "cover": "pending",
        },
        "output": None,
        "error": None,
    }
    background_tasks.add_task(_run_video_job, job_id, body)
    return GenerateVideoResponse(job_id=job_id, status="queued", steps=_JOBS[job_id]["steps"])


@router.get("/jobs/{job_id}", response_model=GenerateVideoResponse)
async def get_video_job(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="job not found")
    j = _JOBS[job_id]
    return GenerateVideoResponse(
        job_id=job_id,
        status=j["status"],
        steps=j["steps"],
        output=j["output"],
        error=j["error"],
    )


async def _run_video_job(job_id: str, body: GenerateVideoRequest) -> None:
    job = _JOBS[job_id]
    job["status"] = "running"
    try:
        # ---- 1. script ----
        job["steps"]["script"] = "running"
        script = generate_script(body.topic, length=body.length)
        job["steps"]["script"] = "succeeded"

        # ---- 2. tts ----
        job["steps"]["tts"] = "running"
        voice_path = _work_dir(f"video_{job_id}") / "voice.wav"
        tts_result = await generate_audio(
            script.content, voice_path, voice=body.voice, rate=body.rate
        )
        job["steps"]["tts"] = "succeeded"

        # ---- 3. asr (optional) ----
        cues: list[Cue]
        if body.skip_asr:
            job["steps"]["asr"] = "skipped"
            # Reuse script cues — they were already scaled to estimated_seconds.
            # Scale to the *measured* TTS duration so subtitles align with audio.
            real_duration = tts_result.duration or script.estimated_seconds
            scale = real_duration / max(0.1, script.estimated_seconds)
            cues = [
                Cue(
                    start=round(c["start"] * scale, 2),
                    end=round(c["end"] * scale, 2),
                    text=c["text"],
                )
                for c in script.cues
            ]
        else:
            job["steps"]["asr"] = "running"
            try:
                asr = await transcribe(
                    voice_path,
                    model_name=body.asr_model,
                    language="zh",
                )
                cues = [
                    Cue(start=s.start, end=s.end, text=s.text) for s in asr.segments
                ]
                job["steps"]["asr"] = "succeeded"
            except Exception as exc:  # noqa: BLE001 — fall back to script cues
                log.warning("ASR failed (%s); falling back to script cues", exc)
                job["steps"]["asr"] = f"failed: {exc}"
                real_duration = tts_result.duration or script.estimated_seconds
                scale = real_duration / max(0.1, script.estimated_seconds)
                cues = [
                    Cue(
                        start=round(c["start"] * scale, 2),
                        end=round(c["end"] * scale, 2),
                        text=c["text"],
                    )
                    for c in script.cues
                ]

        # ---- 4. mix ----
        job["steps"]["mix"] = "running"
        # Sequence the clips evenly across the audio length
        clips = _build_clip_specs(body.clip_paths, tts_result.duration or script.estimated_seconds)
        if not clips:
            raise RuntimeError("no usable clips supplied")
        mix_req = MixRequest(
            project_id=f"job_{job_id}",
            clips=clips,
            voice_path=str(voice_path),
            bgm_path=body.bgm_path,
            cues=cues,
            watermark_path=body.watermark_path,
            preset=body.preset,
            title=body.title or body.topic,
            color_look=body.color_look,
            auto_white_balance=body.auto_white_balance,
            adaptive_bgm_mix=body.adaptive_bgm_mix,
            storage_root=settings.storage_root,
        )
        mix_result = await MixPipeline().run(mix_req)
        job["steps"]["mix"] = "succeeded"

        # ---- 5. cover ----
        job["steps"]["cover"] = "succeeded" if mix_result.cover_path else "skipped"

        rel_video = Path(mix_result.output_path).relative_to(Path(settings.storage_root))
        rel_cover = None
        if mix_result.cover_path:
            rel_cover = Path(mix_result.cover_path).relative_to(Path(settings.storage_root))
        job["output"] = {
            "video_file": str(mix_result.output_path),
            "cover_file": str(mix_result.cover_path) if mix_result.cover_path else None,
            "video_url": f"/static/storage/{rel_video}",
            "cover_url": f"/static/storage/{rel_cover}" if rel_cover else None,
            "duration": mix_result.duration,
            "scenario": script.scenario,
            "script": script.content,
            "keywords": script.keywords,
            "transitions": mix_result.transitions,
            "warnings": mix_result.warnings,
        }
        job["status"] = "succeeded"
    except Exception as exc:  # noqa: BLE001
        log.exception("video job %s failed", job_id)
        job["status"] = "failed"
        job["error"] = str(exc)


def _build_clip_specs(paths: list[str], total_seconds: float) -> list[ClipSpec]:
    """Distribute clips evenly along the audio timeline.

    Each clip gets ``total_seconds / N`` of screen time (bounded to [1.5, 6]),
    with the first clip flagged as the hero and the last as a chapter break.
    """
    valid = [p for p in paths if Path(p).exists()]
    if not valid:
        return []
    n = len(valid)
    per = max(1.5, min(6.0, total_seconds / n))
    clips: list[ClipSpec] = []
    for i, p in enumerate(valid):
        clips.append(
            ClipSpec(
                path=p,
                end=per,
                is_hero=(i == 0),
                is_chapter_break=(i == n - 1 and n >= 3),
                brightness=0.4 + (i * 0.15) % 0.6,
                motion=0.3 + (i * 0.18) % 0.6,
            )
        )
    return clips


__all__ = ["router"]
