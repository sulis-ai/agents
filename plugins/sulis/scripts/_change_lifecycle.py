"""The canonical change-lifecycle Workflow (#129 B1).

Every change runs the same six-stage journey — recon → specify → design →
implement → review → ship — and in practice a *session* is the executor that
walks a change through it. This defines that Workflow ONCE: the singleton id,
the six Steps, the forward transitions. The authoring tool, the emit-time link
(B2), the per-stage LifecycleRuns (B2), and any reader all agree on this one
definition.

Each stage's `mechanism` is `mixed` (human + agent) — the session is exactly the
mixed-mechanism executor the Step model anticipates. Ids are deterministic
(seeded), so authoring is idempotent and the id is a stable constant the
emitter can reference.
"""

from __future__ import annotations

import hashlib

from _entity_repository import EntityRepository

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
TENANT = "dna:tenant:7Q5TE6ZK6XMDM63BHNKXCJ46FY"


def _deterministic_ulid(seed: str) -> str:
    """A stable Crockford-base32 ULID from a seed (mirrors _opportunity_emission)."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(digest[:17], "big") & ((1 << 130) - 1)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


WORKFLOW_ID = "dna:workflow:" + _deterministic_ulid("workflow:change-lifecycle")

# (stage, input_artifacts, output_artifacts)
_STAGES = [
    ("recon", ["change-intent"], ["CONTEXT.md", "RECON.md"]),
    ("specify", ["CONTEXT.md"], ["SPEC.md"]),
    ("design", ["SPEC.md"], ["work-packages", "TDD.md"]),
    ("implement", ["work-packages"], ["code", "tests"]),
    ("review", ["code", "tests"], ["review-verdict"]),
    ("ship", ["review-verdict"], ["merge-to-main"]),
]
STAGES = [s[0] for s in _STAGES]


def step_id(stage: str) -> str:
    return "dna:step:" + _deterministic_ulid("step:change-lifecycle:" + stage)


def workflow_instance() -> dict:
    """The change-lifecycle Workflow entity (forward edges only — #96 adds the
    bounded reverse/spiral-back edges later)."""
    return {
        "id": WORKFLOW_ID,
        "name": "change-lifecycle",
        "for_domain": TENANT,
        "for_process": "change-lifecycle",
        "type": "delivery",
        "description": ("The six-stage journey every change runs, executed by its "
                        "session: recon → specify → design → implement → review → ship."),
        "steps": list(STAGES),
        "initial_steps": ["recon"],
        "terminal_steps": ["ship"],
        "transitions": [f"{a} -> {b}" for a, b in zip(STAGES, STAGES[1:])],
        "state": "active",
        "sys_status": "active",
    }


def step_instances() -> list:
    """The six Step entities — each `mixed` (the session is the human+agent executor)."""
    return [
        {
            "id": step_id(stage),
            "name": stage,
            "for_domain": TENANT,
            "for_process": "change-lifecycle",
            "input_artifacts": list(ins),
            "output_artifacts": list(outs),
            "mechanism": "mixed",
            "state": "active",
            "sys_status": "active",
        }
        for stage, ins, outs in _STAGES
    ]


def author(repo: EntityRepository) -> dict:
    """Persist the Workflow + its Steps through a foundation-domain repo.
    Idempotent — deterministic ids overwrite in place. Returns what was written."""
    wf = workflow_instance()
    repo.save("workflow", wf)
    steps = step_instances()
    for s in steps:
        repo.save("step", s)
    return {"workflow": wf, "steps": steps}
