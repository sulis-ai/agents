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

import pytest

from _brain_location import brain_base_dir
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
# Provenance records (LifecycleRuns) are no longer committed in-repo — they live
# in the user-level central brain (de-branch-scope-the-brain / dogfood-central).
# The repo's durable footprint is the ULID *pointer* in the committed contract;
# the record itself resolves under the central captures root, which a fresh
# checkout / CI / the test-isolated state dir will not contain.
_LIFECYCLERUN_DIR = brain_base_dir(_REPO_ROOT) / "product-development" / "lifecyclerun"


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
    """The harness run that produced the contract has durable provenance: the
    committed contract carries a ULID *pointer* to a persisted LifecycleRun
    (A-8). Post de-branch-scope, the record itself lives in the user-level
    central brain, not committed in-repo — so its physical presence is verified
    only when that brain is reachable (a fresh checkout / CI / the test-isolated
    state dir will not contain it; the durable repo footprint is the pointer)."""
    text = _CONTRACT.read_text(encoding="utf-8")
    import re

    m = re.search(r"harness-run:\s*([0-9A-HJKMNP-TV-Z]{26})", text)
    assert m, "Contract must carry a ULID-shaped harness-run reference."
    run_id = m.group(1)
    run_file = _LIFECYCLERUN_DIR / f"{run_id}.jsonld"
    if not run_file.is_file():
        pytest.skip(
            f"LifecycleRun {run_id} lives in the user-level central brain "
            f"({run_file}); not present in this environment. The durable "
            "in-repo footprint is the ULID pointer asserted above."
        )
