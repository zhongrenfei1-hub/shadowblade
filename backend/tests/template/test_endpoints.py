"""End-to-end checks against the FastAPI router — no ffmpeg required."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.template.conftest import write_template

client = TestClient(app)
# Don't bubble up server exceptions — we want to assert on side effects
# of partial endpoint runs.
client_lenient = TestClient(app, raise_server_exceptions=False)


def test_list_templates_returns_base():
    r = client.get("/api/v1/templates")
    assert r.status_code == 200
    names = [item["name"] for item in r.json()["items"]]
    assert "base" in names


def test_get_template_resolves_extends(template_dir):
    write_template(template_dir, "vlog_warm", {"extends": "base", "color": {"look": "warm"}})
    r = client.get("/api/v1/templates/vlog_warm?fresh=true")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["extends"] is None
    assert body["color"]["look"] == "warm"
    # Inherited from base
    assert body["transition"]["style"] == "editorial"
    assert body["encode"]["preset"] == "social_9x16"


def test_get_template_404_for_unknown(template_dir):
    r = client.get("/api/v1/templates/does_not_exist?fresh=true")
    assert r.status_code == 404


def test_mix_video_rejects_unknown_template(template_dir):
    payload = {
        "project_id": 1,
        "clips": [{"path": "/tmp/does_not_exist.mp4"}],
        "template": "absolutely_not_real",
    }
    r = client.post("/api/v1/mix-video/preview", json=payload)
    assert r.status_code == 400
    assert "unknown template" in r.json()["detail"].lower()


def test_mix_video_template_fold_visible_via_build(monkeypatch, template_dir):
    """We can't run real ffmpeg here, but we can intercept _build_mix_request
    to confirm the template was folded into the payload.
    """
    write_template(
        template_dir,
        "warm_calm",
        {
            "extends": "base",
            "transition": {"style": "calm"},
            "color": {"look": "warm"},
            "encode": {"preset": "social_16x9"},
        },
    )

    from app.api import mix_video as mv

    captured: dict = {}

    real_resolve = mv._resolve_template

    def spy(body):
        out = real_resolve(body)
        captured["folded_body"] = out
        # Returning the resolved body is enough — the test asserts on it
        # without needing the downstream pipeline to actually run.
        return out

    monkeypatch.setattr(mv, "_resolve_template", spy)

    payload = {
        "project_id": 99,
        "clips": [{"path": "/nonexistent.mp4"}],
        "template": "warm_calm",
        # user explicitly overrides one template field
        "transition_style": "editorial",
    }
    # We don't care if it 4xx/5xx — only that our spy ran. probe will
    # raise on the fake path; the lenient client absorbs the 500.
    client_lenient.post("/api/v1/mix-video/preview", json=payload)

    folded = captured.get("folded_body")
    assert folded is not None, "_resolve_template was not called"
    assert folded.color_look == "warm"  # from template
    assert folded.preset == "social_16x9"  # from template (chained via extends)
    assert folded.transition_style == "editorial"  # user overrode template
