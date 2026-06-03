# Decompose Validation — autonomous-delivery-environment (CH-01KT50)

> **Date:** 2026-06-03 · **Decomposer:** sulis:engineering-architect
> **Inputs:** TDD.md + ADR-001..005 + contracts/{openapi.yaml, DATA-CONTRACT-GUIDE.md, visual/sulis-app.contract.md} + SRD.md (29 reqs) + SPEC.md + existing apps/cockpit/.
> **Standards:** WORK_PACKAGE_STANDARD v1.2.0 (WP-01..11), CONTRACT_FIRST_STANDARD (CF-01..09, lightweight internal-seam tier).
> **Verdict: PASS.**

## Summary

16 atomic WPs · 2 contract / 8 backend / 5 frontend / 1 composite-integration.
Contract-first cross-kind decomposition (WP-08.5): data + visual contracts first,
backend + frontend in parallel against the contract, integration last. Dependency
graph machine-validated: no missing refs, no cycles, no self-deps.

---

## WP-01 Identity — PASS

Every WP carries `id` (WP-001..016, unique), `title` (founder-readable),
`kind` (contract×2 / backend×8 / frontend×5 / composite×1), `source: feature`,
and `change_id: 01KT500K2JTE2EGW6TPPQ4D4VN`. Grouped by `parent_phase`
(contract / reads / chat / surfaces / integration).

## WP-02 Atomic scope — PASS

Each WP is one-branch / one-engineer. One-file-per-WP held where practical
(status, brain, search routes; the two pure libs; each new component). The chat
relay (WP-009) legitimately touches route + gate-script + inventory-test because
they are one inseparable safety change (the gate must allow-list the exact file
the relay introduces — splitting them would land a route the gate rejects).
WP-016 is `composite` (integration spanning the swap + a11y + from-graph), the
correct kind per WP-08 for cross-cutting verification.

## WP-03 Acceptance criteria — PASS

Each WP lists 3–6 falsifiable criteria tied to specific FR/NFR/ADR clauses
(verbatim acceptance reused where the SRD gave it — e.g. FR-12 idle-but-fine
non-flag, NFR-SEC-02 A→B zero-bytes). No "works correctly" vagueness.

## WP-04 Test plan + WP-05 per-kind gates — PASS

- **backend** WPs → unit + integration + smoke; exact test paths named (supertest route tests, contract suites, pure-lib unit tests).
- **frontend** WPs → unit + component + visual_diff + a11y (axe-core) + perf_budget; exact `.test.tsx` paths named.
- **contract** WPs → schema validates + examples cover happy/error/empty (CF-03/04) + a consumer can build against it (WP-001 carries the error + empty fixtures; WP-002 is the signed visual contract).
- **composite** WP-016 → union of child gates + the CF-07 conformance (mock→real swap).

## WP-06 Lineage — PASS

Each WP has `derived_from` (TDD/ADR/SRD clause + file), `generated_by`
(plan-work-run/2026-06-03 + sulis:engineering-architect), `addresses_findings`
(empty — this is feature work, not finding-remediation), `invalidated_by` (null
until loop-close), and `depends_on`.

## WP-07 Status — PASS

