"""POST /api/v1/stock — fetch real stock footage from Pexels or any URL."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.stock.pexels import pexels_download, pexels_search
from app.services.stock.searcher import search_and_download
from app.services.stock.youtube import ytdlp_download

log = logging.getLogger("shadowblade.api.stock")
router = APIRouter(prefix="/stock", tags=["stock"])


def _stock_dir(source: str) -> Path:
    p = Path(settings.storage_root) / "stock" / source
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── /stock/pexels/search ───────────────────────────────────────────────


class PexelsSearchRequest(BaseModel):
    query: str
    per_page: int = Field(default=8, ge=1, le=30)
    orientation: str = "portrait"
    size: str = "medium"
    api_key: str | None = Field(
        default=None,
        description="Optional inline override; otherwise read from PEXELS_API_KEY env",
    )


class PexelsClipPayload(BaseModel):
    id: int
    url: str
    download_url: str
    width: int
    height: int
    duration: int
    aspect: str
    photographer: str
    photographer_url: str


@router.post("/pexels/search")
async def pexels_search_endpoint(body: PexelsSearchRequest):
    try:
        items = await pexels_search(
            body.query,
            per_page=body.per_page,
            orientation=body.orientation,
            size=body.size,
            api_key=body.api_key,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "items": [
            PexelsClipPayload(
                id=c.id,
                url=c.url,
                download_url=c.download_url,
                width=c.width,
                height=c.height,
                duration=c.duration,
                aspect=c.aspect,
                photographer=c.photographer,
                photographer_url=c.photographer_url,
            ).model_dump()
            for c in items
        ]
    }


# ── /stock/pexels/auto-download ────────────────────────────────────────


class PexelsAutoRequest(BaseModel):
    query: str
    count: int = Field(default=3, ge=1, le=10)
    orientation: str = "portrait"
    max_seconds: float = Field(default=6.0, ge=2, le=20)
    api_key: str | None = None


class PexelsAutoResponse(BaseModel):
    query: str
    paths: list[str]
    relative_urls: list[str]
    photographers: list[str]


@router.post("/pexels/auto", response_model=PexelsAutoResponse)
async def pexels_auto_download(body: PexelsAutoRequest):
    """Search + download the top N matching Pexels clips in one shot."""
    try:
        results = await pexels_search(
            body.query,
            per_page=body.count + 4,
            orientation=body.orientation,
            api_key=body.api_key,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not results:
        raise HTTPException(
            status_code=404, detail=f"no Pexels videos matched query: {body.query!r}"
        )
    out_dir = _stock_dir("pexels")
    paths: list[str] = []
    rels: list[str] = []
    creds: list[str] = []
    for clip in results[: body.count]:
        try:
            p = await pexels_download(clip, out_dir, max_seconds=body.max_seconds)
        except RuntimeError as exc:
            log.warning("skip pexels clip %s: %s", clip.id, exc)
            continue
        paths.append(str(p))
        rels.append(f"/static/storage/{p.relative_to(Path(settings.storage_root))}")
        creds.append(clip.photographer)
        if len(paths) >= body.count:
            break
    if not paths:
        raise HTTPException(status_code=502, detail="all pexels downloads failed")
    return PexelsAutoResponse(
        query=body.query,
        paths=paths,
        relative_urls=rels,
        photographers=creds,
    )


# ── /stock/from-url (yt-dlp) ───────────────────────────────────────────


class FromUrlRequest(BaseModel):
    url: str
    sections: str | None = Field(
        default=None,
        description="Time range, yt-dlp syntax e.g. '*0:00-0:08' or '0:20-0:30'",
    )
    max_height: int = 1920
    cookies_browser: str | None = None


class FromUrlResponse(BaseModel):
    path: str
    relative_url: str
    title: str
    duration: float
    width: int
    height: int


@router.post("/from-url", response_model=FromUrlResponse)
async def stock_from_url(body: FromUrlRequest):
    out_dir = _stock_dir("ytdlp")
    try:
        clip = await ytdlp_download(
            body.url,
            out_dir,
            sections=body.sections,
            max_height=body.max_height,
            cookies_browser=body.cookies_browser,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rel = clip.path.relative_to(Path(settings.storage_root))
    return FromUrlResponse(
        path=str(clip.path),
        relative_url=f"/static/storage/{rel}",
        title=clip.title,
        duration=clip.duration,
        width=clip.width,
        height=clip.height,
    )


# ── /stock/search (keyword crawl — no API key) ─────────────────────────


class SearchRequest(BaseModel):
    keyword: str
    count: int = Field(default=3, ge=1, le=8)
    max_seconds: float = Field(default=6.0, ge=2, le=15)
    sources: list[str] = Field(
        default_factory=lambda: ["youtube", "archive"],
        description="Try in order; falls back when a source returns no results",
    )


class SearchResponse(BaseModel):
    keyword: str
    paths: list[str]
    relative_urls: list[str]
    titles: list[str]
    sources: list[str]


@router.post("/search", response_model=SearchResponse)
async def stock_search(body: SearchRequest):
    """Keyword → real clips. No API key. Uses yt-dlp search + archive.org."""
    out_dir = _stock_dir("search")
    try:
        clips = await search_and_download(
            body.keyword,
            out_dir,
            count=body.count,
            max_seconds=body.max_seconds,
            sources=tuple(body.sources),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SearchResponse(
        keyword=body.keyword,
        paths=[str(c.path) for c in clips],
        relative_urls=[
            f"/static/storage/{c.path.relative_to(Path(settings.storage_root))}" for c in clips
        ],
        titles=[c.title for c in clips],
        sources=[c.source for c in clips],
    )


# ── /stock/status ──────────────────────────────────────────────────────


@router.get("/status")
async def stock_status():
    """Tells the frontend which sources are configured."""
    from app.services.stock.youtube import has_ytdlp

    has_pexels = bool(
        os.environ.get("PEXELS_API_KEY") or os.environ.get("SHADOWBLADE_PEXELS_KEY")
    )
    return {
        "pexels": {
            "configured": has_pexels,
            "hint": "Set PEXELS_API_KEY env var (get key at https://www.pexels.com/api/)",
        },
        "ytdlp": {
            "configured": has_ytdlp(),
            "hint": "pip install yt-dlp",
        },
    }


__all__ = ["router"]
