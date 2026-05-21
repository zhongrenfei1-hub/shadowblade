from app.services.video.ken_burns import (
    KenBurnsMode,
    KenBurnsSpec,
    auto_mode,
    build_ken_burns,
)


def test_build_ken_burns_in_includes_zoompan():
    f = build_ken_burns(
        duration=3.0,
        fps=30,
        width=1080,
        height=1920,
        spec=KenBurnsSpec(mode=KenBurnsMode.IN),
    )
    assert "zoompan" in f
    assert "s=1080x1920" in f
    assert "fps=30" in f
    assert "scale=" in f


def test_build_ken_burns_out_starts_at_max_zoom():
    f = build_ken_burns(
        duration=3.0, fps=30, width=720, height=720,
        spec=KenBurnsSpec(mode=KenBurnsMode.OUT, zoom_end=1.2),
    )
    assert "zoompan" in f
    # OUT mode references the end zoom factor as the initial state
    assert "1.2" in f


def test_pan_modes_use_x_drift():
    left = build_ken_burns(duration=3.0, fps=30, width=1080, height=1920,
                           spec=KenBurnsSpec(mode=KenBurnsMode.PAN_LEFT))
    right = build_ken_burns(duration=3.0, fps=30, width=1080, height=1920,
                            spec=KenBurnsSpec(mode=KenBurnsMode.PAN_RIGHT))
    assert "iw-(iw/zoom)" in left
    assert "iw*0.06" in right


def test_auto_mode_alternates():
    seen = {auto_mode(i) for i in range(8)}
    assert seen == set(KenBurnsMode)
