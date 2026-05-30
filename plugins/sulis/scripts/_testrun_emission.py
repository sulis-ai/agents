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
) -> dict:
    if in_run and not _COMPONENT_REF_RE.match(in_run):
        raise ValueError(f"in_run must be a valid dna:component:<ulid>; got {in_run!r}")
    timestamp = ran_at or datetime.now(timezone.utc).isoformat()
    run: dict = {
        "id": "dna:testrun:" + _ulid(f"testrun:{timestamp}:{in_run}:{harness}"),
        "ran_at": timestamp,
        "sys_status": "active",
    }
    if in_run:
        run["in_run"] = in_run
    if harness:
        run["harness"] = harness
    return run


def emit_testrun(
    *,
    repo: EntityRepository,
    ran_at: str | None = None,
    in_run: str = "",
    harness: str = "",
) -> dict:
    run = compose_testrun(ran_at=ran_at, in_run=in_run, harness=harness)
    repo.save("testrun", run)
    return run
