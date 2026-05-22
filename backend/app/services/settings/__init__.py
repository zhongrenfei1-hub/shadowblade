"""Settings service layer.

Re-exports the public surface so callers can write::

    from app.services.settings import (
        get_or_create_profile_settings,
        get_or_create_org_settings,
        resolve_effective_brand_kit_id,
        resolve_render_defaults,
        on_brand_kit_deleted,
        on_brand_kit_updated,
    )

The actual implementation lives in :mod:`app.services.settings.resolver`
to keep the module flat — service callers should never import from the
private module directly.
"""

from app.services.settings.resolver import (
    get_or_create_org_settings,
    get_or_create_profile_settings,
    on_brand_kit_deleted,
    on_brand_kit_updated,
    on_template_deleted,
    resolve_effective_brand_kit_id,
    resolve_render_defaults,
)

__all__ = [
    "get_or_create_org_settings",
    "get_or_create_profile_settings",
    "on_brand_kit_deleted",
    "on_brand_kit_updated",
    "on_template_deleted",
    "resolve_effective_brand_kit_id",
    "resolve_render_defaults",
]
