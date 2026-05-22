"""Unit tests for :func:`app.services.oauth.google.extract_userinfo`."""

from __future__ import annotations

import pytest

from app.services.oauth.google import GoogleUserInfo, extract_userinfo


def test_extract_userinfo_from_nested_claim():
    token = {
        "access_token": "x",
        "userinfo": {
            "sub": "abc",
            "email": "a@b.com",
            "email_verified": True,
            "name": "A",
            "picture": "https://p",
        },
    }
    info = extract_userinfo(token)
    assert isinstance(info, GoogleUserInfo)
    assert info.sub == "abc"
    assert info.email == "a@b.com"
    assert info.email_verified is True
    assert info.name == "A"
    assert info.picture == "https://p"


def test_extract_userinfo_lowercases_email():
    token = {"userinfo": {"sub": "1", "email": "MixedCase@Example.COM"}}
    info = extract_userinfo(token)
    assert info.email == "mixedcase@example.com"


def test_extract_userinfo_defaults_email_verified_to_false():
    token = {"userinfo": {"sub": "1", "email": "a@b.com"}}
    info = extract_userinfo(token)
    assert info.email_verified is False


def test_extract_userinfo_falls_back_to_inline_claims():
    """Token without a ``userinfo`` key — claims live at top level."""
    token = {
        "sub": "inline",
        "email": "i@b.com",
        "email_verified": True,
        "name": "Inline",
    }
    info = extract_userinfo(token)
    assert info.sub == "inline"
    assert info.email == "i@b.com"


def test_extract_userinfo_raises_without_sub():
    with pytest.raises(ValueError):
        extract_userinfo({"userinfo": {"email": "a@b.com"}})


def test_extract_userinfo_raises_without_email():
    with pytest.raises(ValueError):
        extract_userinfo({"userinfo": {"sub": "a"}})


def test_extract_userinfo_raises_on_empty_token():
    with pytest.raises(ValueError):
        extract_userinfo({})


def test_extract_userinfo_preserves_raw():
    token = {
        "userinfo": {
            "sub": "abc",
            "email": "a@b.com",
            "locale": "en-US",
            "given_name": "Alice",
        }
    }
    info = extract_userinfo(token)
    # Extra fields land in ``raw`` for the OAuthAccount snapshot.
    assert info.raw["locale"] == "en-US"
    assert info.raw["given_name"] == "Alice"
