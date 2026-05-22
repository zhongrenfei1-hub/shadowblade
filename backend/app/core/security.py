"""Password hashing and JWT helpers for the Team auth layer.

Kept deliberately small — every API endpoint that needs auth pulls from
here, so any behaviour change (new claim, longer TTL, different algo) lives
in one place.

* Passwords are hashed with bcrypt via the ``bcrypt`` library directly. We
  bypass ``passlib`` because passlib<=1.7.4 vs bcrypt>=4.1 has a self-test
  bug that crashes on import.
* JWTs are signed HS256 by default. We mint four flavours, all sharing the
  same secret + algorithm but distinguished by the ``type`` claim:

      - ``access``         — bearer token, sub = user id (str), ~12h TTL
      - ``refresh``        — exchange-only, sub = user id (str), ~30d TTL
      - ``password_reset`` — single-use intent, sub = email, ~1h TTL
      - ``email_verify``   — single-use intent, sub = email, ~48h TTL

* ``decode_*_token`` raises :class:`TokenError` for any failure so callers
  can convert to a 401/400 in one place (see ``api/deps.py``).
"""

from __future__ import annotations

import logging
import secrets as _stdlib_secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

log = logging.getLogger("shadowblade.security")


# Bcrypt has a 72-byte cap on the input — anything longer is silently
# truncated on hashpw(). We surface that as a validation error instead so
# users don't unknowingly create accounts that accept any 72-byte prefix.
# Using the bcrypt library directly (without passlib) sidesteps the known
# passlib<=1.7.4 vs bcrypt>=4.1 self-test bug that crashes on import.
_BCRYPT_MAX_BYTES = 72

# Cost factor 12 ≈ 250 ms on a 2024 laptop — slow enough to deter brute
# force, fast enough to keep login responsive. Bcrypt's default is 12.
_BCRYPT_ROUNDS = 12


# Token-type discriminators. Storing them as constants prevents the kind of
# typo that would, e.g., let an access token be accepted where a refresh
# token was expected.
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"
EMAIL_VERIFY_TOKEN_TYPE = "email_verify"


class TokenError(Exception):
    """Raised when a JWT fails verification.

    Wraps the underlying ``jose`` exception so callers can catch a single
    type and 401 without leaking implementation details to the client.
    """


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of ``plain`` (UTF-8 encoded, cost 12).

    Raises
    ------
    ValueError
        If the password exceeds the bcrypt 72-byte input cap. The API layer
        also enforces an 8-128 char range, so this is a defence-in-depth
        check rather than the primary validation point.
    """
    encoded = plain.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError(
            f"password is {len(encoded)} bytes; bcrypt accepts at most "
            f"{_BCRYPT_MAX_BYTES} bytes — please shorten it"
        )
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(encoded, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time check of ``plain`` against a stored bcrypt hash.

    Returns ``False`` on any internal failure (malformed hash, oversize
    input, library error) — verifying a password should never distinguish
    between *wrong password* and *implementation error*.
    """
    try:
        encoded = plain.encode("utf-8")
        if len(encoded) > _BCRYPT_MAX_BYTES:
            # Bcrypt would raise; treat as auth failure rather than crash.
            return False
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
    except Exception:  # noqa: BLE001 — defence in depth
        log.exception("password verify failed")
        return False


# ---------------------------------------------------------------------------
# JWT factory (the four token flavours funnel through this)
# ---------------------------------------------------------------------------


_RESERVED_CLAIMS = frozenset({"iat", "exp", "sub", "type", "jti"})


