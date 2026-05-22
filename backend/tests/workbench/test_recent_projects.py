"""Tests for GET /api/v1/workbench/recent-projects.

This endpoint is the Workbench's "pick up where you left off" surface. The
contract is: order by updated_at desc, scope by workspace, bound limit,
and decorate each card with the deep-link URLs the frontend uses.
"""

from __future__ import annotations


def test_recent_projects_empty(isolated_db, workspace_headers):
    """No projects → empty list, total=0, but full envelope shape."""
    r = isolated_db.get(
        "/api/v1/workbench/recent-projects", headers=workspace_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["workspace_id"] == 1
    assert body["limit"] == 8


def test_recent_projects_orders_by_updated_at_desc(
    isolated_db, workspace_headers, seed_projects
):
    """Most-recently-updated project comes first."""
    body = isolated_db.get(
        "/api/v1/workbench/recent-projects", headers=workspace_headers
    ).json()
    names = [p["name"] for p in body["items"]]
    # seed_projects: p1 (now) > p2 (-2h) > p3 (-1d), p4 belongs to ws=2.
    assert names == ["春季产品发布", "AI Copilot 60 秒演示", "入职培训训练营"]


def test_recent_projects_excludes_other_workspaces(
    isolated_db, seed_projects
):
    """Workspace 2's project never appears in workspace 1's list."""
    ws1 = isolated_db.get(
        "/api/v1/workbench/recent-projects",
        headers={"X-Workspace-Id": "1"},
    ).json()
    ws2 = isolated_db.get(
        "/api/v1/workbench/recent-projects",
        headers={"X-Workspace-Id": "2"},
    ).json()

    ws1_ids = {p["id"] for p in ws1["items"]}
    ws2_ids = {p["id"] for p in ws2["items"]}
    assert ws1_ids.isdisjoint(ws2_ids)
    assert len(ws2["items"]) == 1
    assert ws2["items"][0]["name"] == "另一工作区项目"


def test_recent_projects_decorates_with_deep_links(
    isolated_db, workspace_headers, seed_projects
):
    """Each card carries href_open + href_detail so cards are click-ready."""
    body = isolated_db.get(
        "/api/v1/workbench/recent-projects", headers=workspace_headers
    ).json()
    top = body["items"][0]
    assert top["href_open"].startswith("/studio.html?project=")
    assert top["href_detail"].startswith("/project-detail.html?id=")
    # Numeric id should round-trip into both links.
    assert str(top["id"]) in top["href_open"]
    assert str(top["id"]) in top["href_detail"]


def test_recent_projects_respects_limit(
    isolated_db, workspace_headers, seed_projects
):
    """Caller can ask for fewer rows than the default."""
    body = isolated_db.get(
        "/api/v1/workbench/recent-projects?limit=2",
        headers=workspace_headers,
    ).json()
    assert body["limit"] == 2
    assert len(body["items"]) == 2


def test_recent_projects_rejects_oversized_limit(
    isolated_db, workspace_headers
):
    """Pydantic ge=1 le=24 enforces the bound at the boundary."""
    r = isolated_db.get(
        "/api/v1/workbench/recent-projects?limit=999",
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_recent_projects_truncates_long_briefs(
    isolated_db, workspace_headers, isolated_engine
):
    """A 500-char brief gets summarised so cards don't blow out the layout."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.project import Project

    session_factory = async_sessionmaker(isolated_engine, expire_on_commit=False)
    long_brief = "细致的需求拆解 " * 80

    async def _insert():
        async with session_factory() as s:
            s.add(
                Project(
                    workspace_id=1, owner_id=1, name="长 brief 项目",
                    purpose="marketing", brief=long_brief,
                    aspect_ratio="9:16", duration_seconds=30,
                    voice="alloy-en-female", status="draft",
                )
            )
            await s.commit()

    import asyncio

    asyncio.run(_insert())

    body = isolated_db.get(
        "/api/v1/workbench/recent-projects", headers=workspace_headers
    ).json()
    top = body["items"][0]
    assert top["name"] == "长 brief 项目"
    # 160 chars + ellipsis.
    assert len(top["brief"]) <= 161
    assert top["brief"].endswith("…")
