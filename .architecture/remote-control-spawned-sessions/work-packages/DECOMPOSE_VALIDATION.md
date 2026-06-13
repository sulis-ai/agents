# Decompose Validation — remote-control-spawned-sessions (CH-HK5D5M)

## At a glance

The work splits into **one** Work Package. Every required structural section is
present, the WP is atomic (one file modified, one test file added), there is no
dependency graph to cycle, no peer-collision surface, and the verification design
is concrete and test-first. **Verdict: PASS.**

---

## Verdict

**PASS** — every MUST passes; no SHOULD failures.

(Phase 9 P-VER is PASS-WITH-RATIONALE on the SRD/TDD-scoped sub-checks because
this is an engineering-architect-light change with no TDD by design — identical
treatment to the `harden-plan-work-listready-gate` precedent. The directly-
checkable WP-level gate, 9.08, PASSes. This does not lower the overall verdict
below PASS because the SRD/TDD checks are *scoped out with rationale*, not
*failed*.)

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 1 |
| Total checks applied | 29 (phases with applicable checks) |
| PASS | 28 |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 0 |
| Scoped-out with rationale | 3 (9.01 / 9.06 / 9.07 — no TDD by design) |

---

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | ✓ | — | All required sections present in WP-001; INDEX lists it; Dependency Graph section present. |
| 2 Atomicity | ✓ | — | One file modified + one test file; title has no "and"; ≤8 files; single primitive. |
| 3 Module naming + clean code | ✓ | — | `WP-001-remote-control-default-on-pty-spawn.md`; kebab, outcome-named, no jargon. |
| 4 Dependency graph correctness | ✓ | — | Single node, `dependsOn: []`; no cycles, no orphan rule violation (foundation WP), order trivially valid. |
| 5 Performance + non-functional | ✓ | — | Not a request-handler/endpoint/external-API primitive; no SLA required. N/A. |
| 6 Peer-collision risk | ✓ | — | Single WP — no peer to collide with. No shared fixture (`fixtures_created: []`). |
| 7 ServiceSpec compliance | ✓ | — | No service introduced/modified; no manifest required. N/A. |
| 8 Cross-WP identifier canonicalisation | ✓ | — | No identifier shared across ≥2 WPs (only one WP). The one ULID-shaped value (`change_id`) is sourced from `.changes/…yaml`, not invented inline. |
| 9 P-VER (Verification Plan) | ✓* | — | 9.08 PASS (concrete WP `verification:`); 9.02–9.05 PASS against the SPEC's plan; 9.01/9.06/9.07 scoped-out (no TDD by design). PASS-WITH-RATIONALE. |
| 10 P-PLAT (Platform Contract) | ✓ | — | `touch-class: read-only` (launch the Claude CLI; no write/deploy). P-PLAT 10.01 does not fire. |

---

## Blocking gaps (MUST failures)

None.

---

## Recommended improvements (SHOULD failures)

None.

---

## Detailed findings per check

### Phase 1 — Inventory completeness (PASS)

- **1.01–1.05** PASS — WP-001 has `## Context`, `## Contract`, `## Definition of
  Done` (Red/Green/Blue), `## Sequence` (`Sequence ID: WP-001`), and
  `## Estimated Token Cost` (numeric `input: ~14k / output: ~6k`).
- **1.06** PASS — `dependsOn: []` in frontmatter (foundation WP).
- **1.07** PASS — INDEX.md lists WP-001; the directory contains exactly one
  `WP-*.md` file. Set equality holds (confirmed by `wpx-index lint`:
  `accounted: 1`, `round_trip: ok`).
- **1.08** PASS — INDEX.md has a `## Dependency Graph` section.
- **1.09** SHOULD PASS — `primitive: expand-create` is in the 22-primitive
  catalogue (EXPAND group, Create).
- **1.10** SHOULD PASS — Contract references the design source (the SPEC's
  Scope/Acceptance) and the §2.4 contract seam; no TDD section to cite by design.

### Phase 2 — Atomicity (PASS)

- **2.01 / 2.06** PASS — purpose is one sentence, no conjunction; title carries
  no " and ".
- **2.02 / 2.03** PASS — Contract modifies **1** source file
  (`claude_pty.py`) and creates **1** test file. ≤8.
- **2.04** SHOULD PASS — estimated output ~6k ≤ 10k.
- **2.05** SHOULD PASS — single `primitive:` value.

