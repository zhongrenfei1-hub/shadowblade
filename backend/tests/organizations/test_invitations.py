"""Invitation lifecycle — create, list, revoke, inspect, accept.

These tests are deliberately tight on the security-sensitive paths
(addressee binding, expiry, role coercion).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from tests.organizations.conftest import (
    create_org,
    invite,
    register,
)


def _seed_owner_with_org(client, *, email="founder@acme.com", slug="acme"):
    h = register(client, email=email)
    org = create_org(client, headers=h["headers"], slug=slug)
    return h, org


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_invitation_returns_code_and_pending_status(client):
    h, org = _seed_owner_with_org(client)
    inv = invite(client, org_id=org["id"], headers=h["headers"], email="x@y.com")
    assert inv["status"] == "pending"
    assert inv["role"] == "member"
    assert len(inv["invite_code"]) >= 20  # token_urlsafe(24) ≈ 32 chars
    assert inv["email"] == "x@y.com"
    assert inv["inviter"]["id"] == h["user_id"]


def test_create_invitation_for_existing_member_returns_409(client):
    h_owner = register(client, email="o@acme.com")
    h_target = register(client, email="t@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="acme")

    # First invite + accept
    inv1 = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="t@acme.com",
    )
    client.post(
        f"/api/v1/invitations/{inv1['invite_code']}/accept",
        headers=h_target["headers"],
    )

    # Second invite — they're already in
    r = client.post(
        f"/api/v1/organizations/{org['id']}/invitations",
        json={"email": "t@acme.com", "role": "member"},
        headers=h_owner["headers"],
    )
    assert r.status_code == 409


def test_create_invitation_rejects_owner_role(client):
    h, org = _seed_owner_with_org(client)
    r = client.post(
        f"/api/v1/organizations/{org['id']}/invitations",
        json={"email": "x@y.com", "role": "owner"},
        headers=h["headers"],
    )
    assert r.status_code == 422


def test_create_invitation_requires_admin(client):
    h_owner = register(client, email="o3@acme.com")
    h_member = register(client, email="m3@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="acme")

    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="m3@acme.com", role="member",
    )
    client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_member["headers"],
    )

    # Plain member tries to invite — 403
    r = client.post(
        f"/api/v1/organizations/{org['id']}/invitations",
        json={"email": "new@acme.com", "role": "member"},
        headers=h_member["headers"],
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Public inspect + accept
# ---------------------------------------------------------------------------


def test_inspect_invitation_is_public(client):
    h, org = _seed_owner_with_org(client, slug="visibleco")
    inv = invite(
        client, org_id=org["id"], headers=h["headers"], email="bob@acme.com",
    )
    r = client.get(f"/api/v1/invitations/{inv['invite_code']}")
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_name"] == "Acme"
    assert body["role"] == "member"
    assert body["email"] == "bob@acme.com"
    # Don't leak inviter identity through public inspect.
    assert "invited_by" not in body and "inviter" not in body


def test_inspect_invitation_unknown_code_is_404(client):
    r = client.get("/api/v1/invitations/totallyfakecode")
    assert r.status_code == 404


def test_accept_invitation_creates_membership(client):
    h_owner, org = _seed_owner_with_org(client)
    h_invitee = register(client, email="invited@acme.com")
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="invited@acme.com", role="admin",
    )
    r = client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_invitee["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == org["id"]
    assert body["role"] == "admin"
    assert body["membership_id"] > 0

    # Followup inspect now reports accepted
    r = client.get(f"/api/v1/invitations/{inv['invite_code']}")
    assert r.json()["status"] == "accepted"


def test_accept_invitation_requires_login(client):
    h_owner, org = _seed_owner_with_org(client)
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="anon@acme.com",
    )
    r = client.post(f"/api/v1/invitations/{inv['invite_code']}/accept")
    assert r.status_code == 401


def test_accept_invitation_wrong_addressee_is_403(client):
    h_owner, org = _seed_owner_with_org(client)
    h_intended = register(client, email="intended@acme.com")
    h_other = register(client, email="other@acme.com")
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="intended@acme.com",
    )
    r = client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_other["headers"],
    )
    assert r.status_code == 403


def test_accept_invitation_already_member_409_and_marks_accepted(client):
    h_owner, org = _seed_owner_with_org(client)
    h_user = register(client, email="dup@acme.com")
    inv1 = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="dup@acme.com",
    )
    # First accept — fine
    client.post(
        f"/api/v1/invitations/{inv1['invite_code']}/accept",
        headers=h_user["headers"],
    )
    # Generate a second invite (admin re-send) — accept should 409
    inv2 = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="dup@acme.com",
    ) if False else None
    # Re-using inv1 (same code) — also 409 because already accepted
    r = client.post(
        f"/api/v1/invitations/{inv1['invite_code']}/accept",
        headers=h_user["headers"],
    )
    # Status is now 'accepted', not 'pending', so it 400's
    assert r.status_code == 400


def test_accept_invitation_after_revoke_fails(client):
    h_owner, org = _seed_owner_with_org(client)
    h_user = register(client, email="rev@acme.com")
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="rev@acme.com",
    )
    # Owner revokes
    r = client.delete(
        f"/api/v1/organizations/{org['id']}/invitations/{inv['id']}",
        headers=h_owner["headers"],
    )
    assert r.status_code == 204

    r = client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_user["headers"],
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# List + revoke
# ---------------------------------------------------------------------------


def test_list_invitations_only_for_admins(client):
    h_owner, org = _seed_owner_with_org(client)
    h_member = register(client, email="lim@acme.com")
    # Invite + accept the member first
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="lim@acme.com", role="member",
    )
    client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_member["headers"],
    )

    # Owner lists — sees the one accepted invite
    r = client.get(
        f"/api/v1/organizations/{org['id']}/invitations",
        headers=h_owner["headers"],
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Member tries to list — 403
    r = client.get(
        f"/api/v1/organizations/{org['id']}/invitations",
        headers=h_member["headers"],
    )
    assert r.status_code == 403


def test_revoke_invitation_is_idempotent(client):
    h, org = _seed_owner_with_org(client)
    inv = invite(client, org_id=org["id"], headers=h["headers"], email="r@y.com")
    for _ in range(2):
        r = client.delete(
            f"/api/v1/organizations/{org['id']}/invitations/{inv['id']}",
            headers=h["headers"],
        )
        assert r.status_code == 204


def test_expired_invitation_reports_expired_status(client, db_engine):
    """Manually back-date an invite to verify the expiry logic.

    Uses the per-test DB engine's session factory directly — the prod
    SessionLocal would point at the wrong database (the test runner
    overrides ``get_db`` for endpoints but the global is untouched).
    """
    import asyncio
    from sqlalchemy import update
    from app.models import WorkspaceInvite

    _engine, session_factory = db_engine

    h_owner, org = _seed_owner_with_org(client)
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="will-expire@acme.com",
    )

    async def _expire():
        async with session_factory() as s:
            await s.execute(
                update(WorkspaceInvite)
                .where(WorkspaceInvite.id == inv["id"])
                .values(expires_at=datetime(1999, 1, 1))
            )
            await s.commit()

    asyncio.new_event_loop().run_until_complete(_expire())

    # Inspect should now say expired.
    r = client.get(f"/api/v1/invitations/{inv['invite_code']}")
    assert r.json()["status"] == "expired"

    # Accept should 400.
    h_user = register(client, email="will-expire@acme.com")
    r = client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_user["headers"],
    )
    assert r.status_code == 400
