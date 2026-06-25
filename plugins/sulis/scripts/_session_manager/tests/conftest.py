"""Per-directory conftest for the in-package ``_session_manager`` tests
(CH-G3Y4RM WP-002).

The WP names its verification artifacts under
``plugins/sulis/scripts/_session_manager/tests/`` — a NEW test directory inside
the package (distinct from the repo-wide ``scripts/tests/`` suite). For the
``from _session_manager...`` imports to resolve when pytest is rooted anywhere
at or above ``scripts/``, the ``scripts/`` directory must be on ``sys.path``
(it is the parent of the ``_session_manager`` package). Mirrors the sys.path
insertion the repo-wide ``scripts/tests/conftest.py`` already does for
``_wpxlib``.

Also points ``HOME`` at a per-test tmp dir for any test that exercises the
DEFAULT chat-store root (``~/.sulis/chat/...``), so the founder's real home is
never touched — the same isolation posture the repo-wide conftest applies for
``SULIS_STATE_DIR``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
# tests/ -> _session_manager/ -> scripts/  (the package parent goes on the path)
_SCRIPTS_DIR = _HERE.parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path_factory, monkeypatch):
    """Point HOME at a per-test tmp dir so a test that reads the DEFAULT chat
    store root (``Path.home()/.sulis/chat/...``) never touches the real home.
    Tests that pass an explicit ``root`` are unaffected; this is the belt for
    the convention-path case."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
