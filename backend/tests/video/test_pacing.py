import pytest

from app.services.video.pacing import (
    SpeechSegment,
    detect_silences,
    plan_cuts,
    plan_from_audio,
    speech_from_silences,
)


@pytest.mark.asyncio
async def test_detect_silences_finds_gaps(synth_voice):
    silences = await detect_silences(str(synth_voice), noise_db=-30, min_silence=0.4)
    # synth_voice toggles every 1.7s on / 0.7s off across 8s — expect ≥ 2 gaps
    assert len(silences) >= 2
    for s in silences:
        assert s.duration > 0.3


def test_speech_from_silences_inverts():
    from app.services.video.pacing import SilenceRange

    sil = [SilenceRange(2.0, 2.5), SilenceRange(5.0, 5.4)]
    speech = speech_from_silences(sil, total_duration=8.0)
    assert speech[0].start == 0.0
    assert speech[0].end == 2.0
    assert speech[-1].end == 8.0


def test_plan_cuts_respects_min_and_max_shot():
    speech = [
        SpeechSegment(0.0, 2.0),
        SpeechSegment(2.5, 5.0),
        SpeechSegment(5.4, 9.0),
        SpeechSegment(9.2, 14.0),
    ]
    plan = plan_cuts(speech, target_shot=3.0, min_shot=1.2, max_shot=4.0)
    for d in plan.shot_durations:
        assert d <= 4.0 + 1e-6
        assert d >= 1.2 - 1e-6
    assert sum(plan.shot_durations) == pytest.approx(14.0, abs=0.6)


@pytest.mark.asyncio
async def test_plan_from_audio_end_to_end(synth_voice):
    plan = await plan_from_audio(str(synth_voice), target_shot=2.0, min_shot=1.0, max_shot=4.0)
    assert plan.cut_points[0] == 0.0
    assert plan.shot_durations  # non-empty
    assert plan.silences
