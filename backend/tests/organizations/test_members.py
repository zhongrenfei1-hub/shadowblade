"""Member management — direct add, list, role change, removal, transfer.

These tests pin down the per-row invariants that aren't enforceable in the
DB (single owner, no admin coup, etc.).
"""

from __future__ import annotations

from tests.organizations.conftest import (
    accept,
    create_org,
    invite,
    register,
)


def _seed_two_members(client):
    """Owner + member fixture used by half the tests below."""
    h_owner = register(client, email="owner@acme.com")
    h_member = register(client, email="member@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="acme")
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="member@acme.com", role="member",
    )
    accept(client, code=inv["invite_code"], headers=h_member["headers"])
    return h_owner, h_member, org


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_members_returns_all_members_with_user_info(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.get(
        f"/api/v1/organizations/{org['id']}/members", headers=h_owner["headers"]
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    by_role = {row["role"] for row in rows}
    assert {"owner", "member"} == by_role
    # Nested user payload present for one-shot rendering.
    for row in rows:
        assert row["user"] is not None
        assert row["user"]["id"] > 0


def test_list_members_visible_to_plain_member(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.get(
        f"/api/v1/organizations/{org['id']}/members",
        headers=h_member["headers"],
    )
    assert r.status_code == 200
    assert len(r.json()) == 2


# ---------------------------------------------------------------------------
# Direct add (POST /members)
# ---------------------------------------------------------------------------


def test_add_member_direct_by_admin(client):
    h_owner = register(client, email="o@acme.com")
    h_other = register(client, email="t@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="acme")

    r = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_id": h_other["user_id"], "role": "member"},
        headers=h_owner["headers"],
    )
    assert r.status_code == 201
    assert r.json()["user_id"] == h_other["user_id"]
    assert r.json()["role"] == "member"


def test_add_member_rejects_duplicate(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_id": h_member["user_id"], "role": "admin"},
        headers=h_owner["headers"],
    )
    assert r.status_code == 409


def test_add_member_admin_cannot_create_owner(client):
    """Admins can't elevate a peer to owner — only the existing owner can."""
    h_owner = register(client, email="owner1@acme.com")
    h_admin = register(client, email="admin1@acme.com")
    h_target = register(client, email="target1@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="acme")

    # Make admin
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="admin1@acme.com", role="admin",
    )
    accept(client, code=inv["invite_code"], headers=h_admin["headers"])

    # Admin tries to add target at owner role
    r = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_id": h_target["user_id"], "role": "owner"},
        headers=h_admin["headers"],
    )
    assert r.status_code == 403


def test_add_member_unknown_user_is_404(client):
    h = register(client, email="lonely@acme.com")
    org = create_org(client, headers=h["headers"], slug="acme")
    r = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"user_id": 99999, "role": "member"},
        headers=h["headers"],
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update role (PUT)
# ---------------------------------------------------------------------------


def test_update_role_promote_member_to_admin(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.put(
        f"/api/v1/organizations/{org['id']}/members/{h_member['user_id']}",
        json={"role": "admin"},
        headers=h_owner["headers"],
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_update_role_cannot_promote_via_put(client):
    """PUT must refuse role=owner; the path is /transfer instead."""
    h_owner, h_member, org = _seed_two_members(client)
    r = client.put(
        f"/api/v1/organizations/{org['id']}/members/{h_member['user_id']}",
        json={"role": "owner"},
        headers=h_owner["headers"],
    )
    assert r.status_code == 400
    assert "transfer" in r.json()["detail"]


def test_update_role_sole_owner_cannot_self_demote(client):
    h = register(client, email="solo@acme.com")
    org = create_org(client, headers=h["headers"], slug="solo")
    r = client.put(
        f"/api/v1/organizations/{org['id']}/members/{h['user_id']}",
        json={"role": "admin"},
        headers=h["headers"],
    )
    assert r.status_code == 400
    assert "transfer" in r.json()["detail"]


def test_update_role_admin_cannot_demote_another_admin(client):
    h_owner = register(client, email="ow@acme.com")
    h_a = register(client, email="aa@acme.com")
    h_b = register(client, email="bb@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="three")

    # Both A and B become admins
    for h_target, email in ((h_a, "aa@acme.com"), (h_b, "bb@acme.com")):
        inv = invite(
            client, org_id=org["id"], headers=h_owner["headers"],
            email=email, role="admin",
        )
        accept(client, code=inv["invite_code"], headers=h_target["headers"])

    # A tries to demote B
    r = client.put(
        f"/api/v1/organizations/{org['id']}/members/{h_b['user_id']}",
        json={"role": "guest"},
        headers=h_a["headers"],
    )
    assert r.status_code == 403


def test_update_role_unknown_member_is_404(client):
    h = register(client, email="lone@acme.com")
    org = create_org(client, headers=h["headers"], slug="lone")
    r = client.put(
        f"/api/v1/organizations/{org['id']}/members/99999",
        json={"role": "admin"},
        headers=h["headers"],
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Remove (DELETE)
# ---------------------------------------------------------------------------


def test_remove_member_by_owner(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.delete(
        f"/api/v1/organizations/{org['id']}/members/{h_member['user_id']}",
        headers=h_owner["headers"],
    )
    assert r.status_code == 204

    members = client.get(
        f"/api/v1/organizations/{org['id']}/members", headers=h_owner["headers"]
    ).json()
    assert len(members) == 1


def test_remove_self_is_leave_org(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.delete(
        f"/api/v1/organizations/{org['id']}/members/{h_member['user_id']}",
        headers=h_member["headers"],
    )
    assert r.status_code == 204

    # Member can no longer see the org.
    orgs = client.get(
        "/api/v1/organizations", headers=h_member["headers"]
    ).json()
    assert all(o["id"] != org["id"] for o in orgs)


def test_remove_sole_owner_blocked(client):
    h = register(client, email="alone@acme.com")
    org = create_org(client, headers=h["headers"], slug="alone")
    r = client.delete(
        f"/api/v1/organizations/{org['id']}/members/{h['user_id']}",
        headers=h["headers"],
    )
    assert r.status_code == 400


def test_remove_other_admin_requires_owner(client):
    h_owner = register(client, email="oa@acme.com")
    h_admin1 = register(client, email="a1@acme.com")
    h_admin2 = register(client, email="a2@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="trio")

    for tg, em in ((h_admin1, "a1@acme.com"), (h_admin2, "a2@acme.com")):
        inv = invite(
            client, org_id=org["id"], headers=h_owner["headers"],
            email=em, role="admin",
        )
        accept(client, code=inv["invite_code"], headers=tg["headers"])

    # admin1 tries to remove admin2 — forbidden
    r = client.delete(
        f"/api/v1/organizations/{org['id']}/members/{h_admin2['user_id']}",
        headers=h_admin1["headers"],
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Transfer ownership
# ---------------------------------------------------------------------------


def test_transfer_ownership_swaps_roles(client):
    h_owner, h_member, org = _seed_two_members(client)
    r = client.post(
        f"/api/v1/organizations/{org['id']}/transfer",
        json={"new_owner_id": h_member["user_id"]},
        headers=h_owner["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    # Two rows returned; check the roles.
    by_uid = {row["user_id"]: row["role"] for row in body}
    assert by_uid[h_member["user_id"]] == "owner"
    assert by_uid[h_owner["user_id"]] == "admin"

    # Old owner can no longer delete the org.
    r = client.delete(
        f"/api/v1/organizations/{org['id']}", headers=h_owner["headers"]
    )
    assert r.status_code == 403


def test_transfer_to_non_member_fails(client):
    h_owner = register(client, email="ow1@acme.com")
    h_outsider = register(client, email="out@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="lone")

    r = client.post(
        f"/api/v1/organizations/{org['id']}/transfer",
        json={"new_owner_id": h_outsider["user_id"]},
        headers=h_owner["headers"],
    )
    assert r.status_code == 404


def test_transfer_to_self_is_400(client):
    h = register(client, email="me@acme.com")
    org = create_org(client, headers=h["headers"], slug="me")
    r = client.post(
        f"/api/v1/organizations/{org['id']}/transfer",
        json={"new_owner_id": h["user_id"]},
        headers=h["headers"],
    )
    assert r.status_code == 400


def test_transfer_requires_owner(client):
    h_owner = register(client, email="o2@acme.com")
    h_admin = register(client, email="a2@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="hand")

    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="a2@acme.com", role="admin",
    )
    accept(client, code=inv["invite_code"], headers=h_admin["headers"])

    r = client.post(
        f"/api/v1/organizations/{org['id']}/transfer",
        json={"new_owner_id": h_admin["user_id"]},
        headers=h_admin["headers"],
    )
    assert r.status_code == 403
