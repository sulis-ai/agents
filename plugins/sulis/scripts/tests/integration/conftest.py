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

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Re-export the fixture so pytest discovers it without per-test imports.
from testbed import train_testbed  # noqa: E402, F401

# NOTE: SULIS_STATE_DIR isolation now lives in the root conftest
# (tests/conftest.py) as a repo-wide autouse fixture, so it covers unit tests
# too. It is intentionally not duplicated here.