### Phase 3 — Module naming + clean code (PASS)

- **3.01 / 3.02 / 3.03** PASS — `WP-001-remote-control-default-on-pty-spawn.md`:
  kebab-case, descriptive outcome slug, no single/double-letter abbreviations
  (`pty` is a widely-understood term). `6` words ≤ 6 (3.06 PASS).
- **3.04 / 3.05 / 3.07** SHOULD PASS — module/constant names in the Contract
  (`_REMOTE_CONTROL_FLAG`, `_remote_control_enabled`) are full words mirroring the
  established `_os_window_enabled` convention; no `mgr`/`svc`/`utils`; no internal
  jargon prefix.

### Phase 4 — Dependency graph correctness (PASS)

- **4.01 / 4.02** PASS — single node, `dependsOn: []` → no cycles, all (zero)
  targets resolve.
- **4.03 / 4.04** SHOULD PASS — 0 dependencies; depth 1.
- **4.05** SHOULD PASS — orphan rule: WP-001 is the sole, foundation WP — its
  isolation is expected, not a defect.
- **4.07** PASS — the single-element order is a trivially valid topological sort.
- **4.08 / 4.09** PASS (N/A) — single-kind set (`backend` only); no cross-kind
  seam, so no data-contract WP required and no cross-kind edge to route.

### Phase 5 — Performance + non-functional (PASS / N/A)

- **5.01–5.06** N/A — `expand-create` on a pure argv builder is not
  `add-endpoint`/`add-handler`/`add-route`/`add-integration`/`add-schema`. No
  request path, no external API call introduced (the CLI is launched, not called
  over the network from this code), no DB/table. No performance section required.

### Phase 6 — Peer-collision risk (PASS)

- **6.01 / 6.02** PASS — one WP; no peer to create or modify the same file. The
  new test module `test_pty_remote_control.py` does not pre-exist (verified) — no
  create collision even against the existing suite.
- **6.03 / 6.04** SHOULD PASS — no shared scaffolding; Contract distinguishes
  `Files modified` from `Files created`.
- **6.06 / 6.07** PASS (N/A) — no shared logical artifact and no shared test
  fixture (`fixtures_created: []`); nothing for a second WP to co-author.

### Phase 7 — ServiceSpec compliance (PASS / N/A)

- **7.01–7.14** N/A — the change introduces/modifies no service; the TDD step-10
  ServiceSpec gate has no service inventory to pair against. No
  `service-specs/` directory required.

### Phase 8 — Cross-WP identifier canonicalisation (PASS)

- **8.01–8.03** PASS — no identifier appears in ≥2 WP Contracts (only one WP).
  The single ULID-shaped value referenced (`change_id:
  01KV0JP9J1HK5D5M27KZZGZAEK`) is the parent change's own ULID, sourced
  authoritatively from `.changes/feat-remote-control-spawned-sessions.yaml`, not
  invented inline (8.02 satisfied).
- **8.04 / 8.05** SHOULD PASS — single-WP-scoped; the change-ULID's source is the
  change record itself.

### Phase 9 — P-VER (Verification Plan) (PASS-WITH-RATIONALE)

**Grandfather sub-phase.** `verification_required_from` is empty (pre-merge
dogfood state) → P-VER applies. `started_at: 2026-06-13T13:28:12Z` is parseable
and there is no later merge-date constant → **not grandfathered**.

- **9.08** PASS (the directly-checkable WP-level gate) — WP-001's frontmatter
  carries `verification:` as a **Shape 1 (concrete)** field: `adapter: backend`
  (matches the change `kind: backend`) + `artifact:` pinning the pytest module
  `plugins/sulis/scripts/tests/unit/test_pty_remote_control.py`.
- **9.05** PASS — `kind: backend` has an adapter row in the canonical
  `VERIFICATION_QUESTIONS.md` kind→adapter table.
- **9.02 / 9.03 / 9.04** PASS against the SPEC's `## Verification Plan` — no
  placeholder content (the foundational-checks matrix is concrete: default-on /
  opt-out / change-named / headless-guard); no bare `n/a`; the named `existing`
  infrastructure all resolves in-repo, verified during authoring:
  `claude_pty.py` `spawn_argv` (target), `validate_change_ulid` (imported at
  `claude_pty.py:73`), the `_OS_WINDOW_FLAG`/`_os_window_enabled` convention in
  `_terminal_launcher.py`, and the existing test patterns
  `tests/unit/test_pty_session.py` + `tests/unit/test_claude_adapter.py`.
