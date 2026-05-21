from app.services.video.audio import AudioBus, build_voice_bgm_mix, build_voice_only


def test_voice_bgm_mix_has_sidechain_and_loudnorm():
    chain = build_voice_bgm_mix(
        voice_label="[1:a]",
        bgm_label="[2:a]",
        duration=12.0,
        bus=AudioBus(target_lufs=-14.0),
        out_label="[mix]",
    )
    assert "sidechaincompress" in chain
    assert "loudnorm=I=-14" in chain
    assert chain.rstrip().endswith("[mix]")
    assert "highpass=f=80" in chain
    assert "acompressor" in chain
    # makeup must be within the valid [1,64] range
    assert "makeup=0" not in chain


def test_voice_only_skips_sidechain():
    chain = build_voice_only(voice_label="[1:a]", out_label="[aout]")
    assert "sidechaincompress" not in chain
    assert "loudnorm" in chain
    assert chain.rstrip().endswith("[aout]")


def test_audio_bus_defaults_are_social():
    bus = AudioBus()
    assert bus.target_lufs == -14.0
    assert bus.duck_release_ms >= 200
