from app.services.video.audio import AudioBus, adapt_bus_to_voice_loudness


def test_adapt_quiet_voice_lifts_gain_and_strong_duck():
    bus = AudioBus()
    adapted = adapt_bus_to_voice_loudness(bus, voice_lufs=-30.0)
    # Voice is quiet → lift voice gain toward -14 target
    assert adapted.voice_gain_db > 0
    # Quiet voice → stronger duck
    assert adapted.duck_ratio >= 8.0
    # Threshold is voice_lufs + 6 dB
    assert abs(adapted.duck_threshold_db - (-24.0)) < 1e-6


def test_adapt_loud_voice_uses_softer_duck():
    bus = AudioBus()
    adapted = adapt_bus_to_voice_loudness(bus, voice_lufs=-14.0)
    assert adapted.duck_ratio <= 4.0
    # Voice already at target — voice_gain ≈ 0
    assert abs(adapted.voice_gain_db) < 1e-6


def test_adapt_preserves_target_lufs():
    bus = AudioBus(target_lufs=-16.0)
    adapted = adapt_bus_to_voice_loudness(bus, voice_lufs=-20.0)
    assert adapted.target_lufs == -16.0


def test_adapt_bgm_gain_in_reasonable_band():
    bus = AudioBus()
    for lufs in (-32, -22, -14, -8):
        adapted = adapt_bus_to_voice_loudness(bus, voice_lufs=lufs)
        assert -28.0 <= adapted.bgm_gain_db <= -6.0
