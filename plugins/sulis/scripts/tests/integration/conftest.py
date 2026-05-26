"""Per-directory conftest for integration tests.

Adds the integration test directory to sys.path so individual test modules
can `from testbed import train_testbed` directly (the TrainTestbed fixture
lives in testbed.py per HD-002).

Re-exports the `train_testbed` fixture from testbed.py so pytest's
fixture discovery finds it without each test module needing to import it
explicitly. (Tests that want to inspect helpers from testbed.py can still
`from testbed import FakeGHClient, TrainTestbed` as a normal import.)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Re-export the fixture so pytest discovers it without per-test imports.
from testbed import train_testbed  # noqa: E402, F401


@pytest.fixture(autouse=True)
def _isolate_sulis_state(tmp_path_factory, monkeypatch):
    """Point SULIS_STATE_DIR at a per-test tmp dir for every integration test.

    Integration tests invoke `sulis-change start` (and list/nuke) via real
    subprocesses, which inherit the parent's environment. Without this, those
    subprocesses write the REAL ~/.sulis/changes/* — polluting the developer's
    (and CI runner's) home, and junking the dashboard's global view. Setting
    the env var here makes _change_state.sulis_state_base() resolve to the tmp
    dir; run_tool's `env=os.environ.copy()` propagates it to the subprocess.
    """
    state_dir = tmp_path_factory.mktemp("sulis-state")
    monkeypatch.setenv("SULIS_STATE_DIR", str(state_dir))
