"""CLI + JSON Schema endpoint coverage.

The CLI is exercised via direct function calls (no subprocess overhead);
the JSON Schema endpoint is hit through TestClient.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.template.__main__ import (
    main,
    _diff_dict,
)

client = TestClient(app)


# ---------- JSON Schema endpoint -------------------------------------------


def test_schema_endpoint_returns_pydantic_schema():
    r = client.get("/api/v1/templates/_schema")
    assert r.status_code == 200
    schema = r.json()
    assert schema.get("type") == "object"
    props = schema.get("properties", {})
    # All ten first-class groups should appear
    for group in (
        "transition", "subtitle", "pacing", "audio",
        "cover", "watermark", "color", "encode",
        "ken_burns", "highlight",
    ):
        assert group in props, f"missing schema group: {group}"
    # And metadata fields
    for meta in ("name", "version", "description", "extends", "tags", "extras"):
        assert meta in props


def test_schema_endpoint_required_fields():
    r = client.get("/api/v1/templates/_schema")
    body = r.json()
    # Only ``name`` is required at the top level
    assert body.get("required") == ["name"]


def test_schema_endpoint_resolves_nested_definitions():
    """Pydantic emits ``$defs`` for the group sub-models — verify they exist."""
    r = client.get("/api/v1/templates/_schema")
    body = r.json()
    defs = body.get("$defs", {})
    assert "TemplateTransition" in defs
    assert "TemplateKenBurns" in defs
    assert "TemplateHighlight" in defs


# ---------- CLI: list ------------------------------------------------------


def test_cli_list_text_mode(capsys):
    rc = main(["list"])
    assert rc == 0
    captured = capsys.readouterr()
    out = captured.out
    for name in ("base", "product-demo", "product-demo-vertical", "product-demo-tutorial"):
        assert name in out
    # Inheritance markers should appear
    assert "← base" in out
    assert "← product-demo" in out


def test_cli_list_json_mode(capsys):
    rc = main(["list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    names = {entry["name"] for entry in payload}
    assert "product-demo" in names
    pd = next(e for e in payload if e["name"] == "product-demo")
    assert pd["extends"] == "base"
    assert pd["builtin"] is False
    assert "saas" in pd["tags"]


# ---------- CLI: show ------------------------------------------------------


def test_cli_show_emits_resolved_json(capsys):
    rc = main(["show", "product-demo"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "product-demo"
    assert payload["extends"] is None  # resolved
    assert payload["encode"]["preset"] == "hero_16x9"
    # Ken Burns from product-demo
    assert payload["ken_burns"]["intensity"] == "subtle"


def test_cli_show_unknown_returns_nonzero(capsys):
    rc = main(["show", "no-such-template"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


# ---------- CLI: validate --------------------------------------------------


def test_cli_validate_ok(tmp_path, capsys):
    f = tmp_path / "valid.json"
    f.write_text(json.dumps({"transition": {"style": "calm"}}), encoding="utf-8")
    rc = main(["validate", str(f)])
    assert rc == 0
    assert "valid" in capsys.readouterr().out  # filename token


def test_cli_validate_malformed_json(tmp_path, capsys):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    rc = main(["validate", str(f)])
    assert rc == 2
    assert "malformed" in capsys.readouterr().err.lower()


def test_cli_validate_schema_violation(tmp_path, capsys):
    f = tmp_path / "fancy.json"
    f.write_text(
        json.dumps({"transition": {"style": "neon_blast"}}),  # invalid Literal
        encoding="utf-8",
    )
    rc = main(["validate", str(f)])
    assert rc == 1
    assert "validation failed" in capsys.readouterr().err.lower()


def test_cli_validate_missing_file(tmp_path, capsys):
    rc = main(["validate", str(tmp_path / "ghost.json")])
    assert rc == 2
    assert "not found" in capsys.readouterr().err.lower()


# ---------- CLI: schema ----------------------------------------------------


def test_cli_schema_outputs_json(capsys):
    rc = main(["schema"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "$defs" in payload
    assert "properties" in payload


# ---------- CLI: diff ------------------------------------------------------


def test_cli_diff_two_templates(capsys):
    rc = main(["diff", "product-demo", "product-demo-vertical"])
    assert rc == 0
    out = capsys.readouterr().out
    # vertical-specific overrides should appear in the diff
    assert "encode.preset" in out
    assert "social_9x16" in out
    assert "cover.brand_strip_position" in out


def test_cli_diff_json_mode(capsys):
    rc = main(["diff", "product-demo", "product-demo-vertical", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "encode.preset" in payload
    a, b = payload["encode.preset"]
    assert a == "hero_16x9"
    assert b == "social_9x16"


def test_diff_dict_handles_nested():
    a = {"x": {"y": 1, "z": 2}, "k": 5}
    b = {"x": {"y": 1, "z": 3}, "k": 5}
    d = _diff_dict(a, b)
    assert d == {"x.z": (2, 3)}


def test_diff_dict_marks_missing_keys():
    a = {"a": 1}
    b = {"b": 2}
    d = _diff_dict(a, b)
    assert d == {"a": (1, "<missing>"), "b": ("<missing>", 2)}


# ---------- CLI: search-paths ---------------------------------------------


def test_cli_search_paths(capsys):
    rc = main(["search-paths"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "templates" in out
    assert "builtin" in out


# ---------- subprocess smoke test ------------------------------------------


def test_subprocess_invocation_works():
    """A real ``python -m`` call should also work — proves the
    entry point is registered correctly, not just the module-level main."""
    result = subprocess.run(
        [sys.executable, "-m", "app.services.template", "list", "--json"],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[2]),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    names = {e["name"] for e in payload}
    assert "product-demo" in names
