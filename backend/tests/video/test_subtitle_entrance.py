from app.services.video.subtitle import SubtitleEntrance, overlay_with_entrance


def test_overlay_none_centers_horizontally():
    chain = overlay_with_entrance(
        base_label="[v]", image_label="[png]",
        start=1.0, end=3.0, entrance=SubtitleEntrance.NONE,
    )
    assert "overlay=" in chain
    assert "between(t,1.000,3.000)" in chain


def test_overlay_slide_up_uses_y_ramp():
    chain = overlay_with_entrance(
        base_label="[v]", image_label="[png]",
        start=2.0, end=4.0, entrance=SubtitleEntrance.SLIDE_UP,
    )
    assert "if(lt(t" in chain  # conditional y expression
    assert "+60*" in chain or "+60.0*" in chain or "+60.000*" in chain or "+60*(" in chain


def test_overlay_fade_default_uses_simple_overlay():
    chain = overlay_with_entrance(
        base_label="[v]", image_label="[png]",
        start=0.5, end=2.5, entrance=SubtitleEntrance.FADE,
    )
    assert "overlay=" in chain
    assert "between(t,0.500,2.500)" in chain
