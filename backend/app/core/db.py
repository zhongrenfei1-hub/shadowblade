"""Async SQLAlchemy 2.0 engine, session factory, and dev-mode auto-migrator.

Production deployments will swap the auto-migration helper for Alembic;
during development we keep startup zero-config by detecting drifted
columns at init time and applying ``ALTER TABLE`` for the additive cases.
The drop-and-recreate branch only runs when the existing table is so
shallow that adding columns is more work than starting fresh (zero rows
plus more than one missing column).
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

log = logging.getLogger("shadowblade.db")

engine = create_async_engine(settings.database_url, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


# Tables whose schema is allowed to drift in dev. For each one we list the
# columns the application expects to exist; missing columns trigger ALTER
# TABLE statements (or drop-and-recreate if the gap is huge and the table
# is empty). The default values mirror the ORM defaults so older rows pick
# up sensible values automatically.
_DEV_MIGRATIONS: dict[str, dict[str, str]] = {
    "brand_kits": {
        "scope": "VARCHAR(16) NOT NULL DEFAULT 'workspace'",
        "owner_id": "INTEGER",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "secondary_color": "VARCHAR(9) NOT NULL DEFAULT '#F5F7FB'",
        "neutral_color": "VARCHAR(9) NOT NULL DEFAULT '#5A6B85'",
        "background_color": "VARCHAR(9) NOT NULL DEFAULT '#FFFFFF'",
        "font_family": "VARCHAR(128) NOT NULL DEFAULT 'Inter'",
        "logo_mono_url": "VARCHAR(512)",
        "watermark_text": "VARCHAR(64)",
        "watermark_opacity": "FLOAT NOT NULL DEFAULT 0.78",
        "watermark_position": "VARCHAR(8) NOT NULL DEFAULT 'br'",
        "watermark_width_pct": "FLOAT NOT NULL DEFAULT 0.16",
        "target_lufs": "FLOAT NOT NULL DEFAULT -14.0",
        "target_tp": "FLOAT NOT NULL DEFAULT -1.0",
        "bgm_gain_db": "FLOAT NOT NULL DEFAULT -14.0",
        "subtitle_size": "INTEGER NOT NULL DEFAULT 64",
        "subtitle_margin_v": "INTEGER NOT NULL DEFAULT 96",
        "default_template_name": "VARCHAR(64)",
        "custom_css_snippet": "TEXT",
        "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    },
    # Team / Organization additions — all nullable so existing demo rows
    # survive the upgrade. The ``users`` and ``workspaces`` tables can
    # already be populated in dev DBs, so we ALTER instead of drop+create.
    "workspaces": {
        "owner_id": "INTEGER",
        "description": "TEXT",
        "avatar_url": "VARCHAR(512)",
        "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    },
    "users": {
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "is_verified": "BOOLEAN NOT NULL DEFAULT 0",
        "last_login_at": "DATETIME",
        "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        # Auth-system additions (refresh / password-reset / verify flows).
        # All nullable so existing demo rows stay valid; the API layer
        # populates them as users register and rotate credentials.
        "username": "VARCHAR(48)",
        "last_password_change_at": "DATETIME",
        "email_verified_at": "DATETIME",
    },
}


def _apply_dev_migrations_sync(conn) -> None:
    """Run any pending additive migrations for dev-mode SQLite databases.

    Synchronous because it's invoked via ``run_sync`` from the async init.
    """
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name, expected_columns in _DEV_MIGRATIONS.items():
        if table_name not in existing_tables:
            continue  # create_all will create it from scratch
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        missing = [c for c in expected_columns if c not in existing_cols]
        if not missing:
            continue

        # Count rows: drop-and-recreate is safer when the gap is huge AND
        # there's nothing to lose. Threshold is 3+ missing on an empty
        # table — fewer columns are added per-statement.
        try:
            row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
        except Exception:  # noqa: BLE001
            row_count = 0

        if row_count == 0 and len(missing) >= 3:
            log.warning(
                "dev-migration: dropping empty %s (gap=%d cols) for clean recreate",
                table_name,
                len(missing),
            )
            conn.execute(text(f"DROP TABLE {table_name}"))
            continue  # create_all will rebuild with the full schema

        for col in missing:
            ddl = f"ALTER TABLE {table_name} ADD COLUMN {col} {expected_columns[col]}"
            log.info("dev-migration: %s", ddl)
            conn.execute(text(ddl))


async def init_db() -> None:
    """Create tables (and patch drifted ones in dev) on app startup."""
    # Importing the modules registers their Mapped classes against Base —
    # required for create_all to discover them. ``invitation`` and
    # ``membership`` are new in the Team feature.
    from app.models import (  # noqa: F401
        asset,
        brand_kit,
        integration,
        invitation,
        job,
        membership,
        notification,
        project,
        render,
        settings as settings_model,
        template,
        user,
        workspace,
    )

    async with engine.begin() as conn:
        await conn.run_sync(_apply_dev_migrations_sync)
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
