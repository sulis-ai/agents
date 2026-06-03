"""LifecycleRun entity (PD).

A LifecycleRun records one execution of a lifecycle Step (e.g.
`/sulis:run-all` Step 7-complete, `/sulis:release-train` step) — a
`prov:Activity` that instantiates a `prov:Plan` (the Step it ran). Event-shaped
— CLI-direct emission from the lifecycle skill at the moment of completion.

Under v2 (the re-vendored canonical schema, ADR-001/ADR-004) the run carries a
required `step` ref — a `dna:step:<ulid>` pointing at the Step definition it
instantiated (via `sulis:viaStep`) — NOT a free `step_name` string. The per-run
specificity that used to be smuggled into the `step_name` string is carried by
the canonical `run_id` field (a workflow-run trace identifier).

The `by_actor` field optionally records who/what ran the step (a service
account, a CI runner, an LLM session).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Final

from _entity_repository import EntityRepository


_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ACTOR_ID_RE: Final = re.compile(r"^dna:actor:[0-9A-HJKMNP-TV-Z]{26}$")
_STEP_ID_RE: Final = re.compile(r"^dna:step:[0-9A-HJKMNP-TV-Z]{26}$")
_VALID_OUTCOMES: Final[set[str]] = {"completed", "failed", "in-progress", "cancelled"}


def _ulid(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def compose_lifecyclerun(
    *,
    step: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
    run_id: str | None = None,
) -> dict:
    """Compose a v2 LifecycleRun payload.

    Args:
        step: a resolved `dna:step:<ulid>` ref — the Step (prov:Plan) this run
            instantiated. Required; rejected if not a valid Step ref.
        outcome: one of completed / failed / in-progress / cancelled.
        at: ISO timestamp; defaults to now (UTC).
        by_actor: optional `dna:actor:<ulid>`.
        run_id: optional workflow-run trace identifier. Carries the per-run
            specificity (e.g. `{primitive}:{slug}`) that the legacy `step_name`
            string used to hold. Emitted only when provided, so the
            `unevaluatedProperties: false` schema stays clean.
    """
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"lifecyclerun outcome must be one of {sorted(_VALID_OUTCOMES)}; got {outcome!r}")
    if not step or not step.strip():
        raise ValueError("lifecyclerun step may not be empty")
    if not _STEP_ID_RE.match(step):
        raise ValueError(f"lifecyclerun step must be a valid dna:step:<ulid> ref; got {step!r}")
    if by_actor and not _ACTOR_ID_RE.match(by_actor):
        raise ValueError(f"by_actor must be a valid dna:actor:<ulid>; got {by_actor!r}")

    timestamp = at or datetime.now(timezone.utc).isoformat()
    run: dict = {
        "id": "dna:lifecyclerun:" + _ulid(f"lcrun:{step}:{timestamp}:{by_actor}"),
        "step": step,
        "at": timestamp,
        "outcome": outcome,
        "sys_status": "active",
    }
    if by_actor:
        run["by_actor"] = by_actor
    if run_id:
        run["run_id"] = run_id
    return run


def emit_lifecyclerun(
    *,
    repo: EntityRepository,
    step: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
    run_id: str | None = None,
) -> dict:
    run = compose_lifecyclerun(
        step=step, outcome=outcome, at=at, by_actor=by_actor, run_id=run_id
    )
    repo.save("lifecyclerun", run)
    return run
