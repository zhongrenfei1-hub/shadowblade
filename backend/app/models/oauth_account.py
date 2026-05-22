"""OAuth account ORM — links external identity providers to a User row.

A single User can be linked to multiple OAuth providers (e.g. Google +
GitHub) so we use a separate table keyed on
``(provider, provider_user_id)``. The provider's user id is the
authoritative identifier — emails can change, get reassigned (in some
G Suite tenants), or collide across providers, so trusting only the
``sub`` claim from the IdP keeps us safe.

We store a snapshot of the profile fields (email, name, avatar) at the
time of the most recent link/refresh so the workspace UI can render
"signed in with Google as <name>" without a follow-up API call.

The raw provider payload is preserved in ``raw_profile`` (JSON-encoded
text — SQLite-compatible) for audit and future schema evolution.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OAuthAccount(Base):
    """An external identity (Google / GitHub / …) bound to one User."""

    __tablename__ = "user_oauth_accounts"
    __table_args__ = (
        # ``(provider, provider_user_id)`` is the natural key — a Google
        # account belongs to at most one ShadowBlade user. The DB also
        # creates a unique index on this pair for fast lookup during
        # ``/auth/google/callback``.
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_provider_user"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Short, lowercase provider slug. We keep this open-ended (no enum
    # check) so adding GitHub later is a one-line code change.
    provider: Mapped[str] = mapped_column(String(32), index=True)
    # The "sub" claim from the provider's id_token (or "id" from userinfo
    # for OAuth2-only providers). Always a string per OAuth spec.
    provider_user_id: Mapped[str] = mapped_column(String(255), index=True)

    # Profile snapshot — updated on every successful login so it never
    # drifts more than one session out of date.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # JSON-encoded full payload from the provider. We keep it because the
    # OAuth provider's schema evolves (Google has added/removed fields
    # over the years) and we may want to extract more fields later
    # without re-prompting the user for consent.
    raw_profile: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )


__all__ = ["OAuthAccount"]
