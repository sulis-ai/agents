"""Harness-refusal verification for WP-007 (platform-contract-standard).

FR-006 / A-2 / MUC-006: the faithful-generation-harness must REFUSE to ground
a claim it cannot bind to a source — it flags the claim as an inference (no
fabricated citation) rather than inventing provenance.

The ideal form of this test dispatches the live ``/sulis-brain:execute-workflow``
harness against an ungrounded fixture manifest (MEA-09: no internal mocking)
and asserts a ``terminal-manifest-insufficient`` refusal. That cannot run
inside pytest — pytest cannot dispatch a Claude sub-agent — so the live-dispatch
integration check is **deferred** (`deferred:live-harness-refusal-integration`).

What we CAN assert mechanically, and do here, is the **observable output** of a
real refusal that already happened: the n=1 dogfood run
(``harness-run: 01KT419R8MQBQ6BNZPXDSKZBHZ``) refused to bind rule 3
(branch-protection) to a non-supporting quote and instead recorded it as an
inference with **no source**. That is the refusal discipline's footprint, and
it is exactly what a fabricated-citation regression would violate.

Stdlib + pyyaml + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

from _platform_contract import parse_contract_claims

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONTRACT = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "references"
    / "platform-contracts"
    / "github-actions.md"
)
_LIFECYCLERUN_DIR = (
    _REPO_ROOT / ".brain" / "instances" / "product-development" / "lifecyclerun"
)


def test_refusal_output_carries_no_fabricated_source() -> None:
    """The flagged inference in the dogfood contract carries NO source — the
    harness refused to fabricate one (A-4 / MUC-006)."""
    claims = parse_contract_claims(_CONTRACT)
    inferred = [c for c in claims if c.get("inferred") is True]
    assert inferred, (
        "Expected at least one flagged inference (the harness refusing to "
        "ground an unprovable claim) in the dogfood contract."
    )
    for claim in inferred:
        assert not claim.get("source"), (
            "A flagged inference must NOT carry a fabricated `source` — the "
            f"refusal discipline was violated: {claim.get('claim')!r}"
        )


def test_refusal_run_was_persisted() -> None:
    """The harness run that produced the contract persisted a LifecycleRun —
    the refusal verdict has durable provenance, not just prose (A-8)."""
    text = _CONTRACT.read_text(encoding="utf-8")
    import re

    m = re.search(r"harness-run:\s*([0-9A-HJKMNP-TV-Z]{26})", text)
    assert m, "Contract must carry a ULID-shaped harness-run reference."
    run_id = m.group(1)
    run_file = _LIFECYCLERUN_DIR / f"{run_id}.jsonld"
    assert run_file.is_file(), (
        f"Expected the LifecycleRun for harness-run {run_id} persisted at "
        f"{run_file} — provenance must be durable, not asserted."
    )
