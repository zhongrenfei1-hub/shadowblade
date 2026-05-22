"""Template-test fixtures — isolated templates directory per test.

Each test gets a temp dir wired into ``SHADOWBLADE_TEMPLATES_DIR`` so
templates land at the front of the search path. We also force a full
rescan (LRU cache + hot-reload state) before and after each test so
the throttle doesn't bleed timing between tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.template.loader import _force_rescan_for_tests


@pytest.fixture
def template_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SHADOWBLADE_TEMPLATES_DIR", str(tmp_path))
    _force_rescan_for_tests()
    yield tmp_path
    _force_rescan_for_tests()


def write_template(template_dir: Path, name: str, body: dict) -> Path:
    p = template_dir / f"{name}.json"
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return p
