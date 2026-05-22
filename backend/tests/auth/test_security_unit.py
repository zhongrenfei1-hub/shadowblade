"""Unit tests for ``app.core.security`` — no HTTP layer involved.

These pin the contracts of the helpers used by the API: token typing,
bcrypt rules, and reserved-claim guarding.
"""

from __future__ import annotations

import pytest

from app.core.security import (
    ACCESS_TOKEN_TYPE,
    EMAIL_VERIFY_TOKEN_TYPE,
    PASSWORD_RESET_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    verify_email_verification_token,
    verify_password,
    verify_password_reset_token,
)


# ---------------------------------------------------------------------------
# Bcrypt
# ---------------------------------------------------------------------------


def test_hash_password_matches_verify():
    h = hash_password("hunter2hunter")
    assert verify_password("hunter2hunter", h) is True


def test_verify_password_rejects_wrong():
    h = hash_password("right1234")
    assert verify_password("wrong1234", h) is False


def test_verify_password_handles_malformed_hash():
    # Garbage hash should NOT raise — verify returns False.
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_hash_password_rejects_oversize():
    with pytest.raises(ValueError):
        hash_password("x" * 100)  # > 72 bytes


def test_verify_password_rejects_oversize_silently():
    # Oversize input on verify returns False (not exception) — auth code
    # should treat all "wrong password" outcomes uniformly.
    h = hash_password("validpass1")
    assert verify_password("x" * 100, h) is False


# ---------------------------------------------------------------------------
# Token typing
# ---------------------------------------------------------------------------


def test_access_token_decodes_as_access():
    t = create_access_token(7)
    claims = decode_access_token(t)
    assert claims["type"] == ACCESS_TOKEN_TYPE
    assert claims["sub"] == "7"


def test_refresh_token_decodes_as_refresh():
    t = create_refresh_token(7)
    claims = decode_refresh_token(t)
    assert claims["type"] == REFRESH_TOKEN_TYPE
    assert claims["sub"] == "7"


def test_access_token_rejected_as_refresh():
    t = create_access_token(7)
    with pytest.raises(TokenError):
        decode_refresh_token(t)


def test_refresh_token_rejected_as_access():
    t = create_refresh_token(7)
    with pytest.raises(TokenError):
        decode_access_token(t)


def test_password_reset_token_decodes_back_to_email():
    t = generate_password_reset_token("alice@acme.com")
    assert verify_password_reset_token(t) == "alice@acme.com"


def test_password_reset_token_lowercases_subject():
    t = generate_password_reset_token("ALICE@acme.com")
    # The verifier returns whatever the token signs; we sign the lowercase
    # form so downstream lookups need only one case branch.
    assert verify_password_reset_token(t) == "alice@acme.com"


def test_password_reset_token_rejected_as_access():
    t = generate_password_reset_token("alice@acme.com")
    with pytest.raises(TokenError):
        decode_access_token(t)


def test_email_verification_token_decodes_back_to_email():
    t = generate_email_verification_token("bob@acme.com")
    assert verify_email_verification_token(t) == "bob@acme.com"


def test_email_verification_token_rejected_as_reset():
    t = generate_email_verification_token("bob@acme.com")
    with pytest.raises(TokenError):
        verify_password_reset_token(t)


def test_password_reset_token_rejected_as_email_verify():
    t = generate_password_reset_token("bob@acme.com")
    with pytest.raises(TokenError):
        verify_email_verification_token(t)


# ---------------------------------------------------------------------------
# Reserved-claim guarding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("claim", ["iat", "exp", "sub", "type", "jti"])
def test_create_access_token_rejects_reserved_claim(claim):
    with pytest.raises(ValueError):
        create_access_token(7, extra_claims={claim: "evil"})


def test_create_access_token_accepts_safe_extra_claim():
    t = create_access_token(7, extra_claims={"ws": 42, "scope": "admin"})
    claims = decode_access_token(t)
    assert claims["ws"] == 42
    assert claims["scope"] == "admin"


# ---------------------------------------------------------------------------
# Decode error handling
# ---------------------------------------------------------------------------


def test_decode_access_token_raises_on_garbage():
    with pytest.raises(TokenError):
        decode_access_token("not.a.valid.jwt")


def test_decode_refresh_token_raises_on_garbage():
    with pytest.raises(TokenError):
        decode_refresh_token("not.a.valid.jwt")
