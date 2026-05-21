from app.services.video.selector import CandidateClip, select_clips


def test_select_clips_basic():
    pool = [
        CandidateClip(path="a.mp4", duration=4, score=0.9, is_hero=True),
        CandidateClip(path="b.mp4", duration=3, score=0.7),
        CandidateClip(path="c.mp4", duration=5, score=0.6),
        CandidateClip(path="d.mp4", duration=2, score=0.5),
    ]
    plan = select_clips(pool, target_total=10.0, target_shot=2.5, min_shot=1.5, max_shot=4.0)
    assert len(plan.shots) >= 2
    assert plan.used_hero_count >= 1
    assert all(s.use_duration >= 1.5 - 1e-6 for s in plan.shots)
    assert all(s.use_duration <= 4.0 + 1e-6 for s in plan.shots)


def test_select_clips_respects_pool_size():
    pool = [CandidateClip(path=f"{i}.mp4", duration=5, score=0.5) for i in range(2)]
    plan = select_clips(pool, target_total=30.0, target_shot=2.0, min_shot=1.0, max_shot=4.0)
    assert len(plan.shots) <= 2  # can't exceed pool


def test_select_clips_must_include_hero():
    pool = [
        CandidateClip(path="hero.mp4", duration=3, score=0.4, is_hero=True),
        CandidateClip(path="b.mp4", duration=3, score=0.95),
        CandidateClip(path="c.mp4", duration=3, score=0.92),
    ]
    plan = select_clips(pool, target_total=6.0, target_shot=3.0, must_include_hero=True)
    assert plan.used_hero_count == 1


def test_select_clips_empty_pool():
    plan = select_clips([], target_total=10.0)
    assert plan.shots == []
    assert plan.total_duration == 0.0
