"""TestRun event entity (PD).

CLI-direct event emission. Typical caller: a CI step at the moment of a
test-run start (or completion — TestRun is the *event* of running, not the
result). Required: ran_at. Optional: in_run (a dna:component:<ulid> for
the component that was the SUT), harness (pytest, vitest, jest, …).

Determinism: ULID from `f"testrun:{ran_at}:{in_run}:{harness}"`.
Re-emitting the same run is idempotent.

Note: the schema admits `ran_at` as the only required event field besides
id + sys_status, so a bare run record (no in_run, no harness) is valid —
useful for early bootstrapping before the Component graph is populated.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_COMPONENT_REF_RE: Final = re.compile(
    r"^dna:component:[0-9A-HJKMNP-TV-Z]{26}$"
)
_SCENARIO_REF_RE: Final = re.compile(
    r"^dna:scenario:[0-9A-HJKMNP-TV-Z]{26}$"
)


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_testrun(
    *,
    ran_at: str | None = None,
    in_run: str = "",
    harness: str = "",
    of_scenario: str = "",
) -> dict:
    if in_run and not _COMPONENT_REF_RE.match(in_run):
        raise ValueError(f"in_run must be a valid dna:component:<ulid>; got {in_run!r}")
    if of_scenario and not _SCENARIO_REF_RE.match(of_scenario):
        raise ValueError(f"of_scenario must be a valid dna:scenario:<ulid>; got {of_scenario!r}")
    timestamp = ran_at or datetime.now(timezone.utc).isoformat()
    # A scenario run is keyed on the scenario, NOT the timestamp: re-running
    # the same scenario must OVERWRITE its single run record (ran_at refreshes,
    # id is stable) so a regressed scenario can't leave a stale-pass record for
    # the requirement-coverage gate to find. A generic test event (no scenario)
    # keeps its event-seeded id (one record per run instant).
    seed = f"testrun:scenario:{of_scenario}" if of_scenario \
        else f"testrun:{timestamp}:{in_run}:{harness}"
    run: dict = {
        "id": "dna:testrun:" + _ulid(seed),
        "ran_at": timestamp,
        "sys_status": "active",
    }
    if in_run:
        run["in_run"] = in_run
    if harness:
        run["harness"] = harness
    if of_scenario:
        run["of_scenario"] = of_scenario
    return run


def emit_testrun(
    *,
    repo: EntityRepository,
    ran_at: str | None = None,
    in_run: str = "",
    harness: str = "",
    of_scenario: str = "",
) -> dict:
    run = compose_testrun(ran_at=ran_at, in_run=in_run, harness=harness, of_scenario=of_scenario)
    repo.save("testrun", run)
    return run
