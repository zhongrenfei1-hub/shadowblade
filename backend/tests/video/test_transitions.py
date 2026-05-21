from app.services.video.transitions import (
    ShotSignal,
    TransitionKind,
    build_xfade_chain,
    select_transition,
)


def test_chapter_break_uses_fadeblack():
    a = ShotSignal(duration=4.0, is_chapter_break=True)
    b = ShotSignal(duration=3.0)
    plan = select_transition(a, b)
    assert plan.kind == TransitionKind.FADEBLACK


def test_hero_uses_fadewhite():
    a = ShotSignal(duration=4.0)
    b = ShotSignal(duration=3.0, is_hero=True)
    plan = select_transition(a, b)
    assert plan.kind == TransitionKind.FADEWHITE
    assert plan.duration <= 0.35


def test_brightness_jump_picks_dissolve():
    a = ShotSignal(duration=3.0, brightness=0.05)
    b = ShotSignal(duration=3.0, brightness=0.95)
    plan = select_transition(a, b)
    assert plan.kind == TransitionKind.DISSOLVE


def test_motion_picks_smooth_pan():
    a = ShotSignal(duration=3.0, motion=0.8)
    b = ShotSignal(duration=3.0, motion=0.65)
    plan = select_transition(a, b, style="editorial")
    assert plan.kind in {TransitionKind.SMOOTHLEFT, TransitionKind.SMOOTHRIGHT}


def test_motion_in_energetic_picks_hblur():
    a = ShotSignal(duration=3.0, motion=0.85)
    b = ShotSignal(duration=3.0, motion=0.8)
    plan = select_transition(a, b, style="energetic")
    assert plan.kind == TransitionKind.HBLUR


def test_calm_overrides_to_fade():
    a = ShotSignal(duration=3.0, brightness=0.05)
    b = ShotSignal(duration=3.0, brightness=0.95)
    plan = select_transition(a, b, style="calm")
    assert plan.kind == TransitionKind.FADE


def test_build_xfade_chain_three_clips():
    durations = [3.0, 2.5, 2.0]
    plans = [
        select_transition(ShotSignal(3.0), ShotSignal(2.5)),
        select_transition(ShotSignal(2.5), ShotSignal(2.0)),
    ]
    chain, vlabel, alabel = build_xfade_chain(durations, plans)
    assert "xfade" in chain
    assert "acrossfade" in chain
    assert vlabel.startswith("[vx")
    assert alabel.startswith("[ax")


def test_build_xfade_chain_single_clip():
    chain, vlabel, alabel = build_xfade_chain([3.0], [])
    assert chain == ""
    assert vlabel == "[v0]"
    assert alabel == "[a0]"
