"""TestResult entity (PD).

CLI-direct emission. Pairs with TestRun (the event) — TestResult is the
*verifying result* one TestRun produced for one or more Requirements.

Required: of_run (dna:testrun ref), verifies (≥1 dna:requirement refs),
type (unit/integration/e2e/contract/security), outcome (pass/fail/skip).
Optional: evidence (URI to artifact; marked sensitive in schema —
typically a CI artifact URL, log file, or coverage report).

Determinism: ULID from `f"testresult:{of_run}:{verifies}:{type}"`. Same
(testrun, requirement-set, type) combination always resolves to the same
ID — re-emitting outcomes is idempotent within one run.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TESTRUN_RE: Final = re.compile(r"^dna:testrun:[0-9A-HJKMNP-TV-Z]{26}$")
_REQ_RE: Final = re.compile(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$")
_SCENARIO_RE: Final = re.compile(r"^dna:scenario:[0-9A-HJKMNP-TV-Z]{26}$")
_VALID_TYPES: Final[set[str]] = {"unit", "integration", "e2e", "contract", "security"}
_VALID_OUTCOMES: Final[set[str]] = {"pass", "fail", "skip"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_testresult(
    *,
    of_run: str,
    verifies: list[str],
    type: str,
    outcome: str,
    evidence: str = "",
    scenario: str = "",
) -> dict:
    if not _TESTRUN_RE.match(of_run):
        raise ValueError(f"of_run must be a valid dna:testrun:<ulid>; got {of_run!r}")
    if type not in _VALID_TYPES:
        raise ValueError(f"testresult type must be one of {sorted(_VALID_TYPES)}; got {type!r}")
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"testresult outcome must be one of {sorted(_VALID_OUTCOMES)}; got {outcome!r}")
    if not isinstance(verifies, list) or not verifies:
        raise ValueError("testresult verifies must be a non-empty list of dna:requirement:<ulid>")
    bad = [v for v in verifies if not isinstance(v, str) or not _REQ_RE.match(v)]
    if bad:
        raise ValueError(f"testresult verifies entries must match dna:requirement:<ulid>; got {bad!r}")
    if scenario and not _SCENARIO_RE.match(scenario):
        raise ValueError(f"scenario must be a valid dna:scenario:<ulid>; got {scenario!r}")

    res: dict = {
        "id": "dna:testresult:" + _ulid(f"testresult:{of_run}:{','.join(sorted(verifies))}:{type}"),
        "of_run": of_run,
        "verifies": list(verifies),
        "type": type,
        "outcome": outcome,
        "sys_status": "active",
    }
    if evidence:
        res["evidence"] = evidence
    if scenario:
        res["scenario"] = scenario
    return res


def emit_testresult(
    *,
    repo: EntityRepository,
    of_run: str,
    verifies: list[str],
    type: str,
    outcome: str,
    evidence: str = "",
    scenario: str = "",
) -> dict:
    res = compose_testresult(
        of_run=of_run, verifies=verifies, type=type,
        outcome=outcome, evidence=evidence, scenario=scenario,
    )
    repo.save("testresult", res)
    return res
