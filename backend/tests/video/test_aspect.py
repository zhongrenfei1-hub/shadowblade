import pytest

from app.services.video.aspect import (
    ASPECT_PRESETS,
    AspectSpec,
    get_aspect,
    reframe_filter,
)


def test_aspect_presets_inventory():
    assert "9:16" in ASPECT_PRESETS
    assert "16:9" in ASPECT_PRESETS
    assert "1:1" in ASPECT_PRESETS
    assert "4:5" in ASPECT_PRESETS


def test_get_aspect_unknown_raises():
    with pytest.raises(KeyError):
        get_aspect("3:5")


def test_reframe_pad_produces_pad_filter():
    target = get_aspect("9:16")
    f = reframe_filter(target=target, mode="pad")
    assert "pad=1080:1920" in f
    assert "force_original_aspect_ratio=decrease" in f


def test_reframe_crop_uses_saliency():
    target = get_aspect("1:1")
    f = reframe_filter(target=target, mode="crop", saliency_x=0.7, saliency_y=0.4)
    assert "crop=1080:1080" in f
    assert "iw*0.700" in f
    assert "ih*0.400" in f


def test_reframe_blur_bg_has_split_and_overlay():
    target = get_aspect("9:16")
    f = reframe_filter(target=target, mode="blur_bg")
    assert "split" in f
    assert "gblur" in f
    assert "overlay" in f
