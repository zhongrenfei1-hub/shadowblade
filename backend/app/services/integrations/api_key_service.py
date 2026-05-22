"""API Key generation, hashing, verification, and scope enforcement.

Design choices worth knowing about:

* **Plaintext is shown once.** We store ``SHA-256(plaintext)`` and a
  4-char tail in :class:`app.models.integration.ApiKey`; callers see the
  real token exactly once, returned from
  :func:`generate_api_key`. Subsequent lookups can identify the key by
  prefix + last_four for the UI but cannot reconstruct the secret.
* **Prefix-tagged.** Each plaintext starts with ``sb_live_`` (production)
  or ``sb_test_`` (dev) so leaked tokens are trivially identifiable in
  GitHub commit scans + observability pipelines.
* **Constant-time compare.** ``hmac.compare_digest`` everywhere we
  compare hashes, so we never leak timing information about a near-miss.
* **Scope wildcards.** ``*`` matches any required scope; otherwise we do
  exact membership. We do NOT implement hierarchical scopes
  (``mix:*`` ≠ ``mix:read`` + ``mix:write``) yet — keep it simple.

The verifier exposes :func:`verify_api_key` (DB-aware, async) and a
FastAPI dependency :func:`require_scope` that endpoints can drop in front
of any handler that wants opt-in API-key auth.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Iterable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.integration import ApiKey as ApiKeyORM

log = logging.getLogger("shadowblade.integrations.api_keys")

# Plaintext layout: <prefix><url-safe random>. Length of the random tail is
# deliberately the same as Stripe's (32 bytes base64 = 43 chars) so the
# overall token feels familiar.
_PREFIX_LIVE = "sb_live_"
_PREFIX_TEST = "sb_test_"
_RANDOM_BYTES = 32  # ≈ 43 chars after url-safe base64


# ---------------------------------------------------------------------------
# Public exceptions / dataclasses
# ---------------------------------------------------------------------------


class APIKeyAuthError(HTTPException):
    """Raised when an API key is missing, malformed, expired, or scoped wrong.

    Lives as an HTTPException subclass so endpoints can let it bubble up
    naturally — FastAPI turns it into the correct HTTP response.
    """

    def __init__(self, detail: str, *, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


@dataclass(slots=True, frozen=True)
class APIKeyAuthResult:
    """The successful outcome of :func:`verify_api_key`.

    Endpoints that depend on :func:`require_scope` receive one of these so
    they can audit *which* key signed the request (useful for logs and
    rate-limit attribution).
    """

    api_key_id: int
    workspace_id: int
    owner_id: int | None
    scopes: list[str]


# ---------------------------------------------------------------------------
# Generation / hashing / masking
# ---------------------------------------------------------------------------


def _active_prefix() -> str:
    """Return the prefix appropriate for the current environment."""
    if settings.environment.lower() in {"production", "prod", "live"}:
        return _PREFIX_LIVE
    return _PREFIX_TEST


def generate_api_key() -> tuple[str, str, str, str]:
    """Mint a new plaintext API key.

    Returns
    -------
    plaintext : str
        The full token (e.g. ``sb_test_AbC...XyZ``). Show this to the
        user exactly once.
    prefix : str
        First 8 chars (``sb_live_`` or ``sb_test_``) — what we store
        unhashed to render the masked display.
    last_four : str
        Last 4 chars of the plaintext.
    key_hash : str
        SHA-256 hex digest of the plaintext — store this in the DB.
    """
    prefix = _active_prefix()
    random_part = secrets.token_urlsafe(_RANDOM_BYTES).rstrip("=").replace("-", "X")
    # ``token_urlsafe`` is already url-safe, but we strip '=' padding and
    # swap '-' for 'X' so the rendered token never breaks ``--curl-arg``
    # parsing in shell environments. The entropy is unchanged because the
    # random_part length is fixed.
    plaintext = prefix + random_part
    last_four = plaintext[-4:]
    key_hash = hash_api_key(plaintext)
    return plaintext, prefix, last_four, key_hash


def hash_api_key(plaintext: str) -> str:
    """Hex-encoded SHA-256 of the plaintext key.

    SHA-256 (not bcrypt/argon2) is the right call here because API keys
    are uniformly random 256-bit secrets — brute force is impossible, so
    we don't need slow hashing. Equality lookups must be exact for the
    auth path to be a single-statement DB query.
    """
    if not isinstance(plaintext, str) or not plaintext:
        raise ValueError("plaintext must be a non-empty string")
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def mask_api_key(prefix: str, last_four: str) -> str:
    """Pretty-print a key for the UI: ``sb_live_•••••abcd``."""
    return f"{prefix}•••••{last_four}"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


async def verify_api_key(
    db: AsyncSession,
    *,
    plaintext: str,
    required_scope: str | None = None,
) -> APIKeyAuthResult:
    """Look up an API key by hash and (optionally) check it has the scope.

    Raises
    ------
    APIKeyAuthError
        If the key is missing / unknown / inactive / expired, or if a
        ``required_scope`` was supplied and the key doesn't carry it.
    """
    if not plaintext or not isinstance(plaintext, str):
        raise APIKeyAuthError("missing API key")
    if len(plaintext) < 16 or not (
        plaintext.startswith(_PREFIX_LIVE) or plaintext.startswith(_PREFIX_TEST)
    ):
        # Reject before we hit the DB — saves a round trip on obviously-bad
        # tokens and lets us answer the predictable 401 in the same shape.
        raise APIKeyAuthError("malformed API key")

    digest = hash_api_key(plaintext)
    stmt = select(ApiKeyORM).where(ApiKeyORM.key_hash == digest).limit(1)
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise APIKeyAuthError("API key not recognised")

    # Defence-in-depth — re-verify with constant-time compare even though
    # the SELECT already did an indexed match. Cheap and removes any
    # accidental DB-side timing oracle.
    if not hmac.compare_digest(row.key_hash, digest):
        raise APIKeyAuthError("API key not recognised")

    if not row.is_active:
        raise APIKeyAuthError("API key is revoked", status_code=status.HTTP_403_FORBIDDEN)

    if row.expires_at is not None and row.expires_at < datetime.utcnow():
        raise APIKeyAuthError("API key has expired", status_code=status.HTTP_403_FORBIDDEN)

    scopes: list[str] = list(row.scopes or [])
    if required_scope is not None and not scope_satisfied(scopes, required_scope):
        raise APIKeyAuthError(
            f"API key missing required scope: {required_scope}",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Update last_used_at on every successful auth. Best-effort — failing
    # to flush should not block the request, so we swallow errors here.
    try:
        row.last_used_at = datetime.utcnow()
        await db.commit()
    except Exception:  # noqa: BLE001
        log.warning("failed to bump last_used_at for api_key id=%s", row.id)

    return APIKeyAuthResult(
        api_key_id=row.id,
        workspace_id=row.workspace_id,
        owner_id=row.owner_id,
        scopes=scopes,
    )


def scope_satisfied(scopes: Iterable[str], required: str) -> bool:
    """``*`` matches anything; otherwise exact membership.

    Pure function — kept at module scope so the test suite can call it
    without standing up the FastAPI app.
    """
    bag = set(scopes)
    if "*" in bag:
        return True
    return required in bag


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def require_scope(scope: str | None = None):
    """Return a FastAPI dependency that gates an endpoint on an API key.

    Usage::

        @router.post("", dependencies=[Depends(require_scope("mix:write"))])
        async def submit_mix(...): ...

    Or grab the auth result for audit::

        async def handler(
            auth: Annotated[APIKeyAuthResult, Depends(require_scope("mix:write"))],
        ):
            log.info("called by api_key=%s", auth.api_key_id)

    The dependency reads ``X-API-Key`` (the canonical header) but falls
    back to the ``Authorization: Bearer <token>`` form so curl/postman
    snippets from third-party tutorials Just Work.
    """

    async def _dep(
        db: Annotated[AsyncSession, Depends(get_db)],
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> APIKeyAuthResult:
        token = x_api_key
        if not token and authorization:
            parts = authorization.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1].strip()
        if not token:
            raise APIKeyAuthError("missing API key (set X-API-Key or Bearer)")
        return await verify_api_key(db, plaintext=token, required_scope=scope)

    return _dep


# ---------------------------------------------------------------------------
# Optional dependency — endpoints that *may* use an API key
# ---------------------------------------------------------------------------


async def optional_api_key(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> APIKeyAuthResult | None:
    """Best-effort API-key resolution.

    Returns ``None`` when no token is present (so the endpoint keeps its
    cookie/header-based path), and raises :class:`APIKeyAuthError` when a
    token IS present but invalid. This way users can't silently downgrade
    a forged token into anonymous access.
    """
    token = x_api_key
    if not token and authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
    if not token:
        return None
    return await verify_api_key(db, plaintext=token, required_scope=None)


__all__ = [
    "APIKeyAuthError",
    "APIKeyAuthResult",
    "generate_api_key",
    "hash_api_key",
    "mask_api_key",
    "optional_api_key",
    "require_scope",
    "scope_satisfied",
    "verify_api_key",
]
