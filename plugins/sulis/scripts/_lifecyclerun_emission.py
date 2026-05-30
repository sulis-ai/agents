"""LifecycleRun entity (PD).

A LifecycleRun records one execution of a named lifecycle step (e.g.
`/sulis:run-all` Step 7-complete, `/sulis:release-train` step). Event-shaped
— CLI-direct emission from the lifecycle skill at the moment of completion.

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
    step_name: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
) -> dict:
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"lifecyclerun outcome must be one of {sorted(_VALID_OUTCOMES)}; got {outcome!r}")
    if not step_name or not step_name.strip():
        raise ValueError("lifecyclerun step_name may not be empty")
    if by_actor and not _ACTOR_ID_RE.match(by_actor):
        raise ValueError(f"by_actor must be a valid dna:actor:<ulid>; got {by_actor!r}")

    timestamp = at or datetime.now(timezone.utc).isoformat()
    run: dict = {
        "id": "dna:lifecyclerun:" + _ulid(f"lcrun:{step_name}:{timestamp}:{by_actor}"),
        "step_name": step_name.strip(),
        "at": timestamp,
        "outcome": outcome,
        "sys_status": "active",
    }
    if by_actor:
        run["by_actor"] = by_actor
    return run


def emit_lifecyclerun(
    *,
    repo: EntityRepository,
    step_name: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
) -> dict:
    run = compose_lifecyclerun(step_name=step_name, outcome=outcome, at=at, by_actor=by_actor)
    repo.save("lifecyclerun", run)
    return run
