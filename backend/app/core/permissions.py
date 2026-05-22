"""Role hierarchy and permission helpers for the Team feature.

Single source of truth for *what each role can do*. The endpoint layer
imports :func:`require_role`/:func:`has_permission`; the resource layer
(brand-kit resolver, mix-video gate) imports :data:`ROLE_HIERARCHY` and
the constants.

Roles, from most to least privileged:

    owner > admin > member > guest

Owner is unique per workspace and protected by invariants enforced in
``api/organizations.py`` — you can transfer it but never delete the last
owner without promoting someone first.

Permission strings are intentionally verb-noun and lowercase so the
frontend can use the same vocabulary for its capability checks.
"""

from __future__ import annotations

from typing import Final

# Larger number = more privileged. Used by :func:`role_at_least`.
ROLE_HIERARCHY: Final[dict[str, int]] = {
    "guest": 0,
    "member": 1,
    "admin": 2,
    "owner": 3,
}

# The string literals that ``WorkspaceMember.role`` is allowed to hold.
ALLOWED_ROLES: Final[tuple[str, ...]] = tuple(ROLE_HIERARCHY.keys())

# Friendlier aliases the frontend used historically. Resolved to the
# canonical name in :func:`normalize_role` before storage so the rest of
# the system (DB, permission matrix, audit logs) stays clean.
#
# ``editor`` and ``viewer`` come from the React UI that predates the
# Team work — keeping them as aliases means we don't 422 a perfectly
# reasonable request just because the term-of-art shifted.
ROLE_ALIASES: Final[dict[str, str]] = {
    "editor": "member",
    "viewer": "guest",
}


def normalize_role(value: str) -> str:
    """Map a possibly-aliased role string to its canonical form.

    Returns the input unchanged if no alias exists; the caller still has
    to validate that the result is a known role.
    """
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    v = value.strip().lower()
    return ROLE_ALIASES.get(v, v)

# Per-role capability matrix. Anything not listed here is *implicitly
# denied* — the helpers below check membership, not absence.
PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    "owner": frozenset(
        {
            "org:read",
            "org:update",
            "org:delete",
            "org:transfer",
            "member:read",
            "member:invite",
            "member:update_role",
            "member:remove",
            "invite:create",
            "invite:list",
            "invite:revoke",
            "brand_kit:read",
            "brand_kit:write",
            "project:read",
            "project:write",
            "render:submit",
            "billing:read",
            "billing:write",
        }
    ),
    "admin": frozenset(
        {
            "org:read",
            "org:update",
            "member:read",
            "member:invite",
            "member:update_role",
            "member:remove",
            "invite:create",
            "invite:list",
            "invite:revoke",
            "brand_kit:read",
            "brand_kit:write",
            "project:read",
            "project:write",
            "render:submit",
            "billing:read",
        }
    ),
    "member": frozenset(
        {
            "org:read",
            "member:read",
            "invite:list",
            "brand_kit:read",
            "project:read",
            "project:write",
            "render:submit",
        }
    ),
    "guest": frozenset(
        {
            "org:read",
            "member:read",
            "brand_kit:read",
            "project:read",
        }
    ),
}


def role_at_least(actor_role: str, required_role: str) -> bool:
    """Return ``True`` when ``actor_role`` is ≥ ``required_role``.

    Unknown roles are treated as ``-1`` (less privileged than guest) so a
    typo in a header or token never accidentally grants access.
    """
    actor = ROLE_HIERARCHY.get(actor_role, -1)
    required = ROLE_HIERARCHY.get(required_role, -1)
    return actor >= required and required >= 0


def has_permission(role: str, permission: str) -> bool:
    """Return ``True`` if ``role`` is granted ``permission``."""
    return permission in PERMISSIONS.get(role, frozenset())


def assert_role_value(role: str) -> str:
    """Validate ``role`` (raises ``ValueError`` on miss) and return canonical.

    Use at trust boundaries — e.g. when accepting a role string from the
    request body for an invite or membership update. Resolves aliases
    (``editor`` → ``member``, ``viewer`` → ``guest``) before checking,
    so the frontend can speak either dialect.
    """
    canonical = normalize_role(role)
    if canonical not in ROLE_HIERARCHY:
        raise ValueError(
            f"unknown role {role!r}; expected one of "
            f"{sorted(ROLE_HIERARCHY)} (aliases: {sorted(ROLE_ALIASES)})"
        )
    return canonical


__all__ = [
    "ALLOWED_ROLES",
    "PERMISSIONS",
    "ROLE_ALIASES",
    "ROLE_HIERARCHY",
    "assert_role_value",
    "has_permission",
    "normalize_role",
    "role_at_least",
]
