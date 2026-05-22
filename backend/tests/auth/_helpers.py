"""Local helpers for the auth test suite.

We don't re-export from ``tests.organizations.conftest`` because some of
those helpers (register-with-personal-ws cleanup) are specific to the
organization-management flow — for raw auth tests we want a minimal
register that doesn't side-effect the org tables beyond the bootstrap.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def register(
    client: TestClient,
    *,
    email: str,
    full_name: str = "Test User",
    password: str = "strongpass1",
    username: str | None = None,
) -> dict:
    """Hit ``POST /auth/register``; return the body dict on success.

    Raises ``AssertionError`` if the call fails — encourages tests to
    assert the *expected* failure shape directly rather than going
    through this helper.
    """
    payload = {
        "email": email,
        "full_name": full_name,
        "password": password,
    }
    if username is not None:
        payload["username"] = username
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    return r.json()


def login(
    client: TestClient,
    *,
    email_or_username: str,
    password: str = "strongpass1",
) -> dict:
    """Hit ``POST /auth/login``; return the body dict on success."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email_or_username, "password": password},
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()


def auth_headers(token: str) -> dict[str, str]:
    """Build the Authorization header for a bearer token."""
    return {"Authorization": f"Bearer {token}"}


__all__ = ["auth_headers", "login", "register"]
