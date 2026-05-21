from app.services.video.watermark import (
    WatermarkPosition,
    WatermarkSpec,
    build_text_watermark,
    build_watermark_chain,
)


def test_watermark_chain_uses_scale2ref():
    chain = build_watermark_chain(
        video_label="[base]",
        logo_label="[logo]",
        duration=10.0,
        spec=WatermarkSpec(),
        out_label="[wm]",
    )
    assert "scale2ref" in chain
    assert "overlay=" in chain
    assert chain.rstrip().endswith("[wm]")


def test_text_watermark_uses_drawtext():
    chain = build_text_watermark(
        video_label="[base]",
        text="@shadowblade",
        duration=10.0,
        out_label="[wm]",
    )
    assert "drawtext=" in chain
    assert "@shadowblade" in chain


def test_position_bottom_right_default():
    spec = WatermarkSpec()
    assert spec.position == WatermarkPosition.BOTTOM_RIGHT
