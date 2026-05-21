from app.services.video.encoder import (
    PRESETS,
    audio_codec_args,
    get_preset,
    list_presets,
    normalize_clip_filter,
    video_codec_args,
)


def test_preset_inventory_includes_socials():
    names = list_presets()
    assert "social_9x16" in names
    assert "hero_16x9" in names
    assert "square_1x1" in names
    assert "preview_360_9x16" in names


def test_get_preset_unknown_raises():
    import pytest

    with pytest.raises(KeyError):
        get_preset("nope")


def test_video_codec_args_software_path():
    args = video_codec_args(get_preset("social_9x16"), hw=False)
    assert "-c:v" in args
    assert "libx264" in args
    assert "-pix_fmt" in args


def test_video_codec_args_hardware_path():
    args = video_codec_args(get_preset("social_9x16"), hw=True)
    assert "h264_videotoolbox" in args


def test_audio_args_default_48k_stereo():
    args = audio_codec_args(get_preset("social_9x16"))
    assert "48000" in args
    assert "-c:a" in args
    assert args[args.index("-c:a") + 1] == "aac"


def test_normalize_clip_filter_includes_scale_pad_fps():
    f = normalize_clip_filter(width=1080, height=1920, fps=30)
    assert "scale=1080:1920" in f
    assert "pad=1080:1920" in f
    assert "fps=30" in f
    assert "format=yuv420p" in f
