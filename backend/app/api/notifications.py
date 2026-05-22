"""REST endpoints for the workspace notification inbox.

Five routes — mirror the fastapi-fullstack-template *user-inbox* pattern
and the React mock in ``frontend-next/app/(app)/notifications/page.tsx``:

* ``GET    /api/v1/notifications``                — list (pagination + filters)
* ``GET    /api/v1/notifications/unread-count``   — badge counter for the header
* ``PUT    /api/v1/notifications/{id}/read``      — flip one row to read=True
* ``PUT    /api/v1/notifications/read-all``       — flip everything to read=True
* ``DELETE /api/v1/notifications/{id}``           — hard-remove (UI dismiss)

Plus two convenience routes the React UI needs:

* ``PUT    /api/v1/notifications/{id}/archive``   — soft-archive (keeps audit)
* ``GET    /api/v1/notifications/types``          — enumerate type/category/kind
  for the frontend's filter chip dropdown.

Permission model — workspace-scoped, user-scoped read:
    Every route resolves ``workspace_id`` from the ``X-Workspace-Id``
    header (falling back to the demo workspace) and ``user_id`` from the
    ``X-User-Id`` header. A user can only read/mutate notifications
    addressed to them or to nobody-in-particular (``user_id IS NULL``,
    i.e. workspace broadcasts). Cross-workspace access is impossible
    because every query is filtered by ``workspace_id``.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user_id,
    get_current_workspace_id,
    get_db,
)
from app.models.notification import (
    NOTIFICATION_CATEGORIES,
    NOTIFICATION_KINDS,
    NOTIFICATION_TYPES,
)
from app.schemas.notification import (
    MarkResponse,
    NotificationCategory,
    NotificationList,
    NotificationRead,
    NotificationType,
    UnreadCountResponse,
)
from app.services import notifications as svc

log = logging.getLogger("shadowblade.api.notifications")
router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=NotificationList)
async def list_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    category: NotificationCategory | None = Query(default=None),
    type: NotificationType | None = Query(default=None),
    include_archived: bool = Query(default=False),
):
    """List notifications for the caller, newest first.

    The envelope carries ``total`` (rows matching the current filter,
    before pagination) and ``unread`` (rows still unread for the caller
    across **all** categories, so the header badge stays correct even
    while a category tab is selected).
    """
    try:
        items, total, unread = await svc.list_notifications(
            workspace_id=workspace_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            category=category,
            type=type,
            include_archived=include_archived,
            db=db,
        )
    except ValueError as exc:  # bad enum value — schema layer already filtered
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return NotificationList(
        items=[NotificationRead.model_validate(it) for it in items],
        total=total,
        unread=unread,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Lightweight counter for the header badge.

    Always reflects the *user's own* unread count when ``X-User-Id`` is
    present; falls back to the workspace-wide unread otherwise.
    """
    count = await svc.unread_count(
        workspace_id=workspace_id, user_id=user_id, db=db
    )
    return UnreadCountResponse(unread=count)


@router.get("/types")
async def list_types_endpoint():
    """Enumerate the closed enums the UI filter dropdowns need.

    Cheaper than reading the OpenAPI schema and works offline.
    """
    return {
        "types": list(NOTIFICATION_TYPES),
        "categories": list(NOTIFICATION_CATEGORIES),
        "kinds": list(NOTIFICATION_KINDS),
        "type_to_category": svc.TYPE_CATEGORY,
        "type_to_kind": svc.TYPE_DEFAULT_KIND,
    }


@router.get("/{notification_id}", response_model=NotificationRead)
async def get_one_endpoint(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Read one notification — used by deep-links from email/push.

    Permission check mirrors the list: caller can read rows addressed to
    them or to ``user_id IS NULL`` broadcasts in their workspace.
    """
    items, _total, _unread = await svc.list_notifications(
        workspace_id=workspace_id,
        user_id=user_id,
        limit=1,
        offset=0,
        include_archived=True,
        db=db,
    )
    # The list helper already enforces (workspace, user) scoping; we now
    # re-fetch by id with the same constraint to avoid leaking an id from
    # another user's inbox.
    from sqlalchemy import select

    from app.models.notification import Notification

    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.workspace_id == workspace_id,
    )
    if user_id is not None:
        stmt = stmt.where(
            (Notification.user_id == user_id) | (Notification.user_id.is_(None))
        )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return NotificationRead.model_validate(row)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


@router.put("/read-all", response_model=MarkResponse)
async def mark_all_read_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    category: NotificationCategory | None = Query(default=None),
):
    """Flip everything (or one category) to read=True for the caller.

    ``category`` lets the UI "mark this tab as read" without affecting
    the others — matches the React mock's per-tab control.
    """
    try:
        n = await svc.mark_all_read(
            workspace_id=workspace_id,
            user_id=user_id,
            category=category,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MarkResponse(ok=True, updated=n)


@router.put("/{notification_id}/read", response_model=NotificationRead)
async def mark_one_read_endpoint(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    row = await svc.mark_read(
        notification_id=notification_id,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return NotificationRead.model_validate(row)


@router.put("/{notification_id}/archive", response_model=NotificationRead)
async def archive_endpoint(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Soft-archive — row stays for audit but vanishes from the default list."""
    row = await svc.archive_notification(
        notification_id=notification_id,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return NotificationRead.model_validate(row)


@router.delete("/{notification_id}", status_code=200)
async def delete_endpoint(
    notification_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Hard-delete one notification — the UI's destructive dismiss."""
    ok = await svc.delete_notification(
        notification_id=notification_id,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="notification not found")
    return {"ok": True, "id": notification_id}


__all__ = ["router"]
