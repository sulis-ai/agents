"""Unit tests for the #118 ship-time observed-verdict gate.

The root cause this closes: the Definition-of-Done verdict (every touched
Requirement has a passing TestResult) was enforced ONLY as prose in
`change/SKILL.md` gate 4.9 — the `sulis-change` ship script ran it zero times.
So a change could be marked *shipped* without an observed verdict, by an agent
skipping the prose step or a hand-merge bypassing the skill entirely. This gate
moves the check from prose into the ship mechanism: `mark-shipped` refuses
unless every touched SRD's DoD verdict is `pass` — escapable only by a
conscious, logged `--force` (mirrors the #111 ship-integrity guard).

`evaluate_observed_verdict` is the PURE decision (touched SRDs + a verdict
function → ok/blocked); the script wires git-diff + `verify_requirements` into
it. The decision is the load-bearing, fixture-able part — tested here.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_sulis_change()
evaluate_observed_verdict = _mod.evaluate_observed_verdict


# ─── no SRD touched → out of scope, never blocks ───────────────────────────


def test_no_srd_touched_is_ok():
    ok, reason = evaluate_observed_verdict([], verify_fn=lambda srd: "pass")
    assert ok is True
    assert "no srd" in reason.lower() or "not applicable" in reason.lower()


# ─── all touched SRDs PASS → observed, ship proceeds ───────────────────────


def test_all_srds_pass_is_ok():
    srds = [".specifications/payments/SRD.md", ".specifications/auth/SRD.md"]
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: "pass")
    assert ok is True


# ─── any touched SRD not-PASS → BLOCKED (observed-or-blocked) ──────────────


def test_a_failing_srd_blocks():
    srds = [".specifications/payments/SRD.md"]
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: "fail")
    assert ok is False
    assert "payments" in reason
    assert "fail" in reason.lower()


def test_a_partial_srd_blocks():
    # partial = some FRs unverified — an unobserved requirement is blocked, not
    # a quiet pass. The conscious escape is --force at the call site.
    srds = [".specifications/auth/SRD.md"]
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: "partial")
    assert ok is False
    assert "auth" in reason


def test_one_pass_one_fail_blocks_and_names_the_failing_one():
    srds = [".specifications/ok/SRD.md", ".specifications/bad/SRD.md"]
    verdicts = {".specifications/ok/SRD.md": "pass",
                ".specifications/bad/SRD.md": "fail"}
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: verdicts[srd])
    assert ok is False
    assert "bad" in reason
    assert "ok/SRD.md" not in reason  # only the unverified one is named
