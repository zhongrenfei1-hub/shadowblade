"""Loader resolution, caching, extends-cycle detection, builtin fallback."""

from __future__ import annotations

import pytest

from app.services.template.loader import (
    TemplateNotFoundError,
    list_templates,
    load_template,
    template_search_paths,
)
from tests.template.conftest import write_template


def test_load_builtin_base_works_without_overrides():
    # The builtin "base" should always resolve even with no user dir.
    t = load_template("base", fresh=True)
    assert t.name == "base"
    assert t.transition.style == "editorial"
    assert t.encode.preset == "social_9x16"


def test_user_dir_overrides_builtin(template_dir):
    write_template(
        template_dir,
        "base",
        {"name": "base", "transition": {"style": "energetic"}},
    )
    t = load_template("base", fresh=True)
    # User dir came first in the search path → its file wins.
    assert t.transition.style == "energetic"


def test_unknown_template_raises(template_dir):
    with pytest.raises(TemplateNotFoundError):
        load_template("doesnt_exist", fresh=True)


def test_filename_fills_missing_name(template_dir):
    write_template(template_dir, "my_slug", {"transition": {"style": "calm"}})
    t = load_template("my_slug", fresh=True)
    assert t.name == "my_slug"
    assert t.transition.style == "calm"


def test_extends_resolves_parent_chain(template_dir):
    write_template(template_dir, "parent", {"transition": {"style": "editorial", "max_duration": 0.4}})
    write_template(template_dir, "child", {"extends": "parent", "color": {"look": "warm"}})
    t = load_template("child", fresh=True)
    assert t.extends is None  # resolved
    assert t.transition.style == "editorial"
    assert t.transition.max_duration == 0.4
    assert t.color.look == "warm"


def test_extends_cycle_detected(template_dir):
    write_template(template_dir, "a", {"extends": "b"})
    write_template(template_dir, "b", {"extends": "a"})
    with pytest.raises(RuntimeError, match="cycle"):
        load_template("a", fresh=True)


def test_list_templates_includes_user_and_builtin(template_dir):
    write_template(template_dir, "vlog_warm", {"color": {"look": "warm"}})
    names = {s.name for s in list_templates()}
    assert "base" in names  # builtin
    assert "vlog_warm" in names  # user

    user_entry = next(s for s in list_templates() if s.name == "vlog_warm")
    assert user_entry.builtin is False
    builtin_entry = next(s for s in list_templates() if s.name == "base")
    assert builtin_entry.builtin is True


def test_search_paths_env_override_first(template_dir):
    paths = template_search_paths()
    assert paths[0] == template_dir
