"""Permission helper unit tests (no HTTP, no DB).

These hit :mod:`app.core.permissions` and :mod:`app.core.security` directly
to lock in the role hierarchy + JWT round-trip invariants. They run an
order of magnitude faster than the integration tests above and let us
catch hierarchy regressions in CI before the slow tier even starts.
"""

from __future__ import annotations

import pytest

from app.core.permissions import (
    ALLOWED_ROLES,
    PERMISSIONS,
    ROLE_HIERARCHY,
    assert_role_value,
    has_permission,
    role_at_least,
)
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "actor,required,expected",
    [
        ("owner", "owner", True),
        ("owner", "admin", True),
        ("owner", "member", True),
        ("owner", "guest", True),
        ("admin", "owner", False),
        ("admin", "admin", True),
        ("admin", "member", True),
        ("member", "admin", False),
        ("member", "member", True),
        ("guest", "member", False),
        ("guest", "guest", True),
        ("garbage", "guest", False),  # unknown role grants nothing
        ("owner", "alien", False),    # unknown requirement grants nothing
    ],
)
def test_role_at_least(actor, required, expected):
    assert role_at_least(actor, required) is expected


def test_allowed_roles_in_hierarchy_match():
    assert set(ALLOWED_ROLES) == set(ROLE_HIERARCHY.keys())


def test_assert_role_value_passes_known(client_unused=None):
    for r in ALLOWED_ROLES:
        assert assert_role_value(r) == r


def test_assert_role_value_rejects_unknown():
    with pytest.raises(ValueError):
        assert_role_value("god")


# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------


def test_owner_has_strict_superset_of_admin():
    assert PERMISSIONS["admin"].issubset(PERMISSIONS["owner"])


def test_admin_has_superset_of_member():
    assert PERMISSIONS["member"].issubset(PERMISSIONS["admin"])


def test_member_has_superset_of_guest():
    assert PERMISSIONS["guest"].issubset(PERMISSIONS["member"])


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        ("owner", "org:delete", True),
        ("admin", "org:delete", False),
        ("admin", "member:invite", True),
        ("member", "member:invite", False),
        ("guest", "render:submit", False),
        ("member", "render:submit", True),
        ("guest", "brand_kit:read", True),
        ("guest", "brand_kit:write", False),
    ],
)
def test_has_permission_matrix(role, permission, expected):
    assert has_permission(role, permission) is expected


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_hash_password_is_bcrypt():
    h = hash_password("hunter2hunter")
    assert h.startswith("$2b$") or h.startswith("$2a$")
    assert len(h) == 60


def test_hash_password_verifies_correctly():
    h = hash_password("correct-horse")
    assert verify_password("correct-horse", h)
    assert not verify_password("battery-staple", h)


def test_hash_password_each_call_unique_salt():
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2  # different salts
    assert verify_password("same-password", h1)
    assert verify_password("same-password", h2)


def test_hash_password_rejects_oversize_input():
    with pytest.raises(ValueError):
        hash_password("a" * 80)


def test_verify_password_returns_false_for_oversize():
    h = hash_password("normal-pass")
    # Oversize must not raise — return False so callers don't have to
    # special-case the "this would have been rejected at hash time" path.
    assert verify_password("a" * 100, h) is False


def test_verify_password_returns_false_on_malformed_hash():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def test_token_round_trip_basic():
    tok = create_access_token(42)
    claims = decode_access_token(tok)
    assert claims["sub"] == "42"
    assert claims["type"] == "access"
    assert "iat" in claims and "exp" in claims


def test_token_with_extra_claims():
    tok = create_access_token(42, extra_claims={"ws": 7, "scope": "demo"})
    claims = decode_access_token(tok)
    assert claims["ws"] == 7
    assert claims["scope"] == "demo"


def test_token_reserved_claims_blocked():
    for reserved in ("iat", "exp", "sub", "type"):
        with pytest.raises(ValueError):
            create_access_token(1, extra_claims={reserved: "no"})


def test_token_tampering_detected():
    tok = create_access_token(42)
    tampered = tok + "x"
    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_token_with_unknown_type_rejected():
    """A token from a different family (refresh, invite) won't pass."""
    from jose import jwt

    from app.core.config import settings

    payload = {"sub": "42", "type": "refresh", "iat": 0, "exp": 9999999999}
    refresh_tok = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(TokenError):
        decode_access_token(refresh_tok)
