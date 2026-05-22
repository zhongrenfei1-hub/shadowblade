"""Schema validation + parent/child merge semantics."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.services.template.schema import (
    Template,
    TemplateColor,
    TemplatePacing,
    TemplateTransition,
)


def test_minimal_template_only_requires_name():
    t = Template(name="x")
    assert t.name == "x"
    assert t.version == "1.0.0"
    assert t.transition.style is None
    assert t.color.look is None


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        Template.model_validate({"name": "x", "transition": {"style": "editorial", "bogus": 1}})


def test_invalid_style_literal_rejected():
    with pytest.raises(ValidationError):
        TemplateTransition.model_validate({"style": "fancy_stuff"})


def test_color_look_literal_rejected():
    with pytest.raises(ValidationError):
        TemplateColor.model_validate({"look": "neon"})


def test_pacing_bounds_enforced():
    with pytest.raises(ValidationError):
        TemplatePacing.model_validate({"target_shot": 999.0})


def test_merged_with_child_overrides_parent_non_null():
    parent = Template(
        name="base",
        transition=TemplateTransition(style="editorial", max_duration=0.45),
        color=TemplateColor(look="natural"),
    )
    child = Template(
        name="punchy",
        transition=TemplateTransition(style="energetic"),  # max_duration stays None
        color=TemplateColor(look="punchy"),
        extends="base",
    )
    merged = parent.merged_with(child)
    assert merged.name == "punchy"
    assert merged.extends is None  # resolved
    assert merged.transition.style == "energetic"  # child wins
    assert merged.transition.max_duration == 0.45  # parent kept (child was None)
    assert merged.color.look == "punchy"


def test_merged_with_tags_deduplicated():
    parent = Template(name="base", tags=["builtin", "social"])
    child = Template(name="punchy", tags=["social", "ads"], extends="base")
    merged = parent.merged_with(child)
    assert merged.tags == ["builtin", "social", "ads"]


def test_merged_with_extras_shallow_merged():
    parent = Template(name="base", extras={"a": 1, "b": 2})
    child = Template(name="c", extras={"b": 99, "c": 3}, extends="base")
    merged = parent.merged_with(child)
    assert merged.extras == {"a": 1, "b": 99, "c": 3}