- **9.01 / 9.06 / 9.07** scoped-out with rationale — these check the
  `## Verification Plan` section presence + the canonical citation + version
  currency in the **SRD and TDD**. This change is **engineering-architect-light
  by explicit brief**: no TDD is produced and no SRD exists; the design input is
  `.changes/feat-remote-control-spawned-sessions.SPEC.md`, which **does** carry a
  `## Verification Plan` (the foundational-checks matrix, the wiring check, the
  observable outcome, the observed-once manual check). The WP's own
  `## Verification Plan` carries the canonical citation annotation
  (`<!-- VERIFICATION_QUESTIONS source: …/VERIFICATION_QUESTIONS.md v1.0.0 -->`).
  The substantive intent of P-VER — *verification is designed up front, not
  bolted on* — is fully met: the SPEC's matrix IS the verification design, and
  the WP's Red step encodes all four variants test-first with a concrete
  `verification:` artifact. **Rationale recorded; not a blocking gap for a light
  change.** Were this a full greenfield TDD flow, 9.01/9.06/9.07 would be hard
  MUSTs against the TDD. (Same disposition as the `harden-plan-work-listready-gate`
  precedent.)

### Phase 10 — P-PLAT (Platform Contract) (PASS)

**Grandfather sub-phase.** `platform_contract_required_from` empty → P-PLAT
applies; not grandfathered.

- **10.01** PASS — WP-001 declares `platform: claude-cli` with
  `touch-class: read-only`. The only platform interaction is launching the Claude
  CLI (read-only/launch); there is no write or deploy touch. P-PLAT's gate fires
  only on `touch-class: write|deploy`, so no Platform Contract is required
  (`read-only` is advisory per ADR-001).
- **10.02–10.07** N/A — no contract referenced because none is required.

---

## Methodology

- [✓] **P1 Inventory completeness.** 1 WP read end-to-end. Required sections
  found: Context, Contract, Definition of Done (Red/Green/Blue), Sequence
  (Sequence ID), Estimated Token Cost, dependencies (`dependsOn: []`). INDEX
  lists the WP (confirmed by `wpx-index lint`: accounted 1, round_trip ok);
  Dependency Graph section present. Gaps: none.
- [✓] **P2 Atomicity.** Purpose one sentence, no conjunction. Touch surface: 1
  source file modified + 1 test file created. Single primitive. 0 WPs exceed
  atomicity bounds.
- [✓] **P3 Module naming.** WP filename + Contract constant/helper names scanned;
  full words, mirror the existing `_os_window_enabled` convention. 0 jargon
  findings.
- [✓] **P4 Dependency graph.** DAG built from INDEX: 1 node, 0 edges. Cycles: 0.
  Orphans: 0 (foundation WP — expected). Order valid.
- [✓] **P5 Performance + non-functional.** No request-handler / endpoint /
  external-API / schema primitive present → no SLA required. 0 violations.
- [✓] **P6 Peer-collision risk.** Single WP → no create/modify peer collision.
  New test module verified non-existent (no create collision vs existing suite).
  Shared-fixture scan: `fixtures_created: []` → 0 logical-fixture collisions.
- [✓] **P7 ServiceSpec compliance.** No service introduced/modified; 0 manifests
  required → 0 MUST failures.
- [✓] **P8 Cross-WP identifier canonicalisation.** 0 identifiers shared across
  ≥2 WPs. The 1 ULID-shaped value (change_id) sourced authoritatively from the
  change record, not inline. 0 flagged.
- [✓] **P9 P-VER.** Grandfather: applies (constant empty), not grandfathered
  (started_at 2026-06-13 parseable). 9.08 PASS (concrete WP `verification:`,
  adapter matches kind). 9.02–9.05 PASS against the SPEC's Verification Plan.
  9.01/9.06/9.07 scoped-out with rationale (no TDD/SRD by design — light change;
  the SPEC carries the Verification Plan, the WP carries the canonical citation).
  Verdict: PASS-WITH-RATIONALE.
- [✓] **P10 P-PLAT.** Grandfather: applies, not grandfathered. 1 WP scanned for
  `platform:`/`touch-class:`: `claude-cli` / `read-only`. 0 gated write/deploy
  touches → no Platform Contract required (10.01 does not fire). Verdict: PASS.

No phases skipped.
