"""Experiment entity (PD).

CLI-direct emission. Records a test of a hypothesis against a Metric —
the build-measure-learn unit. Required: hypothesis (free-text), success_metric
(dna:metric ref), result (supported / refuted / inconclusive). Optional:
tests (dna:opportunity or dna:requirement ref), ran (timestamp).

Determinism: ULID from `f"experiment:{hypothesis}:{success_metric}"`.
Two experiments with the same hypothesis against the same success metric
are the same experiment — a re-run updates the result in place.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_METRIC_RE: Final = re.compile(r"^dna:metric:[0-9A-HJKMNP-TV-Z]{26}$")
_TESTS_RE: Final = re.compile(
    r"^dna:(opportunity|requirement):[0-9A-HJKMNP-TV-Z]{26}$"
)
_VALID_RESULTS: Final[set[str]] = {"supported", "refuted", "inconclusive"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_experiment(
    *,
    hypothesis: str,
    success_metric: str,
    result: str,
    tests: str = "",
    ran: str | None = None,
) -> dict:
    if not hypothesis or not hypothesis.strip():
        raise ValueError("experiment hypothesis may not be empty")
    if not _METRIC_RE.match(success_metric):
        raise ValueError(f"success_metric must be a dna:metric:<ulid>; got {success_metric!r}")
    if result not in _VALID_RESULTS:
        raise ValueError(f"experiment result must be one of {sorted(_VALID_RESULTS)}; got {result!r}")
    if tests and not _TESTS_RE.match(tests):
        raise ValueError(f"experiment tests must be a dna:opportunity|requirement ref; got {tests!r}")

    exp: dict = {
        "id": "dna:experiment:" + _ulid(f"experiment:{hypothesis.strip()}:{success_metric}"),
        "hypothesis": hypothesis.strip(),
        "success_metric": success_metric,
        "result": result,
        "sys_status": "active",
    }
    if tests:
        exp["tests"] = tests
    if ran:
        exp["ran"] = ran
    return exp


def emit_experiment(
    *,
    repo: EntityRepository,
    hypothesis: str,
    success_metric: str,
    result: str,
    tests: str = "",
    ran: str | None = None,
) -> dict:
    exp = compose_experiment(
        hypothesis=hypothesis, success_metric=success_metric,
        result=result, tests=tests, ran=ran,
    )
    repo.save("experiment", exp)
    return exp
