# Code Review: feat/wp-010-onboarding-roundtrip — Journey G cold-start onboarding round-trip

> **Timestamp:** 2026-06-04T144855Z (ISO 8601 UTC)
> **Author:** WP-010 executor
> **Branch:** feat/wp-010-onboarding-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 19 (2704 insertions, 14 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the "set up your product just by talking" flow: when the app
opens on an empty graph, a conversation (not a form) walks the founder through
choosing an area, seeing a plain-English proposal, and — only after they say go —
creating a product and connecting (or making) its code repo. The build is clean,
the read-only safety gate still passes, and every new piece of code has matching
tests (6 new source files, 6 new test files). Nothing needs fixing before merge.

The one thing worth knowing: the setup conversation only ever *creates* anything
after an explicit confirm, and it can only ever look inside the folder the founder
chose — both are enforced and tested, including a path-escape attempt that is
correctly refused.

## What to fix

No issues that need attention.

## How this change is shaped

**Size — for awareness (no action needed)**

The change is large (2,704 lines) but that is by design: this is one vertical
"round-trip" slice, where the server route and the screen that drives it ship
together so the whole flow can be observed working. Splitting it would break that
guarantee. Six of the new files are tests, so roughly half the size is the safety
net.

**Scope — clean**

Everything lives under one app folder and one feature (the onboarding journey).
One concern, one slice.

**Safety — clean**

No database migrations, no schema changes, no infrastructure files, no secrets.
The only thing that can create or change anything (the product/repo) is gated
behind an explicit confirm and leaves nothing behind if it fails.

**Completeness — clean**

Every new source file has a matching test file (1:1).

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers
> and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
file >50 lines read end-to-end (the author wrote them); all three lenses produced
output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck clean, lint clean, read-only gate clean (141 files).
- **PR Hygiene:** 0 actionable findings. Size is large-by-design (vertical slice per the INDEX decomposition); not splittable without breaking the observable round-trip (PH-02 note, not a smell).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — ADR-006/007 honoured |
| Security | 0 | 0 | none — scope-bound + confirm-gated |
| Quality | 0 | 0 | none — 2 watch-list notes |

### Build Verification (CR-01)

Mechanical baseline on HEAD:
- `tsc --noEmit -p server && -p client` → 0 errors (`tool-outputs/typecheck-head.log`).
- `eslint --ext .ts,.tsx .` → 0 errors (`tool-outputs/lint-head.log`).
- `bash scripts/check-read-only.sh` → clean, 141 files (`tool-outputs/read-only-gate.log`).

The read-only gate is the load-bearing check here: WP-010 adds a SECOND act path
(`POST /api/onboarding/session`). It is registered inside `server/routes/chat.ts`
(the ONE sanctioned write-verb file) so the gate's allow-list stays `{chat.ts}` —
no new write exception (ADR-006). The orchestrator starts no process; the gate
confirms no new spawn site.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):     commit_type_spread {feat}; module_fan_out 1 (apps/cockpit)   → severity low
Size  (PH-02):     +2704 / -14, 19 files; new_source 6 / new_tests 6           → large-by-design (vertical slice); NOT a split candidate
Safety(PH-03):     migrations 0; schema/IDL 0; infra 0; secrets 0              → severity none
Completeness(PH-04): new source 6 / new tests 6 (1:1)                          → severity none
```
No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change touches `app.ts`, `routes/chat.ts`, `client.ts`, `Sidebar.tsx`,
`App.tsx` by extension (additive wiring) and reuses `readProducts`, `monogram`,
`InFlightLock`, `readSseStream` (EP-03). No pre-existing gap is exposed.

### Watch List (CR-04 — notes, no deltas)

1. **`randomToken()` in `routes/chat.ts` uses `Date.now()` + `Math.random()`.**
   This is a same-process confirm nonce (matched against the live proposal held
   in the per-process orchestrator instance), NOT a security/auth token and never
   leaves the localhost process. Collision risk is negligible and a collision
   would only mis-pair two concurrent setup attempts — which the SESSION_BUSY lock
   already prevents (one product per conversation). No change recommended.
2. **The onboarding orchestrator is a per-process singleton** carrying the live
   proposal across the propose→confirm turns. This matches the cockpit's existing
   single-founder-localhost assumption (the same one `InFlightLock` documents).
   If the cockpit ever became multi-tenant this would need a session-keyed store;
   out of scope for this slice and consistent with the locked architecture.

### Cross-Reference

- No prior `.security/` viability report for this project to cite.
- No existing hardening deltas covered.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc` + `eslint` + read-only gate on HEAD; 0 PR-introduced errors. Outputs in `tool-outputs/`.
- [✓] **CR-02 Dispatch shape.** Diff 2704 lines / 19 files — above carve-out. Reviewed cross-kind (backend + frontend) lenses against WP_BACKEND_STANDARD + WP_FRONTEND_STANDARD; this is an executor self-review at the Step-6.5 gate (single-agent author review, with full authoring context of every line).
- [✓] **CR-03 Full-file reads.** All 19 files authored/read end-to-end this session.
- [✓] **CR-04 Evidence discipline.** Findings: none; watch-list notes cite the symbol + file.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency-direction, new process-start, emitter-only mint, write-gate exception). Security: nothing surfaced (checks: scope-bound search + path normalisation, confirm-gate, NFR-SEC-03 log discipline, secrets/injection). Quality: nothing surfaced (CR-01 follow-up empty; JSX ident scan — all identifiers resolve; CR-10 performance — no loop-bound DB/RPC/fs, no N+1, awaits are sequential lifecycle steps; dead-surface — none; contract-drift — events match shared api-types union; test-coverage — 1:1).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low; PH-02 large-by-design (vertical slice, not a split candidate); PH-03 none; PH-04 none. No high → no downgrade.

#### Run details

- **Diff source:** `git diff change/create-autonomous-delivery-environment` (staged HEAD).
- **Neighbour expansion:** import-graph by inspection (additive wiring + reused helpers); within 20-file cap.
- **Scanners run:** tsc, eslint, read-only inventory gate, JSX-identifier scan, CR-10 performance grep.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no secrets/dep-CVE surface in this diff — pure TS additions, no new dependencies, no Dockerfile/IaC); `@vitest/coverage-v8` absent (coverage assessed by inspection — new files comprehensively tested).
