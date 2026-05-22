"""POST /api/v1/keys — list / set / delete / test provider API keys.

Persists to ``~/.shadowblade/secrets.json`` and mirrors into ``os.environ``
so the rest of the app keeps reading via the standard env var names.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import secrets

router = APIRouter(prefix="/keys", tags=["keys"])


class KeyRow(BaseModel):
    slug: str
    label: str
    env: str
    hint: str
    configured: bool
    source: str | None
    masked: str


class KeyListResponse(BaseModel):
    items: list[KeyRow]


@router.get("", response_model=KeyListResponse)
async def list_keys():
    """Return every known provider + whether a key is set (masked)."""
    return KeyListResponse(items=secrets.status())


class SetKeyRequest(BaseModel):
    slug: str = Field(..., description="One of: pexels / openai / deepseek / anthropic")
    value: str = Field(..., min_length=4)


@router.post("", response_model=KeyRow)
async def set_key(body: SetKeyRequest):
    try:
        return secrets.set_key(body.slug, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{slug}", response_model=KeyRow)
async def delete_key(slug: str):
    try:
        return secrets.delete_key(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{slug}/test")
async def test_key(slug: str):
    try:
        return await secrets.test_key(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


__all__ = ["router"]
