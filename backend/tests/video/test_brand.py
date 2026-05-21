from app.services.video.brand import BrandKit, _hex_to_ass


def test_hex_to_ass_six_digit():
    assert _hex_to_ass("#22D3B7") == "&H00B7D322"


def test_hex_to_ass_eight_digit_keeps_alpha():
    assert _hex_to_ass("#22D3B780") == "&H80B7D322"


def test_brand_kit_subtitle_style_uses_brand_colors():
    kit = BrandKit(
        primary_color="#101728",
        accent_color="#FF7849",
        secondary_color="#FFFFFF",
        font_body="JetBrains Mono",
    )
    style = kit.subtitle_style()
    assert style.font == "JetBrains Mono"
    assert style.primary == "&H00FFFFFF"  # white
    assert style.outline_color.startswith("&H40")


def test_brand_kit_from_dict_round_trips():
    kit = BrandKit.from_dict(
        {
            "name": "Acme",
            "primary_color": "#000000",
            "accent_color": "#FF0000",
            "target_lufs": -16.0,
            "watermark_position": "tl",
        }
    )
    assert kit.name == "Acme"
    assert kit.target_lufs == -16.0
    assert kit.watermark_position == "tl"
