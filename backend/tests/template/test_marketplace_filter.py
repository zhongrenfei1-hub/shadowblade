"""GET /api/v1/templates filter parameters — aspect / purpose / tag / builtin.

The filter combination is AND. Each query reduces the candidate set
independently before the response is built. ``aspect`` and ``purpose``
require parsing the full template content (extends resolved); ``tag``
and ``builtin`` only touch the cheap summary.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _names(resp_json) -> set[str]:
    return {it["name"] for it in resp_json["items"]}


# ---------- baseline -------------------------------------------------------


def test_no_filter_returns_all_known_templates():
    r = client.get("/api/v1/templates?fresh=true")
    assert r.status_code == 200
    body = r.json()
    names = _names(body)
    # Every shipped template should be visible
    assert "base" in names
    assert "product-demo" in names
    assert "product-demo-vertical" in names
    assert "product-demo-tutorial" in names
    assert body["total"] == len(body["items"])


# ---------- builtin --------------------------------------------------------


def test_filter_builtin_true_returns_only_builtin():
    r = client.get("/api/v1/templates?builtin=true&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    # Only the package-bundled "base" is builtin
    assert names == {"base"}


def test_filter_builtin_false_excludes_builtin():
    r = client.get("/api/v1/templates?builtin=false&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    assert "base" not in names
    assert "product-demo" in names


# ---------- aspect ---------------------------------------------------------


def test_filter_aspect_16x9_picks_horizontal_only():
    r = client.get("/api/v1/templates?aspect=16x9&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    # product-demo and product-demo-tutorial both inherit hero_16x9
    assert "product-demo" in names
    assert "product-demo-tutorial" in names
    # vertical inherits social_9x16 → excluded
    assert "product-demo-vertical" not in names
    # base is social_9x16 → excluded
    assert "base" not in names


def test_filter_aspect_9x16_picks_vertical_only():
    r = client.get("/api/v1/templates?aspect=9x16&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    assert "product-demo-vertical" in names
    assert "base" in names  # also social_9x16
    assert "product-demo" not in names


def test_aspect_accepts_colon_form():
    """``aspect=16:9`` should be normalised to the underscore form."""
    r1 = client.get("/api/v1/templates?aspect=16x9&fresh=true")
    r2 = client.get("/api/v1/templates?aspect=16:9&fresh=true")
    assert _names(r1.json()) == _names(r2.json())


# ---------- purpose --------------------------------------------------------


def test_filter_purpose_product_demo_tutorial():
    r = client.get("/api/v1/templates?purpose=product_demo_tutorial&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    # tutorial sets its own purpose; siblings have different purposes
    assert names == {"product-demo-tutorial"}


def test_filter_purpose_product_demo_excludes_tutorial_and_vertical():
    r = client.get("/api/v1/templates?purpose=product_demo&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    # Only the parent template carries purpose=product_demo verbatim;
    # children declared their own (product_demo_tutorial / _vertical).
    assert "product-demo" in names
    assert "product-demo-tutorial" not in names
    assert "product-demo-vertical" not in names


# ---------- tag ------------------------------------------------------------


def test_filter_tag_tiktok_returns_vertical_only():
    r = client.get("/api/v1/templates?tag=tiktok&fresh=true")
    assert r.status_code == 200
    assert _names(r.json()) == {"product-demo-vertical"}


def test_filter_tag_how_to_returns_tutorial_only():
    r = client.get("/api/v1/templates?tag=how-to&fresh=true")
    assert r.status_code == 200
    assert _names(r.json()) == {"product-demo-tutorial"}


def test_filter_tag_product_demo_returns_all_three():
    """All three product-demo* templates carry the 'product-demo' tag."""
    r = client.get("/api/v1/templates?tag=product-demo&fresh=true")
    assert r.status_code == 200
    names = _names(r.json())
    assert names == {"product-demo", "product-demo-vertical", "product-demo-tutorial"}


# ---------- combined ------------------------------------------------------


def test_combined_filters_intersect():
    """aspect=16x9 ∩ tag=product-demo → pd + tutorial (not vertical)."""
    r = client.get("/api/v1/templates?aspect=16x9&tag=product-demo&fresh=true")
    assert r.status_code == 200
    assert _names(r.json()) == {"product-demo", "product-demo-tutorial"}


def test_combined_filter_empty_intersection_ok():
    """A nonsense combination just returns zero items, not 4xx."""
    r = client.get("/api/v1/templates?aspect=1x1&tag=tiktok&fresh=true")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


# ---------- aspect/purpose entries enriched with metadata ---------------


def test_aspect_filter_enriches_response_with_aspect_field():
    """When aspect filter is used, items include the resolved encode.preset."""
    r = client.get("/api/v1/templates?aspect=16x9&fresh=true")
    body = r.json()
    item = next(it for it in body["items"] if it["name"] == "product-demo")
    assert item.get("aspect") == "hero_16x9"


def test_purpose_filter_enriches_response_with_purpose_field():
    r = client.get("/api/v1/templates?purpose=product_demo_vertical&fresh=true")
    body = r.json()
    item = next(it for it in body["items"] if it["name"] == "product-demo-vertical")
    assert item.get("purpose") == "product_demo_vertical"
