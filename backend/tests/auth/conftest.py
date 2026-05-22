"""Shared fixtures for the dedicated auth test suite.

Re-uses the per-test SQLite + dependency-override scaffolding from
``tests/organizations/conftest.py`` so a single test run can exercise both
the team-management surface and the dedicated login system without leaking
state between cases.

The helper functions (``register``, ``login``, etc.) are imported lazily
inside each test so a stale import in conftest doesn't poison the suite.
"""

from __future__ import annotations

# Re-export the relevant fixtures via inheritance — pytest discovers
# conftest.py files in a parent's tree, so we point at the organisations
# conftest for the heavy lifting.
from tests.organizations.conftest import (  # noqa: F401
    _reset_settings_cache,
    client,
    db_engine,
)
