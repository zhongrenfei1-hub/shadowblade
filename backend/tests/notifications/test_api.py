"""Endpoint tests for /api/v1/notifications/*.

Hits the FastAPI app via TestClient. The shared conftest gives each test
a unique workspace/user id so writes can't leak between tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services import notifications as svc

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed(
    workspace_id: int,
    user_id: int | None,
    n: int = 3,
    *,
    type: str = "video_generated",
) -> list[int]:
    """Create ``n`` notifications, return their ids."""
    ids = []
    for i in range(n):
        row = await svc.create_notification(
            workspace_id=workspace_id,
            user_id=user_id,
            type=type,
            title=f"event {i}",
            message=f"msg {i}",
        )
        ids.append(row.id)
    return ids


# ---------------------------------------------------------------------------
# GET / (list)
# ---------------------------------------------------------------------------


async def test_list_empty(client: TestClient, auth_headers: dict[str, str]):
    r = client.get("/api/v1/notifications", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["unread"] == 0
    assert body["limit"] == 50
    assert body["offset"] == 0


async def test_list_returns_seeded_rows(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 4)
    r = client.get("/api/v1/notifications", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert body["unread"] == 4
    assert len(body["items"]) == 4
    # newest first
    assert body["items"][0]["title"] == "event 3"


async def test_list_unread_only_query(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 3)
    # Mark the middle one read
    await svc.mark_read(
        notification_id=ids[1],
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    r = client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers
    )
    body = r.json()
    assert body["total"] == 2
    titles = [it["title"] for it in body["items"]]
    assert "event 1" not in titles
    assert "event 0" in titles and "event 2" in titles


async def test_list_filter_by_category(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 1, type="video_generated")
    await _seed(test_workspace_id, test_user_id, 2, type="billing")
    r = client.get(
        "/api/v1/notifications?category=billing", headers=auth_headers
    )
    body = r.json()
    assert body["total"] == 2
    assert all(it["category"] == "billing" for it in body["items"])


async def test_list_filter_by_type(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 2, type="brand_kit_changed")
    await _seed(test_workspace_id, test_user_id, 3, type="video_generated")
    r = client.get(
        "/api/v1/notifications?type=brand_kit_changed", headers=auth_headers
    )
    body = r.json()
    assert body["total"] == 2
    assert all(it["type"] == "brand_kit_changed" for it in body["items"])


async def test_list_pagination(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 5)
    p1 = client.get(
        "/api/v1/notifications?limit=2&offset=0", headers=auth_headers
    ).json()
    p2 = client.get(
        "/api/v1/notifications?limit=2&offset=2", headers=auth_headers
    ).json()
    assert p1["total"] == 5 and p2["total"] == 5
    assert len(p1["items"]) == 2 and len(p2["items"]) == 2
    p1_ids = {it["id"] for it in p1["items"]}
    p2_ids = {it["id"] for it in p2["items"]}
    assert p1_ids.isdisjoint(p2_ids)


async def test_list_rejects_unknown_category(
    client: TestClient, auth_headers: dict[str, str]
):
    r = client.get(
        "/api/v1/notifications?category=not_a_thing", headers=auth_headers
    )
    # Pydantic schema rejects the Literal mismatch → 422
    assert r.status_code == 422


async def test_list_clamps_limit_via_validator(
    client: TestClient, auth_headers: dict[str, str]
):
    # Schema enforces max=200; > 200 → 422 from Query(le=200)
    r = client.get(
        "/api/v1/notifications?limit=500", headers=auth_headers
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /unread-count
# ---------------------------------------------------------------------------


async def test_unread_count_zero(
    client: TestClient, auth_headers: dict[str, str]
):
    r = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"unread": 0}


async def test_unread_count_after_seed(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 4)
    r = client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert r.json() == {"unread": 4}


async def test_unread_count_drops_after_read(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 3)
    await svc.mark_read(
        notification_id=ids[0],
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    r = client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert r.json() == {"unread": 2}


# ---------------------------------------------------------------------------
# GET /types
# ---------------------------------------------------------------------------


async def test_types_endpoint_exposes_enums(client: TestClient):
    r = client.get("/api/v1/notifications/types")
    assert r.status_code == 200
    body = r.json()
    assert "video_generated" in body["types"]
    assert "pipeline" in body["categories"]
    assert "done" in body["kinds"]
    # Mapping is exposed for the UI
    assert body["type_to_category"]["video_generated"] == "pipeline"
    assert body["type_to_kind"]["video_failed"] == "fail"


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------


async def test_get_one_returns_row(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 1)
    r = client.get(
        f"/api/v1/notifications/{ids[0]}", headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["id"] == ids[0]


async def test_get_one_404_for_missing(
    client: TestClient, auth_headers: dict[str, str]
):
    r = client.get("/api/v1/notifications/999999999", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{id}/read
# ---------------------------------------------------------------------------


async def test_mark_one_read(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 1)
    r = client.put(
        f"/api/v1/notifications/{ids[0]}/read", headers=auth_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["read"] is True
    assert body["read_at"] is not None


async def test_mark_one_read_404_for_missing(
    client: TestClient, auth_headers: dict[str, str]
):
    r = client.put(
        "/api/v1/notifications/999999999/read", headers=auth_headers
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /read-all
# ---------------------------------------------------------------------------


async def test_mark_all_read(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 5)
    r = client.put("/api/v1/notifications/read-all", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["updated"] == 5
    # Confirm via list
    listing = client.get(
        "/api/v1/notifications", headers=auth_headers
    ).json()
    assert listing["unread"] == 0


async def test_mark_all_read_category_scoped(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 2, type="video_generated")
    await _seed(test_workspace_id, test_user_id, 3, type="billing")
    r = client.put(
        "/api/v1/notifications/read-all?category=billing",
        headers=auth_headers,
    )
    assert r.json()["updated"] == 3
    # Pipeline rows still unread
    listing = client.get(
        "/api/v1/notifications", headers=auth_headers
    ).json()
    assert listing["unread"] == 2


# ---------------------------------------------------------------------------
# PUT /{id}/archive
# ---------------------------------------------------------------------------


async def test_archive_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 1)
    r = client.put(
        f"/api/v1/notifications/{ids[0]}/archive", headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["archived"] is True
    # Default listing should hide it
    listing = client.get(
        "/api/v1/notifications", headers=auth_headers
    ).json()
    assert listing["total"] == 0
    # include_archived=true brings it back
    listing2 = client.get(
        "/api/v1/notifications?include_archived=true", headers=auth_headers
    ).json()
    assert listing2["total"] == 1


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------


async def test_delete_removes_row(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 1)
    r = client.delete(
        f"/api/v1/notifications/{ids[0]}", headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "id": ids[0]}
    # Second delete → 404
    r2 = client.delete(
        f"/api/v1/notifications/{ids[0]}", headers=auth_headers
    )
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# Permission isolation — cross-workspace + cross-user
# ---------------------------------------------------------------------------


async def test_cross_workspace_cannot_see_rows(
    client: TestClient,
    test_workspace_id: int,
    test_user_id: int,
):
    """Putting Workspace A's id in the header must not surface workspace B rows."""
    await _seed(test_workspace_id, test_user_id, 2)
    # Look at a *different* workspace — same user id
    other_headers = {
        "X-Workspace-Id": str(test_workspace_id + 100_001),
        "X-User-Id": str(test_user_id),
    }
    body = client.get("/api/v1/notifications", headers=other_headers).json()
    assert body["total"] == 0


