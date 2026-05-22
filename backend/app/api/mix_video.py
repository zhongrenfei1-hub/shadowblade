"""POST /api/v1/mix-video — the real mixing endpoint.

Modes:
    - ``POST /mix-video/preview``   synchronous 360p preview (≤60s clips)
    - ``POST /mix-video``           kick off an async render task
    - ``GET  /mix-video/{task_id}`` poll status
    - ``GET  /mix-video/{task_id}/download`` stream the resulting MP4
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.api.deps import (
    get_current_user_id,
    get_current_workspace_id,
    get_db,
)
from app.core.config import settings
from app.models.brand_kit import BrandKit as BrandKitORM
from app.services import notifications as notifications_svc
from app.services.template import (
    TemplateNotFoundError,
    apply_brand_kit_to_request,
    apply_template_to_request,
    load_template,
)
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
    speed: float = Field(default=1.0, ge=0.1, le=8.0)


class CuePayload(BaseModel):
    start: float
    end: float
    text: str
    subtext: str = ""


class BrandPayload(BaseModel):
    name: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    secondary_color: str | None = None
    font_heading: str | None = None
    font_body: str | None = None
    target_lufs: float | None = None
    target_tp: float | None = None
    subtitle_size: int | None = None
    subtitle_margin_v: int | None = None
    watermark_opacity: float | None = None
    watermark_position: str | None = None
    watermark_width_pct: float | None = None
    # Audio bus knobs — folded from template.audio
    bgm_gain_db: float | None = None
    voice_gain_db: float | None = None
    duck_threshold_db: float | None = None
    duck_ratio: float | None = None
    fade_in: float | None = None
    fade_out: float | None = None


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
    snap_to_beats: bool = False
    color_look: str | None = None  # "warm" | "cool" | "cinematic" | "punchy" | "mono" | "vintage"
    lut_path: str | None = None
    auto_white_balance: bool = False
    srt_path: str | None = None
    adaptive_bgm_mix: bool = False
    # Ken Burns slow zoom/pan — folded from template.ken_burns
    ken_burns_enabled: bool = False
    ken_burns_intensity: str = "subtle"  # subtle | medium | strong
    ken_burns_direction: str = "auto"  # in | out | pan_left | pan_right | auto
    ken_burns_max_zoom: float | None = None  # overrides intensity when set
    ken_burns_apply_to: str = "all"  # all | low_motion
    # Cover layout — folded from template.cover (brand_strip + title position)
    cover_title_position: str = "bottom-center"
    cover_title_max_chars: int | None = None
    cover_show_brand_strip: bool = False
    cover_brand_strip_color: str | None = None
    cover_brand_strip_position: str = "left"
    cover_brand_strip_width_pct: float = 0.04
    # Subtitle keyword highlight — folded from template.highlight
    highlight_enabled: bool = False
    highlight_color: str | None = None
    highlight_bold: bool = False
    highlight_underline: bool = False
    # Template framework: when set, load the named template and use it to
    # fill any field the user did NOT include in this payload. User-explicit
    # values always win (Pydantic v2 model_fields_set is the source of truth).
    template: str | None = None


class SubtitleIssuePayload(BaseModel):
    cue_index: int
    severity: str
    code: str
    message: str
    cps: float


class BeatGridPayload(BaseModel):
    bpm: float
    onsets: list[float]


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
    subtitle_issues: list[SubtitleIssuePayload] = Field(default_factory=list)
    subtitle_max_cps: float | None = None
    beat_grid: BeatGridPayload | None = None


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
    subtitle_max_cps: float | None = None
    bgm_bpm: float | None = None
    warnings: list[str] = []
    error: str | None = None


def _resolve_template(body: MixVideoRequest) -> MixVideoRequest:
    """If body.template is set, load it and fold its defaults into the
    payload for any field the user did not supply. Raises HTTPException
    on unknown template names so the client gets a clear 400.
    """
    if not body.template:
        return body
    try:
        tmpl = load_template(body.template)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"unknown template: {exc}") from exc
    return apply_template_to_request(tmpl, body)


async def _load_active_brand_kit(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int | None,
) -> BrandKitORM | None:
    """Resolve the effective brand kit for a mix-video request.

    Order (user > workspace > org-settings default > None):

    1. user-scoped active kit for ``(workspace_id, user_id)``
    2. workspace-scoped active kit
    3. ``organization_settings.default_brand_kit_id`` — picked up only when
       the referenced row is still active in this workspace.

    Step 3 is the integration seam with the Settings module: admins can set
    a default kit through ``PUT /api/v1/settings/organization`` and every
    render that doesn't have a user-scoped override picks it up.
    """
    if user_id is not None:
        stmt = (
            select(BrandKitORM)
            .where(
                BrandKitORM.workspace_id == workspace_id,
                BrandKitORM.scope == "user",
                BrandKitORM.owner_id == user_id,
                BrandKitORM.is_active.is_(True),
            )
            .order_by(BrandKitORM.id.desc())
            .limit(1)
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            return result

    stmt = (
        select(BrandKitORM)
        .where(
            BrandKitORM.workspace_id == workspace_id,
            BrandKitORM.scope == "workspace",
            BrandKitORM.is_active.is_(True),
        )
        .order_by(BrandKitORM.id.desc())
        .limit(1)
    )
    workspace_kit = (await db.execute(stmt)).scalars().first()
    if workspace_kit is not None:
        return workspace_kit

    # Final fallback — the org-settings default. Lazy-imported to keep this
    # module free of cycles with the settings service.
    from app.models.settings import OrganizationSettings

    org_default_id = (
        await db.execute(
            select(OrganizationSettings.default_brand_kit_id).where(
                OrganizationSettings.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    if org_default_id is None:
        return None
    stmt = (
        select(BrandKitORM)
        .where(
            BrandKitORM.id == org_default_id,
            BrandKitORM.workspace_id == workspace_id,
            BrandKitORM.is_active.is_(True),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def _apply_org_settings_defaults(
    db: AsyncSession,
    *,
    workspace_id: int,
    body: "MixVideoRequest",
) -> "MixVideoRequest":
    """Fold org-settings defaults onto a mix-video request payload.

    Mirrors brand-kit fold semantics — we only touch fields the caller
    did *not* explicitly send (``model_fields_set`` is the source of truth).

    Currently folds:
    * ``template``        ← ``default_template_slug``
    * ``preset``          ← derived from ``default_aspect_ratio`` (only when
                            the caller left the social_9x16 default in place)
    * ``target_lufs``     ← ``default_loudness_lufs``
    * ``watermark_path``  ← cleared when ``video_watermark_enabled=False``

    The org-settings row is auto-materialised, so the call is safe on a
    brand-new workspace.
    """
    from app.services.settings import get_or_create_org_settings

    org = await get_or_create_org_settings(db, workspace_id=workspace_id)
    explicit = body.model_fields_set
    updates: dict[str, object] = {}

    if "template" not in explicit and org.default_template_slug:
        updates["template"] = org.default_template_slug

    if "target_lufs" not in explicit and body.target_lufs is None:
        updates["target_lufs"] = org.default_loudness_lufs

    if "preset" not in explicit:
        aspect_to_preset = {
            "9:16": "social_9x16",
            "16:9": "broadcast_16x9",
            "1:1": "social_1x1",
            "4:5": "social_4x5",
        }
        preset_name = aspect_to_preset.get(org.default_aspect_ratio)
        # Only override the *default* — a caller who set 16x9 implicitly
        # via a template still gets to keep it.
        if preset_name and body.preset == "social_9x16":
            updates["preset"] = preset_name

    if not org.video_watermark_enabled and "watermark_path" not in explicit:
        updates["watermark_path"] = None

    if not updates:
        return body
    return body.model_copy(update=updates)


def _build_mix_request(body: MixVideoRequest) -> MixRequest:
    body = _resolve_template(body)
    brand = default_kit()
    if body.brand:
        data = {k: v for k, v in body.brand.model_dump().items() if v is not None}
        # BrandKit is dataclass(slots=True) → no __dict__; use asdict
        brand = BrandKit.from_dict(
            {
                **dataclasses.asdict(brand),
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
            speed=c.speed,
        )
        for c in body.clips
    ]
    cues = [Cue(c.start, c.end, c.text, subtext=c.subtext) for c in body.cues]
    if body.srt_path and not cues:
        from app.services.video.subtitle import load_srt

        cues = load_srt(body.srt_path)
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
        snap_to_beats=body.snap_to_beats,
        color_look=body.color_look,
        lut_path=body.lut_path,
        auto_white_balance=body.auto_white_balance,
        adaptive_bgm_mix=body.adaptive_bgm_mix,
        ken_burns_enabled=body.ken_burns_enabled,
        ken_burns_intensity=body.ken_burns_intensity,
        ken_burns_direction=body.ken_burns_direction,
        ken_burns_max_zoom=body.ken_burns_max_zoom,
        ken_burns_apply_to=body.ken_burns_apply_to,
        cover_title_position=body.cover_title_position,
        cover_title_max_chars=body.cover_title_max_chars,
        cover_show_brand_strip=body.cover_show_brand_strip,
        cover_brand_strip_color=body.cover_brand_strip_color,
        cover_brand_strip_position=body.cover_brand_strip_position,
        cover_brand_strip_width_pct=body.cover_brand_strip_width_pct,
        highlight_enabled=body.highlight_enabled,
        highlight_color=body.highlight_color,
        highlight_bold=body.highlight_bold,
        highlight_underline=body.highlight_underline,
    )


def _result_to_response(result) -> MixVideoResponse:
    issues = [
        SubtitleIssuePayload(
            cue_index=i.cue_index,
            severity=i.severity,
            code=i.code,
            message=i.message,
            cps=round(i.cps, 2),
        )
        for i in (result.subtitle_report.issues if result.subtitle_report else [])
    ]
    beat = None
    if result.beat_grid:
        beat = BeatGridPayload(
            bpm=round(result.beat_grid.bpm, 2),
            onsets=[round(t, 3) for t in result.beat_grid.onsets[:128]],
        )
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
        subtitle_issues=issues,
        subtitle_max_cps=(
            round(result.subtitle_report.max_cps, 2)
            if result.subtitle_report
            else None
        ),
        beat_grid=beat,
    )


@router.post("/preview", response_model=MixVideoResponse)
async def preview_mix(
    body: MixVideoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Synchronous 360p preview path. Forces a fast encoder preset.

    Before building the pipeline request we fold the caller's active
    Brand Kit (if any) into the payload so colours, fonts, watermark and
    audio defaults match the workspace identity. The caller can still
    override anything by passing the field explicitly.
    """
    # Capture the *true* user-explicit field set BEFORE org/brand fold —
    # ``model_copy(update=...)`` and ``model_validate(model_dump())`` both
    # taint ``model_fields_set`` with whatever the helper touched, which
    # would otherwise trick :func:`apply_template_to_request` into thinking
    # those fields were user-supplied.
    _user_set = set(body.model_fields_set)
    # Fold org-settings defaults *first* — they should lose to anything the
    # brand kit later supplies (kit > org > spec defaults). Both folds are
    # opt-in: caller-explicit fields always win.
    body = await _apply_org_settings_defaults(
        db, workspace_id=workspace_id, body=body
    )
    kit = await _load_active_brand_kit(db, workspace_id=workspace_id, user_id=user_id)
    if kit is not None:
        body = apply_brand_kit_to_request(kit, body)
    # Restore the original user-set so template-apply has a faithful view.
    body.__pydantic_fields_set__.clear()
    body.__pydantic_fields_set__.update(_user_set)
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
    return _result_to_response(result)


