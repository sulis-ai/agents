"""Unit tests for the interaction-flow done-gate (CH-01KT9H, ADR-001).

Sibling of `test_visual_contract_gate.py`. The interaction gate blocks a
`kind: contract` / `contract_type: interaction` WP from reaching `done` until
its multi-step flow has been exercised end-to-end over stub adapters — evidenced
either `agent-observed` or `human-attested`.

Two pure predicates on a frontmatter dict:

- `is_interaction_contract_wp(fm)` — recognition (mirrors
  `is_visual_contract_wp`).
- `interaction_flow_exercised(fm)` → `None`/error — the runtime done-gate
  predicate (mirrors `visual_contract_signed_off`). Passes iff `exercised_at`
  is non-empty, `exercised_by` ∈ {agent-observed, human-attested}
  (case-insensitive), and `exercised_attestation` is non-empty (ADR-001).
"""

from __future__ import annotations

from _wpxlib import (
    interaction_flow_exercised,
    is_interaction_contract_wp,
)


# ─── is_interaction_contract_wp (recognition) ───────────────────────────────


def test_is_interaction_contract_wp_true_for_contract_interaction():
    assert is_interaction_contract_wp(
        {"kind": "contract", "contract_type": "interaction"}
    )


def test_is_interaction_contract_wp_false_for_visual_contract():
    assert not is_interaction_contract_wp(
        {"kind": "contract", "contract_type": "visual"}
    )


def test_is_interaction_contract_wp_false_for_frontend():
    assert not is_interaction_contract_wp({"kind": "frontend"})


def test_is_interaction_contract_wp_false_for_backend():
    assert not is_interaction_contract_wp({"kind": "backend"})


def test_is_interaction_contract_wp_is_case_insensitive():
    assert is_interaction_contract_wp(
        {"kind": "Contract", "contract_type": "Interaction"}
    )


# ─── interaction_flow_exercised (the runtime done-gate predicate) ───────────


def _exercised(**overrides) -> dict:
    base = {
        "kind": "contract",
        "contract_type": "interaction",
        "exercised_at": "2026-06-04T15:40:00Z",
        "exercised_by": "agent-observed",
        "exercised_attestation": (
            "stub run transcript at contracts/interaction/clinics-scheme.run.txt"
        ),
    }
    base.update(overrides)
    return base


# pass paths


def test_agent_observed_full_evidence_passes():
    assert interaction_flow_exercised(_exercised()) is None


def test_human_attested_full_evidence_passes():
    assert (
        interaction_flow_exercised(
            _exercised(
                exercised_by="human-attested",
                exercised_attestation="Iain ran the clinics flow 2026-06-04",
            )
        )
        is None
    )


def test_exercised_by_is_case_insensitive():
    assert interaction_flow_exercised(_exercised(exercised_by="Agent-Observed")) is None
    assert interaction_flow_exercised(_exercised(exercised_by="HUMAN-ATTESTED")) is None


# reject paths


def test_no_evidence_is_rejected():
    msg = interaction_flow_exercised(
        {"kind": "contract", "contract_type": "interaction"}
    )
    assert msg is not None
    assert "exercised_at" in msg


def test_empty_exercised_at_is_rejected():
    msg = interaction_flow_exercised(_exercised(exercised_at=""))
    assert msg is not None
    assert "exercised_at" in msg


def test_blank_exercised_by_is_rejected():
    msg = interaction_flow_exercised(_exercised(exercised_by="   "))
    assert msg is not None
    assert "exercised_by" in msg


def test_unknown_exercised_by_token_is_rejected():
    msg = interaction_flow_exercised(_exercised(exercised_by="self-certified"))
    assert msg is not None
    # the message names the two valid sources
    assert "agent-observed" in msg
    assert "human-attested" in msg


def test_missing_exercised_attestation_is_rejected():
    msg = interaction_flow_exercised(_exercised(exercised_attestation=""))
    assert msg is not None
    assert "exercised_attestation" in msg


def test_bare_timestamp_alone_does_not_pass():
    # A bare exercised_at with no source and no attestation must NOT satisfy the
    # gate — the whole point of ADR-001's three-field rule.
    msg = interaction_flow_exercised(
        {
            "kind": "contract",
            "contract_type": "interaction",
            "exercised_at": "2026-06-04T15:40:00Z",
        }
    )
    assert msg is not None