async def test_cross_workspace_cannot_mutate_rows(
    client: TestClient,
    test_workspace_id: int,
    test_user_id: int,
):
    ids = await _seed(test_workspace_id, test_user_id, 1)
    # Try marking it read using a different workspace id
    other_headers = {
        "X-Workspace-Id": str(test_workspace_id + 100_001),
        "X-User-Id": str(test_user_id),
    }
    r = client.put(
        f"/api/v1/notifications/{ids[0]}/read", headers=other_headers
    )
    assert r.status_code == 404


async def test_cross_user_cannot_see_rows(
    client: TestClient,
    test_workspace_id: int,
    test_user_id: int,
):
    await _seed(test_workspace_id, test_user_id, 2)
    other_headers = {
        "X-Workspace-Id": str(test_workspace_id),
        "X-User-Id": str(test_user_id + 100_001),
    }
    body = client.get("/api/v1/notifications", headers=other_headers).json()
    assert body["total"] == 0


async def test_workspace_broadcasts_visible_when_unauth(
    client: TestClient,
    test_workspace_id: int,
):
    """A row with user_id=NULL is visible to any authed user in the workspace
    (also visible to the "no X-User-Id" caller).
    """
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=None,
        type="billing",
        title="broadcast",
    )
    headers_no_user = {"X-Workspace-Id": str(test_workspace_id)}
    body = client.get("/api/v1/notifications", headers=headers_no_user).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "broadcast"