15 `pending`, 1 `done` (WP-002, the signed visual contract — `done` is correct so
the #45 done-oracle gate is open for the frontend WPs).

## WP-08.5 / CF-05 Contract-first cross-kind — PASS

- **Data contract (WP-001) lands first.** Backend + frontend depend on it, not on each other where independent (CF-05 parallel-not-sequential): the frontend WPs do NOT depend on the backend route WPs except where a surface genuinely consumes a specific endpoint's data (WP-012→WP-003 status; WP-013→WP-004 brain; WP-014→WP-005 search; WP-015→WP-009 SSE relay). Those are real producer/consumer edges, not bundling — the consumer builds against the contract (WP-001) and the named endpoint.
- **User-facing seam has TWO contracts.** Data (WP-001) + visual (WP-002, `contract_type: visual`). Every frontend WP declares `visual_contract: WP-002` and `dependsOn` it (#45 enforced).
- **Integration child last (WP-016).** `kind: composite`, swaps RecordedSessionBridge→StreamJsonSessionBridge, runs the CF-07 conformance + the six from-graph scenarios. The parent merge gate is this integration's pass.

## #45 Visual-contract gate — PASS (carried verbatim)

WP-002 carries `signed_off_at: 2026-06-03T08:31:03Z` + `provenance:
production-approved` exactly as in `contracts/visual/sulis-app.contract.md`. It is
`status: done`, so the frontend WPs' dependency on it is satisfied at write-time
and at their done-transition. The frontend WPs can proceed. **The #45 gate is
passed, not pending.**

## CF-03 three-category errors — PASS

The data contract error envelope carries the three chat codes (SESSION_BUSY 409 /
SESSION_CHANGE_MISMATCH 422 / SESSION_UNREACHABLE 502), mapped to client/network
/ validation / upstream categories. WP-001's fixture covers error + empty cases.

## CF-09 streaming contract — PASS

`ChatStreamEvent` is a structured discriminated event schema (state / chunk /
complete / error), not a raw byte stream (ADR-001).

## Sensitive write/act path constraints (NFR-SEC) — PASS

The four chat-path WPs carry the constraints explicitly:
- **WP-008** binding guard (act only on the targeted change; fail-closed; identical for live/resume/spawn — NFR-SEC-02/06) + one-in-flight lock (FR-20/NFR-REL-03).
- **WP-009** read-only-gate extension: exactly one sanctioned write path; everything else provably read-only (FR-N1, NFR-SEC-05, NFR-ARCH-02); no message body in logs (NFR-SEC-03); failure surfacing (FR-19/FR-N3); partial-on-break (FR-22).
- **WP-010** resume/spawn act on only the targeted session; never fabricate completion (FR-26/FR-N5); process-start confined to this one file.
- **WP-015** honest resume/incomplete-step surfacing client-side (FR-26/FR-N5); composer acts only on the open change.

## Change primitives — PASS

EXPAND-Create for the new port/adapters/routes/libs/components (incl. the
SessionBridge adapter, correctly classified Create-not-Wrap per the catalogue —
the public face is the cockpit's own port). REORGANISE-Refactor for the two
client refactors (Board WP-011, ThreadView WP-012), each carrying a
`characterisation_test` in Red (EP-07 MUST). REINFORCE-Test for the integration
WP-016. No Wrap-over-internal. No wrapper rot.

## EP-03 extend-don't-rebuild — PASS

WPs target real existing files: `shared/api-types.ts`, `server/app.ts`,
`server/routes/`, `server/lib/`, `server/ports/`, `scripts/check-read-only.sh`,
`client/src/pages/{Dashboard,ThreadView}.tsx`, `client/src/components/` (reusing
ChangeCard / StageBadge / LivenessDot / Monaco / contract renderer). No rebuild.

## Scenario linkage (from-graph verification) — PASS

All six emitted scenarios are linked from the WP that delivers them; WP-016
aggregates all six for the `sulis-verify-acceptance --scenario` from-graph run:

| Scenario | WP(s) |
|---|---|
| See everything in flight at a glance (board) | WP-011 |
| Understand where a change is (status) | WP-012, WP-003 |
| Talk to the agent about a change (chat) | WP-015, WP-009 |
| Find a change (search) | WP-014, WP-005 |
| Read a document rendered (previews) | WP-013 |
| See what the agent has created (brain) | WP-013, WP-004 |

## Deferred infrastructure needs (carried from SRD/TDD) — PASS

- `recording-bridge-claude-session` — referenced by WP-007 (fixture), WP-010 (prod-adapter parity), WP-016 (live swap). Canonical `{noun}-{noun}-{scope}` identifier.
- `seed-brain-entities-fixture` — referenced by WP-004 (brain route test). Canonical identifier.

## Dependency-graph machine check — PASS

```
WP count: 16 · by kind: contract 2, backend 8, frontend 5, composite 1
missing dep refs: none · cycles: none · self-deps: none
ready (pending + all deps done): [WP-001] · done: [WP-002]
```

## Genuine founder-owned gaps

**None at decomposition stage.** The two open architecture questions in the TDD
(§11 — exact "needs attention" set; search content-reach) were resolved in the
SRD/contract (`needsAttention.reason` enum is fixed; search is over content) and
are encoded as falsifiable acceptance in WP-003/005. The one founder-owned design
call (the AI-03 seamless-delivery vs human-in-the-loop reconciliation) is already
resolved in the signed visual contract (send-is-consent; consequential downstream
actions gated). No new founder decision is required to start building.
