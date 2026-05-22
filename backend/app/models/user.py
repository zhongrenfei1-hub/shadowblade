"""User ORM — global account identity.

The user is intentionally org-agnostic. Membership in a workspace is
expressed through :class:`app.models.membership.WorkspaceMember`, so a user
can belong to multiple orgs (e.g. a freelancer working with two clients)
without needing a separate row per org.

Fields added for the Team feature (all backward-compat, default values
match the pre-existing demo data):

* ``username``    – handle distinct from email; nullable so legacy rows
                    survive the upgrade. Lower-case, 3–32 chars,
                    alphanumeric + ``_`` + ``.``.
* ``is_active``   – soft-disable account without deletion.
* ``is_verified`` – mirror of ``email_verified_at`` for cheap reads.
* ``email_verified_at`` – wall-clock timestamp of the verification event.
* ``last_login_at`` – bumped on every successful ``/auth/login``.
* ``last_password_change_at`` – audit + drives "stale password" warnings.
* ``updated_at``  – mirrors the brand-kit pattern; bumps on every PATCH.

The legacy ``role`` column (``'member'`` default) is kept for backward
compatibility — it is *not* the org-scoped role. The org-scoped role lives
on the ``WorkspaceMember`` row.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Distinct handle. Nullable + unique so existing rows (which have no
    # username yet) stay legal until they're either populated by a future
    # migration or via the user editing their profile.
    username: Mapped[str | None] = mapped_column(
        String(48), unique=True, index=True, nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255))
    # Legacy system-role; not the org-scoped role. Kept for back-compat with
    # the brand-kit demo and the /workspaces/me fixture endpoint.
    role: Mapped[str] = mapped_column(String(32), default="member")
    # Nullable since OAuth-only users (signed up via Google) never set a
    # password. The password endpoints all guard against this — see
    # ``verify_password`` returning False on None-ish hashes, plus the
    # ``/auth/password/change`` early-return that 400s when ``hashed_password
    # is None`` so an attacker can't probe "is this account a Google-only
    # account?" via timing.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Account status flags (added for Team feature).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_password_change_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )


__all__ = ["User"]
