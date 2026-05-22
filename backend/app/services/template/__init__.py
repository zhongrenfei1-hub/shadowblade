"""Video template framework — declarative rule sets layered on top of
MixRequest.

A *template* is a versioned JSON document that bundles transition style,
subtitle policy, pacing, BGM volume curve, cover style, watermark rules,
intelligent clip-selection rules, and color/encode preset into one named
preset (e.g. ``base``, ``social_punchy``, ``cinematic_calm``).

Templates are pure data — they never run ffmpeg directly. The
:mod:`pipeline` consumes ``MixRequest`` exclusively; templates fold into
that request via :func:`apply.apply_template_to_request`.

Public API
----------
- :class:`Template`             — the validated schema
- :func:`load_template`         — name → Template (cached, supports ``extends``)
- :func:`list_templates`        — discovery (builtin + user dirs)
- :func:`apply_template_to_request` — merge template into MixVideoRequest

See :mod:`schema` for the field layout, :mod:`loader` for resolution
rules, and :mod:`apply` for the user-explicit-wins merge policy.
"""

from app.services.template.apply import (
    apply_brand_and_template,
    apply_brand_kit_to_request,
    apply_template_to_mix_request,
    apply_template_to_request,
)
from app.services.template.loader import (
    TemplateNotFoundError,
    TemplateSummary,
    list_templates,
    load_template,
    template_search_paths,
)
from app.services.template.schema import (
    Template,
    TemplateAudio,
    TemplateColor,
    TemplateCover,
    TemplateEncode,
    TemplateHighlight,
    TemplateKenBurns,
    TemplatePacing,
    TemplateSubtitle,
    TemplateTransition,
    TemplateWatermark,
)

__all__ = [
    "Template",
    "TemplateAudio",
    "TemplateColor",
    "TemplateCover",
    "TemplateEncode",
    "TemplateHighlight",
    "TemplateKenBurns",
    "TemplatePacing",
    "TemplateSubtitle",
    "TemplateTransition",
    "TemplateWatermark",
    "TemplateNotFoundError",
    "TemplateSummary",
    "list_templates",
    "load_template",
    "template_search_paths",
    "apply_brand_and_template",
    "apply_brand_kit_to_request",
    "apply_template_to_request",
    "apply_template_to_mix_request",
]
