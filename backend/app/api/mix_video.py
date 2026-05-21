"""POST /api/v1/mix-video — the real mixing endpoint.

Modes:
    - ``POST /mix-video/preview``   synchronous 360p preview (≤60s clips)
    - ``POST /mix-video``           kick off an async render task
    - ``GET  /mix-video/{task_id}`` poll status
    - ``GET  /mix-video/{task_id}/download`` stream the resulting MP4
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.video.brand import BrandKit, default_kit
from app.services.video.pipeline import ClipSpec, MixPipeline, MixRequest
from app.services.video.subtitle import Cue

log = logging.getLogger("shadowblade.api.mix")
router = APIRouter(prefix="/mix-video", tags=["mix_video"])

# In-memory task registry. Swap for Redis / Celery in production.
_TASKS: dict[str, dict] = {}


class ClipPayload(BaseModel):
    path: str
    start: float = 0.0
    end: float | None = None
    brightness: float = Field(default=0.5, ge=0.0, le=1.0)
    motion: float = Field(default=0.5, ge=0.0, le=1.0)
    is_chapter_break: bool = False
    is_hero: bool = False


class CuePayload(BaseModel):
    start: float
    end: float
    text: str


class BrandPayload(BaseModel):
    name: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    secondary_color: str | None = None
    font_heading: str | None = None
    font_body: str | None = None
    target_lufs: float | None = None
    subtitle_size: int | None = None
    subtitle_margin_v: int | None = None
    watermark_opacity: float | None = None
    watermark_position: str | None = None
    watermark_width_pct: float | None = None


class MixVideoRequest(BaseModel):
    project_id: int | str
    clips: list[ClipPayload]
    voice_path: str | None = None
    bgm_path: str | None = None
    cues: list[CuePayload] = Field(default_factory=list)
    watermark_path: str | None = None
    watermark_position: str = "br"
    brand: BrandPayload | None = None
    preset: str = "social_9x16"
    transition_style: str = "editorial"
    max_transition: float = Field(default=0.55, ge=0.05, le=2.0)
    target_lufs: float | None = None
    title: str | None = None
    cover_timestamp: float | None = None


class MixVideoResponse(BaseModel):
    project_id: int | str
    output_path: str
    cover_path: str | None
    duration: float
    preset: str
    used_hardware: bool
    transitions: list[str]
    runtime_seconds: float
    warnings: list[str]


class MixTaskStatus(BaseModel):
    task_id: str
    status: str  # queued | running | succeeded | failed
    progress: float = 0.0
    project_id: int | str | None = None
    output_path: str | None = None
    cover_path: str | None = None
    duration: float | None = None
    preset: str | None = None
    transitions: list[str] = []
    runtime_seconds: float | None = None
    error: str | None = None


def _build_mix_request(body: MixVideoRequest) -> MixRequest:
    brand = default_kit()
    if body.brand:
        data = {k: v for k, v in body.brand.model_dump().items() if v is not None}
        # Brand.from_dict expects "voice" not "voice_name"
        brand = BrandKit.from_dict(
            {
                **brand.__dict__,
                **data,
            }
        )
    clips = [
        ClipSpec(
            path=c.path,
            start=c.start,
            end=c.end,
            brightness=c.brightness,
            motion=c.motion,
            is_chapter_break=c.is_chapter_break,
            is_hero=c.is_hero,
        )
        for c in body.clips
    ]
    cues = [Cue(c.start, c.end, c.text) for c in body.cues]
    return MixRequest(
        project_id=body.project_id,
        clips=clips,
        voice_path=body.voice_path,
        bgm_path=body.bgm_path,
        cues=cues,
        watermark_path=body.watermark_path,
        watermark_position=body.watermark_position,
        brand_kit=brand,
        preset=body.preset,
        transition_style=body.transition_style,
        max_transition=body.max_transition,
        target_lufs=body.target_lufs,
        title=body.title,
        cover_timestamp=body.cover_timestamp,
        storage_root=settings.storage_root,
    )


@router.post("/preview", response_model=MixVideoResponse)
async def preview_mix(body: MixVideoRequest):
    """Synchronous 360p preview path. Forces a fast encoder preset."""
    req = _build_mix_request(body)
    # Force preview preset based on the requested aspect
    if req.preset.endswith("9x16"):
        req.preset = "preview_360_9x16"
    elif req.preset.endswith("16x9"):
        req.preset = "preview_360_16x9"
    else:
        req.preset = "preview_360_9x16"
    pipeline = MixPipeline()
    try:
        result = await pipeline.run(req)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MixVideoResponse(
        project_id=result.project_id,
        output_path=str(result.output_path),
        cover_path=str(result.cover_path) if result.cover_path else None,
        duration=result.duration,
        preset=result.preset,
        used_hardware=result.used_hardware,
        transitions=result.transitions,
        runtime_seconds=result.runtime_seconds,
        warnings=result.warnings,
    )


@router.post("", response_model=MixTaskStatus)
async def submit_mix(body: MixVideoRequest, background_tasks: BackgroundTasks):
    """Kick off an async mix render. Returns a task id for polling."""
    task_id = uuid.uuid4().hex[:12]
    _TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0.0,
        "project_id": body.project_id,
        "preset": body.preset,
    }
    background_tasks.add_task(_run_async_mix, task_id, body)
    return MixTaskStatus(**_TASKS[task_id])


@router.get("/{task_id}", response_model=MixTaskStatus)
async def get_task(task_id: str):
    payload = _TASKS.get(task_id)
    if not payload:
        raise HTTPException(status_code=404, detail="task not found")
    return MixTaskStatus(**payload)


@router.get("/{task_id}/download")
async def download(task_id: str):
    payload = _TASKS.get(task_id)
    if not payload:
        raise HTTPException(status_code=404, detail="task not found")
    if payload.get("status") != "succeeded" or not payload.get("output_path"):
        raise HTTPException(status_code=409, detail="render not ready")
    path = Path(payload["output_path"])
    if not path.exists():
        raise HTTPException(status_code=410, detail="output expired")
    return FileResponse(
        path, media_type="video/mp4", filename=f"shadowblade-{task_id}.mp4"
    )


@router.get("/presets/list")
async def list_presets_endpoint():
    from app.services.video.encoder import PRESETS

    return {
        "items": [
            {
                "name": name,
                "width": p.width,
                "height": p.height,
                "fps": p.fps,
                "video_bitrate": p.video_bitrate,
            }
            for name, p in PRESETS.items()
        ]
    }


async def _run_async_mix(task_id: str, body: MixVideoRequest) -> None:
    task = _TASKS[task_id]
    task["status"] = "running"
    task["progress"] = 0.05
    try:
        req = _build_mix_request(body)
        pipeline = MixPipeline()
        result = await pipeline.run(req)
        task.update(
            {
                "status": "succeeded",
                "progress": 1.0,
                "output_path": str(result.output_path),
                "cover_path": str(result.cover_path) if result.cover_path else None,
                "duration": result.duration,
                "preset": result.preset,
                "transitions": result.transitions,
                "runtime_seconds": result.runtime_seconds,
            }
        )
    except Exception as exc:  # noqa: BLE001 — surfaced via API
        log.exception("mix-video task %s failed", task_id)
        task.update({"status": "failed", "error": str(exc), "progress": 1.0})


__all__: list[str] = ["router"]
