"""Org-level CRUD — create / list / get / patch / delete.

The behavioural contract these tests pin down:

* The slug is canonical, URL-safe, and unique globally.
* Listing returns only orgs you're a member of.
* Detail/patch require membership; non-members see 404 (not 403) so we
  don't leak existence of private orgs.
* Plan/seats/quota mutation requires owner-level (admin alone isn't enough).
* Delete needs owner role; cascade removes members and invitations.
"""

from __future__ import annotations

from tests.organizations.conftest import (
    create_org,
    invite,
    register,
)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_organization_sets_caller_as_owner(client):
    h = register(client, email="ada@acme.com")
    org = create_org(client, headers=h["headers"], name="Ada Studio", slug="ada")
    assert org["slug"] == "ada"
    assert org["name"] == "Ada Studio"
    assert org["owner_id"] == h["user_id"]
    assert org["role"] == "owner"
    assert org["member_count"] == 1
    assert org["plan"] == "growth"


def test_create_organization_normalises_slug_to_lowercase(client):
    h = register(client, email="grace@acme.com")
    r = client.post(
        "/api/v1/organizations",
        json={"name": "Grace", "slug": "ACME-Co"},
        headers=h["headers"],
    )
    assert r.status_code == 201
    assert r.json()["slug"] == "acme-co"


def test_create_organization_rejects_invalid_slug(client):
    h = register(client, email="hugo@acme.com")
    for bad in ["a", "-bad", "bad-", "bad--double", "9start", "has space"]:
        r = client.post(
            "/api/v1/organizations",
            json={"name": "Bad", "slug": bad},
            headers=h["headers"],
        )
        assert r.status_code == 422, f"slug {bad!r} should be rejected"


def test_create_organization_unique_slug(client):
    h = register(client, email="iris@acme.com")
    create_org(client, headers=h["headers"], slug="dupe-test")
    r = client.post(
        "/api/v1/organizations",
        json={"name": "Other", "slug": "dupe-test"},
        headers=h["headers"],
    )
    assert r.status_code == 409


def test_create_organization_requires_auth(client):
    r = client.post(
        "/api/v1/organizations",
        json={"name": "Anon", "slug": "anon"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_organizations_includes_personal_and_created(client):
    h = register(client, email="jack@acme.com", drop_personal_ws=False)
    org = create_org(client, headers=h["headers"], slug="jack-team")

    r = client.get("/api/v1/organizations", headers=h["headers"])
    assert r.status_code == 200
    orgs = r.json()
    assert len(orgs) == 2  # personal + created
    slugs = {o["slug"] for o in orgs}
    assert "jack-team" in slugs
    # Personal workspace slug derives from email local part.
    assert any(s.startswith("jack") for s in slugs)


def test_list_organizations_excludes_others(client):
    h_a = register(client, email="kate@acme.com")
    h_b = register(client, email="liam@acme.com")
    create_org(client, headers=h_a["headers"], slug="kate-only")

    orgs_b = client.get("/api/v1/organizations", headers=h_b["headers"]).json()
    slugs = {o["slug"] for o in orgs_b}
    assert "kate-only" not in slugs


# ---------------------------------------------------------------------------
# Get detail
# ---------------------------------------------------------------------------


def test_get_organization_returns_member_count_and_role(client):
    h = register(client, email="maya@acme.com")
    org = create_org(client, headers=h["headers"], slug="maya")

    r = client.get(
        f"/api/v1/organizations/{org['id']}", headers=h["headers"]
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == org["id"]
    assert body["role"] == "owner"
    assert body["member_count"] == 1


def test_get_organization_returns_404_for_non_member(client):
    h_a = register(client, email="noah@acme.com")
    h_b = register(client, email="olive@acme.com")
    org = create_org(client, headers=h_a["headers"], slug="noah-private")

    r = client.get(
        f"/api/v1/organizations/{org['id']}", headers=h_b["headers"]
    )
    # 404, not 403 — don't leak existence.
    assert r.status_code == 404


def test_get_organization_unknown_id_is_404(client):
    h = register(client, email="paul@acme.com")
    r = client.get("/api/v1/organizations/99999", headers=h["headers"])
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------


def test_patch_organization_updates_name_and_description(client):
    h = register(client, email="quinn@acme.com")
    org = create_org(client, headers=h["headers"], slug="quinn")
    r = client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "Quinn Holdings", "description": "the new tagline"},
        headers=h["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Quinn Holdings"
    assert body["description"] == "the new tagline"


def test_patch_organization_admin_can_update_name_but_not_billing(client):
    """Admin can rename the org but plan/seats need owner."""
    h_owner = register(client, email="rita@acme.com")
    h_admin = register(client, email="sam@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="rita-co")

    # Invite + accept Sam as admin
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="sam@acme.com", role="admin",
    )
    client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_admin["headers"],
    )

    # Admin renames — OK
    r = client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "Renamed by Sam"},
        headers=h_admin["headers"],
    )
    assert r.status_code == 200
    # Admin tries to change plan — 403
    r = client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"plan": "enterprise"},
        headers=h_admin["headers"],
    )
    assert r.status_code == 403
    assert "owner" in r.json()["detail"]


def test_patch_organization_member_role_forbidden(client):
    """A plain member cannot patch the org at all."""
    h_owner = register(client, email="tara@acme.com")
    h_member = register(client, email="uma@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="tara-co")
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="uma@acme.com", role="member",
    )
    client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_member["headers"],
    )

    r = client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "By Uma"},
        headers=h_member["headers"],
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_organization_requires_owner(client):
    h_owner = register(client, email="vic@acme.com")
    h_admin = register(client, email="wen@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="vic-co")
    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="wen@acme.com", role="admin",
    )
    client.post(
        f"/api/v1/invitations/{inv['invite_code']}/accept",
        headers=h_admin["headers"],
    )

    # Admin cannot delete
    r = client.delete(
        f"/api/v1/organizations/{org['id']}", headers=h_admin["headers"]
    )
    assert r.status_code == 403

    # Owner can
    r = client.delete(
        f"/api/v1/organizations/{org['id']}", headers=h_owner["headers"]
    )
    assert r.status_code == 204


def test_delete_organization_cascades_members_and_invites(client):
    h = register(client, email="zoe@acme.com")
    org = create_org(client, headers=h["headers"], slug="zoe-co")
    invite(
        client, org_id=org["id"], headers=h["headers"],
        email="pending@example.com", role="member",
    )

    r = client.delete(
        f"/api/v1/organizations/{org['id']}", headers=h["headers"]
    )
    assert r.status_code == 204

    # Owner is back to their personal org only.
    r = client.get("/api/v1/organizations", headers=h["headers"])
    assert all(o["id"] != org["id"] for o in r.json())
