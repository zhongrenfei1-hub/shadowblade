from app.services.video.speed import SpeedSpec, apply_to_clip, atempo_chain, setpts_expr


def test_setpts_identity():
    assert setpts_expr(1.0) == ""


def test_setpts_double_speed_halves_pts():
    expr = setpts_expr(2.0)
    assert "PTS/2" in expr


def test_atempo_within_native_range():
    assert atempo_chain(1.5) == "atempo=1.5000"


def test_atempo_chains_for_extreme_slow():
    chain = atempo_chain(0.25)
    parts = chain.split(",")
    # need at least one atempo=0.5
    assert any("atempo=0.5" in p for p in parts)


def test_atempo_chains_for_extreme_fast():
    chain = atempo_chain(4.0)
    parts = chain.split(",")
    assert sum(1 for p in parts if "atempo=2.0" in p) >= 2


def test_speedspec_clamp_extremes():
    s = SpeedSpec(factor=20).clamp()
    assert s.factor == 8.0
    s = SpeedSpec(factor=-1).clamp()
    assert s.factor == 0.1


def test_apply_to_clip_returns_labelled_chains():
    v, a = apply_to_clip(
        video_label="[v0]", audio_label="[a0]",
        spec=SpeedSpec(factor=2.0),
        out_v="[vs0]", out_a="[as0]",
    )
    assert "[v0]" in v and "[vs0]" in v and "PTS/2" in v
    assert "[a0]" in a and "[as0]" in a and "atempo=2" in a
