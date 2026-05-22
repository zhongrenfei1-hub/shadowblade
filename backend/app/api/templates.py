"""GET /api/v1/templates — discovery and inspection of video-mix templates.

Backed by :mod:`app.services.template` — JSON files in
``<repo>/templates`` and the builtin set shipped with the package.

The list endpoint supports optional filtering so the frontend template
picker can group templates by aspect ratio, purpose, builtin/user, or
free-form tag:

    GET /api/v1/templates?aspect=9x16&purpose=product_demo&tag=tiktok&builtin=false
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.template import (
    Template,
    TemplateNotFoundError,
    list_templates,
    load_template,
)

router = APIRouter(prefix="/templates", tags=["templates"])


def _matches_aspect(preset_name: str | None, wanted: str) -> bool:
    """Match templates whose ``encode.preset`` ends with the aspect token.

    Examples:
        wanted="9x16"  → matches social_9x16, preview_360_9x16
        wanted="16x9"  → matches hero_16x9, social_16x9, broadcast_16x9
        wanted="1x1"   → matches social_1x1, square_1x1
    """
    if not preset_name:
        return False
    token = wanted.replace(":", "x").lower()
    return preset_name.lower().endswith(token)


@router.get("")
async def list_templates_endpoint(
    fresh: bool = Query(default=False, description="Bypass the in-process cache."),
    aspect: str | None = Query(
        default=None,
        description="Filter by aspect (9x16 / 16x9 / 1x1 / 4x5). Matches encode.preset suffix.",
    ),
    purpose: str | None = Query(
        default=None,
        description="Filter by extras.purpose (e.g. product_demo, product_demo_vertical).",
    ),
    tag: str | None = Query(
        default=None,
        description="Filter by exact tag membership.",
    ),
    builtin: bool | None = Query(
        default=None,
        description="True = only builtin templates; False = only user templates.",
    ),
):
    """List every discoverable template with one-line metadata + filters."""
    if fresh:
        from app.services.template.loader import _load_cached

        _load_cached.cache_clear()

    # Heavy-load only when a content filter is requested (aspect / purpose).
    need_content = aspect is not None or purpose is not None

    items: list[dict] = []
    for s in list_templates():
        if builtin is not None and s.builtin != builtin:
            continue
        if tag is not None and tag not in s.tags:
            continue
        entry = {
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "extends": s.extends,
            "tags": list(s.tags),
            "builtin": s.builtin,
            "source": s.source,
        }
        if need_content:
            try:
                tmpl = load_template(s.name)
            except (TemplateNotFoundError, RuntimeError, ValueError):
                continue
            if aspect is not None and not _matches_aspect(tmpl.encode.preset, aspect):
                continue
            if purpose is not None:
                tp = (tmpl.extras or {}).get("purpose")
                if tp != purpose:
                    continue
            entry["aspect"] = tmpl.encode.preset
            entry["purpose"] = (tmpl.extras or {}).get("purpose")
        items.append(entry)
    return {"items": items, "total": len(items)}


@router.get("/_schema")
async def template_schema_endpoint():
    """Return the Template Pydantic model as a JSON Schema document.

    Useful for the frontend template editor to drive form generation and
    client-side validation without duplicating the field definitions.
    """
    return Template.model_json_schema()


@router.get("/{name}")
async def get_template_endpoint(name: str, fresh: bool = Query(default=False)):
    """Return one template, fully resolved (``extends`` already merged)."""
    try:
        tmpl = load_template(name, fresh=fresh)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return tmpl.model_dump()


__all__ = ["router"]
