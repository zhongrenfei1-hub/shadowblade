"""Shared fixtures for analytics tests.

Mirrors the workbench / brand-kit / settings pattern: each test gets a
throw-away SQLite DB under ``tmp_path``, the FastAPI ``get_db`` is
overridden to bind to it, and the in-memory TTL cache is reset between
tests so cache-hit tests don't poison the next case's freshness.

Two seed fixtures are provided:

* ``empty_db`` — just the isolated client with no rows. Tests for
  "empty workspace looks like ___" can request this directly.
* ``seeded_analytics`` — a fairly realistic distribution of projects,
  render tasks, templates, brand kits, users and assets, spread across
  two workspaces (1 and 2) so cross-tenant isolation has something to
  assert against. Returns a dict with the ids the test can refer back
  to.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import deps as deps_module
from app.core import config as config_module
from app.core.db import Base, _apply_dev_migrations_sync


# ---------------------------------------------------------------------------
# Isolation primitives
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def isolated_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Throw-away async engine on tmp SQLite; storage_root rerouted to tmp."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(
        config_module.settings, "storage_root", str(storage_root), raising=True
    )

    from app import models  # noqa: F401 — registers all tables on Base.metadata
    from app.models import (  # noqa: F401
        asset,
        brand_kit,
        invitation,
        job,
        membership,
        project,
        render,
        template,
        user,
        workspace,
    )

    engine = create_async_engine(db_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(_apply_dev_migrations_sync)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def isolated_db(isolated_engine):
    """``TestClient`` bound to the isolated engine via dependency override.

    Also flushes the analytics TTL cache before/after so cached responses
    from one test never leak into another (cached=True would suddenly
    appear out of nowhere otherwise).
    """
    from app.main import app
    from app.services.analytics import get_analytics_cache

    session_factory = async_sessionmaker(isolated_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    cache = get_analytics_cache()
    cache.invalidate()  # baseline

    app.dependency_overrides[deps_module.get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps_module.get_db, None)
        cache.invalidate()


@pytest.fixture
def workspace_headers() -> dict[str, str]:
    """Headers selecting the default demo workspace (id=1)."""
    return {"X-Workspace-Id": "1"}


@pytest.fixture
def other_workspace_headers() -> dict[str, str]:
    """Headers pointing at workspace 2 — used for cross-tenant tests."""
    return {"X-Workspace-Id": "2"}


@pytest.fixture
def user_headers(workspace_headers: dict[str, str]) -> dict[str, str]:
    """Workspace + user headers (most analytics calls don't require it)."""
    return {**workspace_headers, "X-User-Id": "1"}


# ---------------------------------------------------------------------------
# Seed factories — exposed as plain functions so per-test seeding works
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def empty_db(isolated_engine):
    """Convenience alias for tests that just need an empty isolated DB."""
    return isolated_engine


@pytest_asyncio.fixture
async def seeded_analytics(isolated_engine) -> dict:
    """Insert a realistic dataset across two workspaces.

    Layout — chosen so every endpoint has something non-trivial to
    assert against, including edge cases (failed renders, archived
    projects, unused brand kits, multi-template usage)::

        workspace 1 (analytics target)
          users:  u1 Ada Chen, u2 Bo Lin, u3 Carla Wu
          templates seeded:
            vlog_warm (marketing), tutorial_steady (training),
            product_demo_vertical (product_demo), social_punchy (social)
          brand kits:
            bk1 workspace-active, bk2 workspace-inactive,
            bk3 user-scope (owner=u2)
          projects (12 total): mix of purposes/statuses, all created
            in the last 5 days so the 7d window captures them
          render_tasks (20+ total): pattern of succeeded/failed/running
            queued over the last 5 days so the trend chart has shape
          assets: 2 images + 1 video for storage_bytes
        workspace 2 (isolation foil)
          projects (3), render_tasks (5) — must never appear in
          workspace 1's queries.

    Returns a dict with the inserted ids so tests can refer back to
    them without re-querying.
    """
    from app.models import (
        Asset,
        BrandKit,
        Project,
        RenderTask,
        Template,
        User,
        Workspace,
    )

    # We anchor everything against ``now`` so the 7d window catches the
    # whole seed set deterministically. Naive UTC matches what server
    # defaults produce, so comparisons line up cleanly.
    now = datetime.utcnow().replace(microsecond=0)

    session_factory = async_sessionmaker(isolated_engine, expire_on_commit=False)

    async with session_factory() as s:
        # ----- workspaces ------------------------------------------------
        ws1 = Workspace(id=1, slug="acme", name="Acme Studio", plan="growth")
        ws2 = Workspace(id=2, slug="other", name="Other Tenant", plan="growth")
        s.add_all([ws1, ws2])

        # ----- users (workspace 1) --------------------------------------
        u1 = User(
            id=1,
            email="ada@acme.com",
            full_name="Ada Chen",
            hashed_password="x",
            last_login_at=now - timedelta(hours=1),
        )
        u2 = User(
            id=2,
            email="bo@acme.com",
            full_name="Bo Lin",
            hashed_password="x",
            last_login_at=now - timedelta(days=1),
        )
        u3 = User(
            id=3,
            email="carla@acme.com",
            full_name="Carla Wu",
            hashed_password="x",
            last_login_at=now - timedelta(days=8),  # outside 7d window
        )
        s.add_all([u1, u2, u3])

        # ----- templates ------------------------------------------------
        templates = [
            Template(
                slug="vlog_warm",
                name="Warm Vlog",
                category="marketing",
                preview_url="/preview/vlog_warm.png",
            ),
            Template(
                slug="tutorial_steady",
                name="Steady Tutorial",
                category="training",
                preview_url="/preview/tutorial_steady.png",
            ),
            Template(
                slug="product_demo_vertical",
                name="Vertical Product Demo",
                category="product_demo",
                preview_url="/preview/product_demo_vertical.png",
            ),
            Template(
                slug="social_punchy",
                name="Punchy Social",
                category="social",
                preview_url="/preview/social_punchy.png",
            ),
        ]
        s.add_all(templates)

        # ----- brand kits (workspace 1) ---------------------------------
        bk1 = BrandKit(
            workspace_id=1,
            scope="workspace",
            owner_id=None,
            is_active=True,
            name="Acme Default",
        )
        bk2 = BrandKit(
            workspace_id=1,
            scope="workspace",
            owner_id=None,
            is_active=False,
            name="Acme Legacy",
        )
        bk3 = BrandKit(
            workspace_id=1,
            scope="user",
            owner_id=2,
            is_active=True,
            name="Bo's Personal Kit",
        )
        # workspace-2 kit, must never appear in workspace-1 listings
        bk4 = BrandKit(
            workspace_id=2,
            scope="workspace",
            owner_id=None,
            is_active=True,
            name="Other Tenant Kit",
        )
        s.add_all([bk1, bk2, bk3, bk4])
        await s.flush()

        # ----- projects (workspace 1) -----------------------------------
        # Spread created_at within the 7-day window. We pre-stamp
        # created_at because SQLite's server_default(now) would always
        # use the current wall-clock and we'd lose deterministic ordering.
        ws1_owners = [u1.id, u2.id, u1.id, u3.id, u2.id, u1.id, u2.id, u1.id,
                      u2.id, u1.id, u1.id, u2.id]
        ws1_purposes = ["marketing", "marketing", "marketing", "training",
                        "training", "product_demo", "product_demo",
                        "product_demo", "social", "social", "marketing",
                        "training"]
        ws1_template_slugs = [
            "vlog_warm", "vlog_warm", "vlog_warm",
            "tutorial_steady", "tutorial_steady",
            "product_demo_vertical", "product_demo_vertical",
            "product_demo_vertical",
            "social_punchy", "social_punchy",
            "vlog_warm", "tutorial_steady",
        ]
        ws1_statuses = ["done", "done", "rendering", "review", "done",
                        "done", "scripting", "rendering",
                        "done", "draft", "archived", "done"]
        ws1_brand_kits = [bk1.id, bk1.id, bk1.id, bk1.id, bk3.id,
                          bk3.id, bk1.id, bk1.id, bk1.id, None, bk1.id, bk3.id]

        projects: list[Project] = []
        for i in range(12):
            # Distribute over 6 days; first 6 projects today, others spread.
            offset_hours = i * 12  # 0, 12, 24, …, 132
            projects.append(
                Project(
                    workspace_id=1,
                    owner_id=ws1_owners[i],
                    name=f"Project {i + 1}",
                    purpose=ws1_purposes[i],
                    duration_seconds=15 + i * 5,
                    aspect_ratio="9:16" if i % 2 == 0 else "16:9",
                    status=ws1_statuses[i],
                    config={
                        "template": ws1_template_slugs[i],
                        "brand_kit_id": ws1_brand_kits[i],
                    },
                    created_at=now - timedelta(hours=offset_hours),
                    updated_at=now - timedelta(hours=offset_hours),
                )
            )

        # Workspace 2 projects — same model but isolated
        ws2_projects = [
            Project(
                workspace_id=2,
                owner_id=1,
                name=f"Other Project {i + 1}",
                purpose="marketing",
                duration_seconds=30,
                aspect_ratio="16:9",
                status="done",
                config={"template": "vlog_warm"},
                created_at=now - timedelta(hours=i * 12),
                updated_at=now - timedelta(hours=i * 12),
            )
            for i in range(3)
        ]

        s.add_all(projects + ws2_projects)
        await s.flush()

        # ----- render tasks (workspace 1) -------------------------------
        # Pattern: most projects have 1-3 renders; first 3 have a failed one.
        renders: list[RenderTask] = []

        def add_render(
            project: Project,
            status: str,
            queued_offset_hours: int,
            runtime_seconds: float,
            finished_offset_hours: int | None = None,
        ) -> None:
            queued = now - timedelta(hours=queued_offset_hours)
            finished = (
                now - timedelta(hours=finished_offset_hours)
                if finished_offset_hours is not None
                else None
            )
            renders.append(
                RenderTask(
                    project_id=project.id,
                    priority="normal",
                    status=status,
                    progress=1.0 if status == "succeeded" else 0.5,
                    estimated_seconds=runtime_seconds,
                    queued_at=queued,
                    started_at=queued + timedelta(minutes=1),
                    finished_at=finished,
                )
            )

        # Project 1: 2 succeeded + 1 failed
        add_render(projects[0], "succeeded", 1, 18.0, 0)
        add_render(projects[0], "failed", 2, 3.5, 1)
        add_render(projects[0], "succeeded", 3, 22.0, 2)
        # Project 2-5: 1-2 succeeded each
        add_render(projects[1], "succeeded", 14, 25.0, 13)
        add_render(projects[1], "succeeded", 26, 24.5, 25)
        add_render(projects[2], "running", 1, 0.0)  # currently rendering
        add_render(projects[3], "succeeded", 38, 60.0, 37)
        add_render(projects[3], "succeeded", 50, 58.0, 49)
        add_render(projects[4], "succeeded", 62, 55.0, 61)
        # Project 6: 1 success, 1 fail
        add_render(projects[5], "succeeded", 74, 14.0, 73)
        add_render(projects[5], "failed", 75, 4.0, 74)
        # Project 7-12: scatter
        add_render(projects[6], "queued", 1, 0.0)
        add_render(projects[7], "running", 5, 0.0)
        add_render(projects[8], "succeeded", 98, 17.0, 97)
        add_render(projects[9], "succeeded", 110, 12.5, 109)
        add_render(projects[10], "succeeded", 122, 35.0, 121)  # archived project
        add_render(projects[11], "succeeded", 134, 80.0, 133)

        # ----- render tasks (workspace 2) -------------------------------
        for i, p in enumerate(ws2_projects):
            renders.append(
                RenderTask(
                    project_id=p.id,
                    priority="normal",
                    status="succeeded",
                    progress=1.0,
                    estimated_seconds=20.0,
                    queued_at=now - timedelta(hours=i * 12 + 1),
                    finished_at=now - timedelta(hours=i * 12),
                )
            )

        s.add_all(renders)

        # ----- assets ---------------------------------------------------
        s.add_all([
            Asset(
                workspace_id=1, project_id=projects[0].id, kind="video",
                name="hero.mp4", url="/static/hero.mp4", size_bytes=20_000_000,
            ),
            Asset(
                workspace_id=1, project_id=projects[1].id, kind="image",
                name="cover.png", url="/static/cover.png", size_bytes=400_000,
            ),
            Asset(
                workspace_id=1, project_id=None, kind="logo",
                name="brand.svg", url="/static/brand.svg", size_bytes=15_000,
            ),
            # Workspace 2 — should not affect workspace 1 storage_bytes
            Asset(
                workspace_id=2, project_id=ws2_projects[0].id, kind="video",
                name="other.mp4", url="/static/other.mp4", size_bytes=99_999_999,
            ),
        ])

        await s.commit()

        return {
            "now": now,
            "ws1_project_ids": [p.id for p in projects],
            "ws1_user_ids": [u1.id, u2.id, u3.id],
            "ws1_brand_kit_ids": [bk1.id, bk2.id, bk3.id],
            "ws1_template_slugs": [t.slug for t in templates],
            "ws1_storage_bytes": 20_000_000 + 400_000 + 15_000,
            "ws1_renders_total": len(renders) - len(ws2_projects),
            "ws1_succeeded": sum(1 for r in renders[: len(renders) - len(ws2_projects)] if r.status == "succeeded"),
            "ws1_failed": sum(1 for r in renders[: len(renders) - len(ws2_projects)] if r.status == "failed"),
            "ws2_project_ids": [p.id for p in ws2_projects],
        }
