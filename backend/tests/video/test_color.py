import pytest

from app.services.video.color import (
    PRESETS,
    apply_lut,
    apply_preset,
    auto_white_balance,
    compose_color_chain,
)


def test_apply_preset_known_returns_chain():
    chain = apply_preset("cinematic")
    assert "eq=" in chain
    assert "colorbalance" in chain


def test_apply_preset_natural_returns_empty():
    assert apply_preset("natural") == ""


def test_apply_preset_unknown_returns_empty():
    assert apply_preset("does-not-exist") == ""


def test_apply_lut_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        apply_lut(tmp_path / "missing.cube")


def test_apply_lut_present(tmp_path):
    p = tmp_path / "look.cube"
    p.write_text("# minimal stub\nLUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n")
    chain = apply_lut(p)
    assert "lut3d=file=" in chain
    assert "tetrahedral" in chain


def test_compose_color_chain_combines_in_order():
    chain = compose_color_chain(preset="warm", auto_wb=True)
    parts = chain.split(",")
    assert any("colorlevels" in p for p in parts[:2])
    assert any("eq=" in p for p in parts)


def test_preset_inventory_contains_brand_palette():
    for name in ("warm", "cool", "cinematic", "punchy", "mono", "vintage"):
        assert name in PRESETS
