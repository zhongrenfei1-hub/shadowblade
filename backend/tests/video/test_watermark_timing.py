from app.services.video.watermark import WatermarkSpec, build_watermark_chain


def test_watermark_default_visible_full_duration():
    chain = build_watermark_chain(
        video_label="[base]", logo_label="[logo]", duration=10.0,
        spec=WatermarkSpec(), out_label="[wm]",
    )
    assert "between(t,0.000,10.000)" in chain


def test_watermark_visible_window():
    chain = build_watermark_chain(
        video_label="[base]", logo_label="[logo]", duration=10.0,
        spec=WatermarkSpec(visible_from=2.0, visible_to=6.0),
        out_label="[wm]",
    )
    assert "between(t,2.000,6.000)" in chain


def test_watermark_pulse_includes_sine():
    chain = build_watermark_chain(
        video_label="[base]", logo_label="[logo]", duration=10.0,
        spec=WatermarkSpec(pulse_period=1.2),
        out_label="[wm]",
    )
    assert "sin(2*PI*t/1.200)" in chain