def _mint_token(
    *,
    subject: str,
    token_type: str,
    ttl_minutes: int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Sign a JWT with the standard frame + ``type`` discriminator.

    Internal helper — public callers should use one of the four ``create_*_token``
    wrappers which fix the ``token_type`` and TTL for their flavour.
    """
    if extra_claims:
        clashes = _RESERVED_CLAIMS & extra_claims.keys()
        if clashes:
            raise ValueError(
                f"reserved claims cannot be overridden: {sorted(clashes)}"
            )

    now = datetime.now(timezone.utc)
    ttl = timedelta(minutes=ttl_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "type": token_type,
        # jti gives every token a unique identifier — useful when we add a
        # revocation list later, and harmless until then.
        "jti": _stdlib_secrets.token_urlsafe(12),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_and_check_type(token: str, *, expected_type: str) -> dict[str, Any]:
    """Decode a JWT and confirm its ``type`` matches ``expected_type``.

    Returns the claims dict. Raises :class:`TokenError` for any mismatch,
    expiry, signature failure, or missing-required-claim condition.
    """
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise TokenError(f"invalid token: {exc}") from exc

    if claims.get("type") != expected_type:
        raise TokenError(
            f"wrong token type; expected {expected_type!r}, "
            f"got {claims.get('type')!r}"
        )
    if "sub" not in claims:
        raise TokenError("token missing subject")
    return claims


# ---------------------------------------------------------------------------
# Access tokens (short-lived, bearer)
# ---------------------------------------------------------------------------


def create_access_token(
    subject: int | str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_in_minutes: int | None = None,
) -> str:
    """Sign a short-lived access JWT identifying ``subject`` (user id).

    Parameters
    ----------
    subject
        The principal. Coerced to ``str`` to satisfy RFC 7519 §4.1.2.
    extra_claims
        Optional dict folded into the payload (e.g. workspace context).
        Reserved names raise ``ValueError`` to prevent accidental override.
    expires_in_minutes
        Override the default ``settings.jwt_ttl_minutes``. Useful for
        short-lived invite tokens or long-lived service tokens.
    """
    return _mint_token(
        subject=str(subject),
        token_type=ACCESS_TOKEN_TYPE,
        ttl_minutes=expires_in_minutes or settings.jwt_ttl_minutes,
        extra_claims=extra_claims,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify an access token, returning the claims dict.

    Raises
    ------
    TokenError
        Signature mismatch, expired, malformed, or wrong token type.
    """
    return _decode_and_check_type(token, expected_type=ACCESS_TOKEN_TYPE)


# ---------------------------------------------------------------------------
# Refresh tokens (long-lived, exchange-only)
# ---------------------------------------------------------------------------


def create_refresh_token(
    subject: int | str,
    *,
    expires_in_minutes: int | None = None,
) -> str:
    """Sign a long-lived refresh JWT for ``subject``.

    Refresh tokens are *only* accepted by ``POST /auth/refresh``. They do
    NOT grant access to protected endpoints — those still require an
    ``access`` token. This split limits the blast radius if a refresh
    token leaks: the attacker has to exchange it for an access token,
    which gives us a chance to detect the rotation if we ever add server-
    side refresh-token tracking.
    """
    return _mint_token(
        subject=str(subject),
        token_type=REFRESH_TOKEN_TYPE,
        ttl_minutes=expires_in_minutes or settings.jwt_refresh_ttl_minutes,
    )


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token. Raises :class:`TokenError` on any failure."""
    return _decode_and_check_type(token, expected_type=REFRESH_TOKEN_TYPE)


# ---------------------------------------------------------------------------
# Password reset tokens (short-lived, sub = email)
# ---------------------------------------------------------------------------


def generate_password_reset_token(email: str) -> str:
    """Sign a single-use password-reset token bound to ``email``.

    ``sub`` carries the email so we don't have to look up the user id
    before signing (the recovery endpoint doesn't have it on hand). The
    verifier returns the email which the API then uses to load the user.

    Implementation note: this is a *stateless* token. We don't store a
    server-side reset record — if the user requests two recovery emails
    in a row, both will work until they expire. That's the trade-off the
    fastapi-fullstack-template makes too; production deployments that
    need single-use semantics should add a revoke table later.
    """
    return _mint_token(
        subject=email.lower(),
        token_type=PASSWORD_RESET_TOKEN_TYPE,
        ttl_minutes=settings.password_reset_ttl_minutes,
    )


def verify_password_reset_token(token: str) -> str:
    """Return the email embedded in a valid password-reset token.

    Raises :class:`TokenError` for any failure (expired, bad signature,
    wrong type, missing subject).
    """
    claims = _decode_and_check_type(token, expected_type=PASSWORD_RESET_TOKEN_TYPE)
    return str(claims["sub"])


# ---------------------------------------------------------------------------
# Email verification tokens (short-lived, sub = email)
# ---------------------------------------------------------------------------


def generate_email_verification_token(email: str) -> str:
    """Sign an email-verification token bound to ``email``.

    Same pattern as the reset token but with a longer TTL — users
    sometimes wait a day or two to click the verification link.
    """
    return _mint_token(
        subject=email.lower(),
        token_type=EMAIL_VERIFY_TOKEN_TYPE,
        ttl_minutes=settings.email_verify_ttl_minutes,
    )


def verify_email_verification_token(token: str) -> str:
    """Return the email embedded in a valid email-verification token."""
    claims = _decode_and_check_type(token, expected_type=EMAIL_VERIFY_TOKEN_TYPE)
    return str(claims["sub"])


__all__ = [
    "ACCESS_TOKEN_TYPE",
    "EMAIL_VERIFY_TOKEN_TYPE",
    "PASSWORD_RESET_TOKEN_TYPE",
    "REFRESH_TOKEN_TYPE",
    "TokenError",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "generate_email_verification_token",
    "generate_password_reset_token",
    "hash_password",
    "verify_email_verification_token",
    "verify_password",
    "verify_password_reset_token",
]