@router.post("", response_model=MixTaskStatus)
async def submit_mix(
    body: MixVideoRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Kick off an async mix render. Returns a task id for polling."""
    _user_set = set(body.model_fields_set)
    body = await _apply_org_settings_defaults(
        db, workspace_id=workspace_id, body=body
    )
    kit = await _load_active_brand_kit(db, workspace_id=workspace_id, user_id=user_id)
    if kit is not None:
        body = apply_brand_kit_to_request(kit, body)
    body.__pydantic_fields_set__.clear()
    body.__pydantic_fields_set__.update(_user_set)
    task_id = uuid.uuid4().hex[:12]
    _TASKS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0.0,
        "project_id": body.project_id,
        "preset": body.preset,
    }
    background_tasks.add_task(
        _run_async_mix, task_id, body, workspace_id, user_id
    )
    return MixTaskStatus(**_TASKS[task_id])


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


@router.get("/looks/list")
async def list_color_looks():
    from app.services.video.color import PRESETS

    return {"items": [{"name": k, "available": v != "null"} for k, v in PRESETS.items()]}


@router.get("/aspects/list")
async def list_aspects():
    from app.services.video.aspect import ASPECT_PRESETS

    return {
        "items": [
            {"name": k, "width": v.width, "height": v.height}
            for k, v in ASPECT_PRESETS.items()
        ]
    }


@router.get("/features")
async def features_endpoint():
    """Runtime ffmpeg capability snapshot."""
    from app.services.video.features import detect_features

    f = detect_features()
    return {
        "has_drawtext": f.has_drawtext,
        "has_subtitles_filter": f.has_subtitles,
        "has_libass": f.has_libass,
        "can_burn_subtitles": f.can_burn_subtitles,
        "has_videotoolbox": f.has_videotoolbox,
    }


class AnalyzeBeatsRequest(BaseModel):
    audio_path: str


@router.post("/analyze/beats")
async def analyze_beats(body: AnalyzeBeatsRequest):
    from app.services.video.beat import detect_beats

    try:
        grid = await detect_beats(body.audio_path)
    except (FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "bpm": round(grid.bpm, 2),
        "onsets": [round(t, 3) for t in grid.onsets],
        "duration": round(grid.duration, 3),
        "confidence": round(grid.confidence, 3),
    }


class AnalyzeSubtitlesRequest(BaseModel):
    cues: list[CuePayload]
    cps_warn: float = 14.0
    cps_fail: float = 18.0


@router.post("/analyze/subtitles")
async def analyze_subtitles(body: AnalyzeSubtitlesRequest):
    from app.services.video.subtitle import score_subtitles

    cues = [Cue(c.start, c.end, c.text) for c in body.cues]
    report = score_subtitles(cues, cps_warn=body.cps_warn, cps_fail=body.cps_fail)
    return {
        "cues": report.cues,
        "max_cps": round(report.max_cps, 2),
        "avg_cps": round(report.avg_cps, 2),
        "is_ok": report.is_ok,
        "issues": [
            {
                "cue_index": i.cue_index,
                "severity": i.severity,
                "code": i.code,
                "message": i.message,
                "cps": round(i.cps, 2),
            }
            for i in report.issues
        ],
    }


class SelectorClipPayload(BaseModel):
    path: str
    duration: float
    is_hero: bool = False
    is_chapter_break: bool = False
    brightness: float = 0.5
    motion: float = 0.5
    score: float = 0.0


class SelectorRequest(BaseModel):
    target_total: float
    candidates: list[SelectorClipPayload]
    target_shot: float = 3.5
    min_shot: float = 1.4
    max_shot: float = 6.0
    must_include_hero: bool = True


@router.get("/tasks/{task_id}", response_model=MixTaskStatus)
async def get_task(task_id: str):
    payload = _TASKS.get(task_id)
    if not payload:
        raise HTTPException(status_code=404, detail="task not found")
    return MixTaskStatus(**payload)


@router.get("/tasks/{task_id}/download")
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


@router.post("/select-clips")
async def select_clips_endpoint(body: SelectorRequest):
    from app.services.video.selector import CandidateClip, select_clips

    pool = [
        CandidateClip(
            path=c.path,
            duration=c.duration,
            is_hero=c.is_hero,
            is_chapter_break=c.is_chapter_break,
            brightness=c.brightness,
            motion=c.motion,
            score=c.score,
        )
        for c in body.candidates
    ]
    plan = select_clips(
        pool,
        target_total=body.target_total,
        target_shot=body.target_shot,
        min_shot=body.min_shot,
        max_shot=body.max_shot,
        must_include_hero=body.must_include_hero,
    )
    return {
        "total_duration": plan.total_duration,
        "used_hero_count": plan.used_hero_count,
        "used_chapter_break_count": plan.used_chapter_break_count,
        "shots": [
            {
                "path": s.clip.path,
                "use_duration": s.use_duration,
                "start": s.start,
                "end": s.end,
                "is_hero": s.clip.is_hero,
            }
            for s in plan.shots
        ],
    }


async def _run_async_mix(
    task_id: str,
    body: MixVideoRequest,
    workspace_id: int | None = None,
    user_id: int | None = None,
) -> None:
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
                "subtitle_max_cps": (
                    round(result.subtitle_report.max_cps, 2)
                    if result.subtitle_report
                    else None
                ),
                "bgm_bpm": round(result.beat_grid.bpm, 2) if result.beat_grid else None,
                "warnings": result.warnings,
            }
        )
        # Fire-and-forget inbox event. Notifications are best-effort —
        # ``notify_video_generated`` swallows its own exceptions so a DB
        # hiccup here never marks a successful render as failed.
        if workspace_id is not None:
            await notifications_svc.notify_video_generated(
                workspace_id=workspace_id,
                user_id=user_id,
                task_id=task_id,
                project_id=body.project_id,
                duration=result.duration,
                preset=result.preset,
                output_path=str(result.output_path),
                runtime_seconds=result.runtime_seconds,
            )
            # Fan the same news out to webhooks + third-party integrations.
            # Wrapped in try/except so a misbehaving subscriber can never
            # corrupt the task status — the render has already succeeded.
            try:
                from app.services.integrations.events import emit_event

                await emit_event(
                    workspace_id=workspace_id,
                    event_type="video_generated",
                    payload={
                        "task_id": task_id,
                        "project_id": body.project_id,
                        "duration": result.duration,
                        "preset": result.preset,
                        "output_path": str(result.output_path),
                        "runtime_seconds": result.runtime_seconds,
                        "workspace_id": workspace_id,
                    },
                )
            except Exception:  # noqa: BLE001
                log.exception(
                    "emit_event(video_generated) failed for task=%s", task_id
                )
    except Exception as exc:  # noqa: BLE001 — surfaced via API
        log.exception("mix-video task %s failed", task_id)
        task.update({"status": "failed", "error": str(exc), "progress": 1.0})
        if workspace_id is not None:
            await notifications_svc.notify_video_failed(
                workspace_id=workspace_id,
                user_id=user_id,
                task_id=task_id,
                project_id=body.project_id,
                error=str(exc),
            )
            try:
                from app.services.integrations.events import emit_event

                await emit_event(
                    workspace_id=workspace_id,
                    event_type="video_failed",
                    payload={
                        "task_id": task_id,
                        "project_id": body.project_id,
                        "error": str(exc),
                        "workspace_id": workspace_id,
                    },
                )
            except Exception:  # noqa: BLE001
                log.exception(
                    "emit_event(video_failed) failed for task=%s", task_id
                )


__all__: list[str] = ["router"]
