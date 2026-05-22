"""Auth wire shapes — login, token, refresh, register-response, recovery.

Separate from :mod:`app.schemas.user` because these are *protocol*
artefacts (token + envelope shape) rather than domain objects.

Convention: every request body uses ``extra="forbid"`` so a typo'd field
name fails loudly instead of silently being dropped. Every response is a
plain ``BaseModel`` — FastAPI handles serialisation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.organization import OrganizationSummary
from app.schemas.user import PasswordStr, UserRead


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# Token envelopes
# ---------------------------------------------------------------------------


class TokenEnvelope(BaseModel):
    """Plain bearer-token envelope (compat with the OAuth2 password flow)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until exp


class TokenPair(TokenEnvelope):
    """Access + refresh pair, returned by login/register/refresh.

    The refresh token is included here so the React/SPA client can store
    both in the same step. Clients that don't want a refresh token
    (server-side renderers, cron jobs) can ignore the field.
    """

    refresh_token: str
    refresh_expires_in: int  # seconds until the refresh token expires


class LoginResponse(TokenPair):
    """Token pair + the user record + the active workspace summary.

    Kept this shape because the existing demo login returned ``user``;
    extending it with ``organizations`` lets the frontend skip a follow-up
    fetch.
    """

    user: UserRead
    organizations: list[OrganizationSummary] = Field(default_factory=list)
    default_workspace_id: int | None = None


class RegisterResponse(LoginResponse):
    """``POST /auth/register`` extends LoginResponse with the new org id."""

    new_organization_id: int
    # In dev mode where email is not actually sent, surface the verification
    # token in the response so the client can complete the verify flow in
    # tests / showcases. Production builds should wire an email provider.
    email_verification_token: str | None = None


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class RefreshRequest(BaseModel):
    """Body for ``POST /auth/refresh`` — just the refresh token."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    refresh_token: str = Field(min_length=10, max_length=4096)


class RefreshResponse(TokenPair):
    """``POST /auth/refresh`` returns a fresh access + refresh pair.

    We rotate the refresh token on every use ("refresh-token rotation")
    so a single leak gives an attacker at most one new access token
    before the legitimate client renews and invalidates the leaked one.
    """


# ---------------------------------------------------------------------------
# Password change (authenticated)
# ---------------------------------------------------------------------------


class PasswordChangeRequest(BaseModel):
    """Body for ``POST /auth/password/change`` (must be authenticated).

    ``current_password`` is required even for the authenticated user — it
    prevents an attacker who steals a logged-in session from rotating the
    password and locking the legitimate user out.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    current_password: str = Field(min_length=1, max_length=128)
    new_password: PasswordStr


# ---------------------------------------------------------------------------
# Password reset (forgot-password flow)
# ---------------------------------------------------------------------------


class PasswordRecoverRequest(BaseModel):
    """Body for ``POST /auth/password/recover`` — just the email."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr


class PasswordRecoverResponse(BaseModel):
    """Response for ``POST /auth/password/recover``.

    Always returns ``ok=True`` even when the email doesn't match a user —
    that prevents enumeration of registered emails. In dev mode the token
    is also returned so tests/showcases can drive the reset flow without
    a real email provider; production builds should strip ``reset_token``
    via a config flag (TODO when we wire SES/Postmark).
    """

    ok: bool = True
    message: str = "if the email is registered, a reset link has been sent"
    # Non-None only in dev/test; the prod build should set this to None
    # once we have an email service.
    reset_token: str | None = None


class PasswordResetRequest(BaseModel):
    """Body for ``POST /auth/password/reset`` — token + new password."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=10, max_length=4096)
    new_password: PasswordStr


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


class EmailVerificationRequest(BaseModel):
    """Body for ``POST /auth/email/verify`` — just the token."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=10, max_length=4096)


class EmailVerificationResendResponse(BaseModel):
    """Response for ``POST /auth/email/resend-verification``.

    Same dev-mode pattern as :class:`PasswordRecoverResponse` — the token
    is surfaced for tests; production should drop the field once email
    sending is wired.
    """

    ok: bool = True
    message: str = "verification email sent"
    verification_token: str | None = None


# ---------------------------------------------------------------------------
# Generic OK
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    """Used by endpoints that have nothing structured to return."""

    ok: bool = True
    message: str | None = None


__all__ = [
    "EmailVerificationRequest",
    "EmailVerificationResendResponse",
    "LoginRequest",
    "LoginResponse",
    "MessageResponse",
    "PasswordChangeRequest",
    "PasswordRecoverRequest",
    "PasswordRecoverResponse",
    "PasswordResetRequest",
    "RefreshRequest",
    "RefreshResponse",
    "RegisterResponse",
    "TokenEnvelope",
    "TokenPair",
]
