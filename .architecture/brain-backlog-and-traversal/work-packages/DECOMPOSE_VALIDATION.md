# Decompose Validation — Brain as a living backlog + traversable memory

> **Change:** CH-01KT60 · `create` · `brain-backlog-and-traversal`
> **WP set:** 13 (WP-001 … WP-013) · Tier M
> **Rubric:** `plugins/sulis/references/decompose-validation-rubric.md`
> **Verdict:** **PASS** (every MUST passes; no SHOULD failures)

## Summary

| Outcome | Count |
|---|---|
| PASS | 10 phases |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 0 |
| N/A (no applicable surface) | P5, P7, P-PLAT |

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| P1 Inventory completeness | ✓ | — | All 13 WPs carry Context, Contract, DoD (RGB), Sequence, Token cost, Dependencies, `verification:`. |
| P2 Atomicity | ✓ | — | One capability per WP; touch surface ≤ 2 source files + 1 test file each (≤ 8 SHOULD bound). No "and" in titles (WP-013's title names one act — the dogfood — with three sequenced sub-steps in one PR by design). |
| P3 Module naming + clean code | ✓ | — | Descriptive kebab-case slugs; no jargon prefixes, no single-letter abbreviations. Contract module names are the real codebase modules. |
| P4 Dependency graph correctness | ✓ | — | Acyclic (Kahn topo resolves all 13); all targets exist; max transitive depth 5 (≤ 8); valid topological order. Data-contract wiring check N/A — single-kind set (see P-contract note). |
| P5 Performance + non-functional | N/A | — | No request-handler/endpoint WP. Change has no network surface (TDD Armor: "no network, no external service, no secrets"). NFR-01 (graceful degradation) is asserted as a behavioural test per WP, not an SLA. |
| P6 Peer-collision risk | ✓ | — | No two WPs **Create** the same file path. Shared-file *extensions* are serialised via `dependsOn` (see below). |
| P7 ServiceSpec compliance | N/A | — | No service is defined; no `service-specs/` dir; no networked service in scope. |
| P8 Cross-WP identifier canonicalisation | ✓ | — | All shared identifiers minted at runtime from authoritative recipes (see below). No inline-minted literal in any WP Contract. |
| P10 P-PLAT (Platform Contract) | N/A | — | No WP carries `platform:`/`touch-class:`. SRD constraint: "No third-party platform write/deploy touch → no Platform Contract gate." Confirmed by grep — zero platform-tagged WPs. |

## Detailed findings per check

### P2 — Atomicity (the one judgement call)

Each WP is one logical capability implementable in one PR by one agent:
WP-001/002 are one compose fn each; WP-003/004/005 are one helper each;
WP-006/008 are one CLI surface each; WP-007 is one module's view-extensions
(three sibling functions sharing one extension point — atomic at the
module-edit level); WP-009/010/011 are one skill/agent body each; WP-012 is
one additive edit to one agent body; WP-013 is the single dogfood act.

**WP-013 note (anticipated reviewer flag):** its title names three sequenced
sub-steps (mature opportunity → capture two ideas → author+emit+run two
scenarios). This is **one atomic act by design** — the dogfood is the
end-to-end proof that cannot be split without leaving a half-proven path
(you cannot run the scenarios without first emitting through the path, and
you cannot emit through the path without the matured opportunity). The TDD's
bootstrapping-circularity note mandates it land as the single terminal WP.
Splitting would create WPs that each individually verify nothing. PASS with
this rationale recorded; not a SHOULD failure because the unit is genuinely
indivisible.

### P6 — Peer-collision (the shared-file serialisation)

Two source files are touched by more than one WP. Neither is a *create*
collision; both are serialised so no two branches edit the same file
concurrently:

| File | Created by | Extended by | Serialisation |
|---|---|---|---|
| `_brain_capture.py` | WP-003 (bootstrap) | WP-005 (`roadmap_add`), WP-004 (`capture_idea`) | WP-005 `dependsOn: WP-003`; WP-004 `dependsOn: WP-005` → strict chain WP-003 → WP-005 → WP-004 |
| `_brain_query.py` (pre-existing) | — | WP-005 (`roadmap_members`), WP-007 (views) | WP-007 `dependsOn: WP-005` → WP-005 → WP-007 |

P6.01 (no two WPs Create the same path): **PASS** — only WP-003 creates
`_brain_capture.py`; `_brain_query.py` already exists in the tree.

### P8 — Cross-WP identifier canonicalisation

Shared identifiers across the set are the Tenant / Product / Opportunity /
Requirement ULIDs. None is minted as a literal in any WP Contract; each
resolves to an authoritative upstream recipe:

| Identifier | Recipe | Authoritative source |
|---|---|---|
| `dna:tenant:<ulid>` | `Sha256CrockfordTenantDeriver.derive_consumer_tenant(repo_org_slash_name)` | ADR-002 (extends external `discover-project/ADR-002`) |
| `dna:product:<ulid>` | `_product_emission` deterministic recipe (reused) | ADR-002 |
| `dna:opportunity:<ulid>` | `_deterministic_ulid_from("opportunity-from-idea:" + seed)` | ADR-005 |
| `dna:requirement:<ulid>` | `_deterministic_ulid_from("requirement-from-idea:" + seed)` | ADR-005 |

Parallel-dispatched executors (WP-001, WP-002, WP-003) each derive ids via
the **same reused helper / canonical deriver** — there is no path where two
executors mint divergent values for the same conceptual entity (the
CH-01KSZ4 failure mode this phase exists to prevent). The `change_id`
frontmatter literal is the change handle, not a cross-WP entity id.

### Cross-kind detection (WP-08.5)

The set is **single-kind (`backend`)**. Python scripts, skill bodies, and
agent bodies are all verified through the backend adapter (pytest nodeids +
the run-from-graph scenario harness). No producer/consumer **data** contract
seam crosses kinds; therefore no `kind: contract` WP is required (WP-08.5
applies only when ≥2 of backend/frontend/async touch the same operation
surface). The CLI JSON envelopes (`{"ok":…}`) are produced and consumed
within the backend kind; their shape is pinned by the CLI integration tests
in WP-006 and WP-008 (CONTRACT_FIRST CF-03 satisfied in-kind).

### Per-kind gate audit (step 7a)

Every WP is `kind: backend`; each DoD names unit and/or integration tests
with named pytest nodeids per WP-05. The methodology-shaped WPs (WP-009,
WP-010, WP-011) additionally carry a `tests/methodology/` shape test **and**
name the run-from-graph scenario as their behavioural artifact (TDD §5). The
one REORGANISE WP (WP-012) carries a `characterisation_test:` field pinning
the existing `dispatch_via`/`artifact_owners` routing (EP-07 / WORKPACKAGE
REORGANISE rule). PASS.

### `verification:` field (step 4d)

All 13 WPs are **Shape 1 — concrete**: `adapter: backend` + `artifact:` a
pytest nodeid. No deferred (Shape 2) or trivial-carveout (Shape 3) WPs, per
the TDD Verification Plan §6 ("Infrastructure needs surfaced (deferred):
None"). Adapter value `backend` is one of the seven canonical kinds.

## Methodology (rubric self-attestation)

- [✓] **P1 Inventory completeness.** 13 WPs read end-to-end. Required sections found per WP: Context, Contract, DoD/RGB, Sequence, Token cost, Dependencies, `verification:`. Gaps: none.
- [✓] **P2 Atomicity.** Purpose statements parsed; touch surface counted (≤ 3 files/WP). 0 WPs exceed bounds. WP-013's three-step dogfood recorded as an indivisible unit with rationale.
- [✓] **P3 Module naming.** WP filenames + Contract module names scanned for jargon/single-letter slugs. 0 findings.
- [✓] **P4 Dependency graph.** DAG built from frontmatter `dependsOn`. Cycles: 0. Orphan targets: 0. Max depth: 5. Topo order valid. `wpx-index lint` → header `canonical`.
- [—] **P5 Performance + non-functional.** N/A — no request-handler WP; no network surface (TDD Armor). NFR-01 covered by per-WP behavioural failure-mode tests.
- [✓] **P6 Peer-collision risk.** Cross-WP file-create scan: 0 create-collisions. 2 shared-file extension chains serialised via `dependsOn` (table above).
- [—] **P7 ServiceSpec compliance.** N/A — no service defined; no `service-specs/`.
- [✓] **P8 Cross-WP identifier canonicalisation.** 4 shared identifier classes extracted; all 4 resolve to authoritative ADR recipes (ADR-002, ADR-005). 0 inline-minted literals flagged.
- [—] **P10 P-PLAT (Platform Contract).** N/A — 0 WPs carry `platform:`/`touch-class:`; SRD records no Platform Contract gate.

## Verdict

**PASS.** Every applicable MUST passes; no SHOULD failures; three phases
(P5, P7, P-PLAT) are not-applicable to a single-kind, no-network,
no-service, no-platform-touch change. The decomposition is complete and
ready for execution. Ready-now set: **WP-001, WP-002, WP-003**.
