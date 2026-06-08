# Work Package Standard

> **Sulis-local v1.1.0 (2026-05-25).** No platform precedent — this codifies what `sulis-execution` already does informally, plus the per-kind execution shapes (backend / frontend / async / docs / infra / composite) the methodology needs going forward.
>
> **v1.1.0 amendment** (Phase 4 of change-as-primitive build): adds the `change_id:` field to WP-01 Identity, linking every WP to its parent change. Backwards-compatible — `change_id:` is optional for legacy WPs created before the change primitive landed.

> **Version:** 1.1.0
> **Status:** Active
> **Purpose:** Define the canonical unit of execution work in sulis. Every actionable thing that flows from a code-health finding to a shipped commit is a Work Package (WP). This standard documents the primitive: file format, identity, lineage, status lifecycle, executor dispatch contract, and the rules for composing WPs into larger arcs.

---

## Conclusion (Pyramid Principle — lead with the answer)

A **Work Package (WP)** is one markdown file describing one atomic unit of executable work. It carries identity (ID + kind + source), scope (acceptance criteria + test plan), lineage (which findings it addresses + which scanner run produced them), and status (lifecycle + verification gates). The executor reads `kind:` to dispatch to the right execution path; the loop closes when the next scanner run confirms the finding is gone.

The WP is the **single point of truth** between three skill families:

1. **Detection** (`code-health`, `check-*`) produces findings
2. **Characterisation** (`/sulis:address-findings`, `sea:engineering-architect`) turns findings into WPs
3. **Execution** (`sulis-execution:executor` today; eventually per-kind executors inside sulis) runs WPs

This standard governs the shape of WPs only. Per-kind execution mechanics live in companion standards (`WP_BACKEND_STANDARD.md`, `WP_FRONTEND_STANDARD.md`, `WP_ASYNC_STANDARD.md`) — to be authored as each execution kind is built out.

---

## Why this exists

Without a canonical WP primitive, three things break:

1. **No standard hand-off between SEA / sulis-execution / check-* skills.** Today each skill emits its own shape; the next skill in the chain re-parses it. Friction accumulates as new kinds are added.
2. **No lineage.** The founder ships a fix, has no automated way to verify the original finding is actually gone. The loop never closes; trust in the methodology stays anecdotal.
3. **No founder-readable queue.** "What's next to work on?" requires scanning directories. With an INDEX.md derived from per-WP files, the founder reads one file to see the whole state.

The primitive defined here unblocks all three.

---

## Requirements

### WP-01: Identity

Every WP MUST have:

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Globally unique within the project. Format: `WP-NNN` (sequential within a change) or `WP-{SOURCE}-{NNN}` (e.g., `WP-HD-AA-001`). Conventional, not enforced — IDs in the same project just have to be unique. With `change_id:` populated, WP-NNN sequencing is per-change; cross-change collisions don't matter because the change_id disambiguates. |
| `title` | yes | One-line plain-English summary. Founder-readable. |
| `kind` | yes | One of: `backend` / `frontend` / `async` / `docs` / `infra` / `contract` / `composite`. Determines which executor + which verification gates apply. (`contract` is the producer/consumer seam — see WP-08.5.) |
| `source` | yes | Where this WP came from: `hardening` / `feature` / `migration` / `refactor` / `observability` / `bug` / `manual`. Determines where the WP file lives within `.architecture/{project}/`. |
| `change_id` | optional (required for WPs created after Phase 5 of the change-as-primitive build) | ULID of the parent change this WP belongs to. Format: 26-character Crockford-base32 ULID (e.g., `01HQ8XQM8G5KZGZQXPZD8H6PJ7`). Every WP created via `/sulis:change start` automatically gets the parent change's ULID. Legacy WPs (created before the change primitive) omit this field; they execute against `dev` directly without a change branch. See `change-work-standard.md` CW-04 for the change-branch + WP-branch hierarchy this field enables. |
| `parent_phase` | optional | Groups related WPs (e.g., `HD-AA` for the hardening bundle in the transcript). Used by the INDEX.md generator to show grouped progress. |

### WP-02: Atomic scope

A WP MUST represent one atomic unit of work — one engineer, one branch, mergeable independently. Two tests:

- **One-branch test:** the work fits on a single feature branch with a single merge to dev. If it needs two branches, it's two WPs.
- **One-engineer test:** one engineer can hold the whole change in their head. If it needs coordination across people, it's a composite (see WP-08).

Multi-day work is fine if the work is sequential and the engineer can checkpoint daily. Multi-engineer concurrent work is not — break it into composite.

### WP-03: Acceptance criteria

Every WP MUST list 1-5 observable criteria that prove the WP is done. Each criterion MUST be:

- **Falsifiable.** "Works correctly" is not falsifiable; "POST /api/items returns 201 with a JSON body matching schema X" is.
- **Verifiable without judgment.** A test can determine it, or a mechanical check, or a deploy gate. Not a human judgment call.
- **Specific to this WP.** Not the global system being healthy.

Example (from the transcript):
```yaml
acceptance_criteria:
  - "ET.parse → defused_ET.parse at workspace.py:269 (single line replacement)"
  - "Characterisation test test_xxe_workspace_parse passes locally"
  - "branch-ci #N green"
```

### WP-04: Test plan

Every WP MUST list the tests that prove the acceptance criteria, named at named levels. Levels depend on `kind` (see per-kind standards) but at minimum every WP names:

- The unit/integration tests that pass before merge
- The verification step (CI workflow run, deploy gate, smoke endpoint) that proves the change is live

Test names should be exact paths (`tests/integration/test_workspace.py::test_xxe_workspace_parse`) so the executor can pin them in CI.

### WP-05: Verification gates (per-kind)

Every WP cites which verification gates apply, determined by `kind:`. The complete set lives in the kind-specific standards; this standard documents the contract:

| Kind | Minimum gates |
|------|---------------|
| `backend` | unit tests + integration tests + smoke at API boundary |
| `frontend` | unit tests + component tests + visual diff + a11y check + perf budget |
| `async` | unit tests + integration tests (full enqueue/dequeue) + chaos test + idempotency proof |
| `docs` | link-integrity check + a11y for rendered output |
| `infra` | Terraform plan + drift detection + staging destroy-test |
| `contract` | schema validates (OpenAPI / JSON Schema lint) + examples cover happy + error + empty cases (CF-03/CF-04) + at least one consumer mock generated from it (CF-05) |
| `composite` | union of child WP gates; parent merges only when all children merge |

The executor reads `kind:` and refuses to mark a WP done until its gates pass.

### WP-06: Lineage (PROV-O-aligned)

Every WP MUST record lineage — what produced it, what it addresses, what activity created it, what agent authored it. Field names borrow the W3C PROV-O vocabulary but the format stays YAML (no JSON-LD machinery; no tooling tax). Migration path to JSON-LD is preserved by the field-name alignment.

```yaml
# Lineage block (PROV-O-aligned)
derived_from:           # PROV-O: wasDerivedFrom — what findings this WP came from
  - finding: code-health::tier-2::semgrep::python.lang.security.use-defused-xml::workspace.py::40
    found_in: .checkup/{project}/runs/2026-05-24T14:30:00Z/CHECKUP.md
    severity_at_discovery: critical

generated_by:           # PROV-O: wasGeneratedBy — what activity created this WP file
  activity: address-findings-run/2026-05-24T15:00:00Z
  agent: claude-session/<id>           # or "manual" if a human authored it directly

addresses_findings:     # finding signatures the loop-closed check will verify gone
  - code-health::tier-2::semgrep::python.lang.security.use-defused-xml::workspace.py::40
  - code-health::tier-2::semgrep::python.lang.security.use-defused-xml-parse::workspace.py::269

# Set by the executor when the loop closes (or by the loop-closed checker on re-scan)
invalidated_by:         # PROV-O: wasInvalidatedBy — proof finding is gone
  activity: code-health-run/2026-05-24T16:00:00Z
  result: "finding signatures NO LONGER PRESENT — loop closed"
```

Five-field minimum: `derived_from`, `generated_by`, `addresses_findings`, `invalidated_by` (set on loop-close), and any sibling `depends_on` (WP-08).

### WP-07: Status lifecycle

Every WP carries a status field. The lifecycle:

| Status | Meaning | Set by |
|--------|---------|--------|
| `pending` | Ready to start, all dependencies met | Default on file creation |
| `in_progress` | Claimed by an executor or human; branch is open | Executor on claim |
| `blocked` | Started but waiting on a sibling WP or external decision | Executor on detection of a blocker |
| `sleeping` | Paused intentionally — needs a decision before resuming (cost approval, scope clarification) | Human or executor |
| `done` | Merged; verification gates passed; awaiting loop-close check | Executor on merge |
| `closed` | Loop-closed: next scanner run confirmed the finding is gone | Loop-closed checker |
| `regressed` | Loop-closed once, then finding reappeared in a later scan | Loop-closed checker |
| `abandoned` | Scope no longer relevant; will not ship | Human |

The INDEX.md generator buckets WPs by status (see WP-10).

> **Canonical status word (L-03):** `pending` is the one word for "ready to
> start" across the whole toolchain (`wpx-index list-ready`, the train, the
> orchestrator, the `plan-work` template). The legacy spellings `todo` and
> `ready` are tolerated only on the read path — the INDEX generator still
> buckets them as ready so old files surface — but a WP being added or
> decomposed MUST use `pending`. `wpx-index add-wp` / `sync-auto-drafts`
> reject any other spelling loudly rather than let a drifted-status WP vanish
> from the ready set.

### WP-08: Composite WPs

Cross-kind work (backend + frontend API change, schema migration spanning backend + async) is real. Two ways to represent it:

**Composite parent + per-kind children** (RECOMMENDED for most cases):

```yaml
# Parent WP
id: WP-042
kind: composite
title: "Migrate Compute API to v2"
child_wps:
  - WP-042a    # kind: backend — implement new endpoints
  - WP-042b    # kind: frontend — switch consumer to v2
  - WP-042c    # kind: docs — update API reference
acceptance_criteria:
  - "All three child WPs merged + verified"
```

Each child has its own `kind`, runs through its own per-kind executor, has its own verification gates. The parent merges only when all children merge.

**Multi-kind WP** (rare — use only when fixes must ship in one commit, e.g., atomic schema change touching backend handlers AND async in-flight messages simultaneously):

```yaml
id: WP-043
kinds: [backend, async]      # NOTE: plural — only valid for genuinely atomic cross-kind changes
title: "Add tenant_id column + propagate through message envelope"
```

Default to composite. Only use multi-kind when atomic shipping is genuinely required.

### WP-08.5: Contract-first cross-kind decomposition (MUST when cross-kind)

When a composite spans a **producer/consumer seam** (backend + frontend, or
tool + caller) the children MUST be decomposed contract-first per
`CONTRACT_FIRST_STANDARD.md`:

1. **A `kind: contract` child WP comes first.** It defines the schema layer
   (operations + types + the three error categories + LLM-/dev-facing
   descriptions) and the example stubs (happy + **error** + **empty**). Its
   gates are the contract-kind gates above.
2. **The kind-specific child WPs (backend, frontend, …) `dependsOn` the
   contract WP — and not each other** (CF-05 parallel-not-sequential). The
   frontend WP `dependsOn: [WP-contract]`; it does *not* `dependsOn` the
   backend WP. Both build at once, the consumer against the contract mock.
3. **An integration child WP comes last** — `kind: composite` or `kind: docs`
   with `produces: integration-check` — that swaps the mock for the real
   producer and runs the conformance check (CF-07). The parent composite's
   merge gate is this integration's pass.

Worked shape:

```yaml
# Parent
id: WP-100
kind: composite
title: "Add orders API + UI"
child_wps:
  - WP-100a    # kind: contract  — orders API schema + stubs (FIRST)
  - WP-100b    # kind: backend   — implement endpoints   (dependsOn: WP-100a)
  - WP-100c    # kind: frontend  — orders view           (dependsOn: WP-100a)
  - WP-100d    # kind: composite — integration: mock→real + conformance check
                #                  dependsOn: [WP-100b, WP-100c]
```

> **User-facing seams need TWO contracts.** When the consumer is a UI, a
> `kind: contract` WP for the **data** contract is paired with a **visual**
> contract — itself a `kind: contract` WP with `contract_type: visual` (tokens
> + HIG + UX patterns + a real-token mockup, per `UX_VISUAL_DESIGN_STANDARD.md`
> UXD-14). The frontend WP MUST declare `visual_contract: <that WP id>` and
> `dependsOn` it. The visual-contract WP reaches `done` only when the founder
> signs off the rendered mockup (`signed_off_at` + `provenance:
> production-approved`). This is enforced by `wpx-index` at write-time (a
> frontend WP without the dependency is refused) and at the done-transition (an
> unsigned visual contract can't be marked done) — #45.
>
> (Earlier this standard said the visual contract "isn't its own WP"; #45
> makes it a WP so the dependency is enforceable via the existing done-oracle
> rather than aspirational prose.)

> **Founder-facing flows need an interaction contract.** When the
> founder-facing capability spans a **multi-step interaction flow** (a sequence
> the user walks end-to-end, not a single screen), the work **SHOULD** emit a
> `kind: contract` WP with `contract_type: interaction` — sibling to the visual
> contract. Its done-gate is the **exercised-flow predicate**: the WP reaches
> `done` only when the flow has been **exercised end-to-end over stub
> adapters** and the evidence is recorded (`exercised_at` + `exercised_by` ∈
> {`agent-observed`, `human-attested`} + `exercised_attestation`). That gate is
> enforced by `wpx-index` at the done-transition — the same done-oracle that
> signs off the visual contract — so an un-exercised interaction contract can't
> be marked done.
>
> **Phase 1 is SHOULD strength.** This callout makes the interaction contract a
> recommended decomposition with a runtime done-gate for any WP that *opts in*
> by declaring `contract_type: interaction`. Making it **MUST** — mandatory for
> *all* founder-facing work, enforced at write-time so a founder-facing WP
> without an interaction contract is refused at INDEX entry — is the **Phase 2**
> flip, and is explicitly **out of scope** here (ADR-002). Until Phase 2 lands,
> the interaction contract is SHOULD, not MUST.

> **Exemption.** Single-kind work and `--prototype` changes are exempt from
> contract-first decomposition (`CONTRACT_FIRST_STANDARD.md` tier carve-out).

### WP-09: Loop-closed verification

A WP MUST close its loop — i.e., prove the original finding is gone — before status advances from `done` → `closed`. The mechanism:

1. WP merges and deploys (status → `done`)
2. Loop-closed checker re-runs the scanner that produced the original finding(s) listed in `addresses_findings`
3. For each finding signature in `addresses_findings`:
   - If absent in the new scan → finding closed
   - If present → finding NOT closed; WP marked `done` but flagged for reopen review
4. When ALL `addresses_findings` are absent → status → `closed`, `invalidated_by` set to the new scanner run
5. If a previously-closed finding reappears in a later scan → original WP gets status → `regressed` + a new WP is auto-created with `derived_from` pointing to both the original finding AND the regression scan

The loop-closed check is the empirical proof. Without it, "done" is just "someone wrote code."

### WP-10: Index regeneration

The per-WP markdown files are authoritative; `INDEX.md` is derived. The INDEX MUST be regenerated whenever a WP file is created, modified, or its status changes. The INDEX is read by founders + agents to answer "what's next?"; it is NEVER hand-edited.

The INDEX MUST bucket WPs by status (see WP-07) with a sub-grouping by `kind` within each bucket. Format example:

```markdown
# Work Packages — {project}

## ▶ Ready to start (N)
- WP-001 — Replace xml.etree with defusedxml in probe        (backend, 2h)
- WP-002 — Add CHANGELOG.md to sulis-platform-sdk plugin     (docs, 30min)

## 🔄 In progress (N)
- WP-003 — Split compute_router.py into per-resource modules (backend, 8h)
       └─ claimed by Iain, started 2026-05-24 14:00

## ⏸ Blocked (N)
- WP-004 — Wire frontend rate-limit indicator               (frontend, 4h)
       └─ waiting on WP-003

## 💤 Sleeping (N)
- WP-006 — Distributed rate-limit / Redis                   (backend, 6h)
       └─ awaiting Memorystore spend approval

## ✅ Done — awaiting loop-close verification (N)
## 🔒 Closed (last 7 days) (N)
## 🔁 Regressed (N)
```

### WP-11: File layout convention

```
.architecture/{project}/
├── work-packages/
│   ├── INDEX.md                       # derived — never hand-edit
│   ├── WP-001.md
│   ├── WP-002.md
│   └── ...
├── hardening-deltas/                  # source=hardening characterisation artifacts
│   └── HD-AA-001.md                   # → produces 1..N WP files
├── refactor-plans/                    # source=refactor characterisation artifacts
│   └── kitchen-sink-refactor-2026-05-23.md
└── skill-proposals/                   # output from "extract skill when recurring"
    └── SP-001-split-kitchen-sink.md
```

Characterisation artifacts (HDs, refactor plans, skill proposals) live in their own subdirectories and are referenced from the WP frontmatter via `derived_from.activity`. WP files all live in `work-packages/` regardless of source.

---

## Required WP file shape

Complete worked example. Every field marked `required` per WP-01..WP-10:

```yaml
---
# Identity (WP-01)
id: WP-001
title: "Replace xml.etree with defusedxml in probe workspace.py"
kind: backend                          # WP-01 — dispatches executor
source: hardening                      # WP-01 — determines characterisation-artifact location
parent_phase: HD-AA                    # WP-01 — optional grouping

# Scope (WP-02..04)
atomic_branch: yes                     # WP-02 — confirms one-branch fit
estimate: 2h                           # WP-02 — small/medium/large or hours
blast_radius: low                      # WP-02 — low/medium/high
acceptance_criteria:                   # WP-03
  - "ET.parse → defused_ET.parse at workspace.py:269 (single line replacement)"
  - "Characterisation test tests/integration/test_workspace.py::test_xxe_workspace_parse passes locally"
  - "branch-ci #N green on the WP branch"
test_plan:                             # WP-04
  unit: []                              # no new unit tests; existing pass
  integration:
    - "tests/integration/test_workspace.py::test_xxe_workspace_parse"
  verification:
    - "branch-ci workflow on PR"
verification_gates: [unit, integration, smoke]   # WP-05 (per-kind default for backend)

# Lineage (WP-06 — PROV-O-aligned)
derived_from:
  - finding: code-health::tier-2::semgrep::python.lang.security.use-defused-xml::workspace.py::40
    found_in: .checkup/agents/runs/2026-05-24T14:30:00Z/CHECKUP.md
    severity_at_discovery: critical
  - finding: code-health::tier-2::semgrep::python.lang.security.use-defused-xml-parse::workspace.py::269
    found_in: .checkup/agents/runs/2026-05-24T14:30:00Z/CHECKUP.md
    severity_at_discovery: critical
generated_by:
  activity: address-findings-run/2026-05-24T15:00:00Z
  agent: claude-session/abc123
addresses_findings:
  - code-health::tier-2::semgrep::python.lang.security.use-defused-xml::workspace.py::40
  - code-health::tier-2::semgrep::python.lang.security.use-defused-xml-parse::workspace.py::269
invalidated_by:                        # set by loop-closed checker on next scan; null until then
  activity: null
  result: null

# Lifecycle (WP-07)
status: todo                           # WP-07 — updated by executor
depends_on: []                         # sibling WPs that must complete first

# Composite (WP-08 — null unless composite/multi-kind)
child_wps: []
kinds: null                            # only set for rare multi-kind atomic WPs

# Rollback (always required)
rollback: |
  Revert the single commit. No data migration, no config change.
  defusedxml is a drop-in replacement; the change is pure code.
---

# Replace xml.etree with defusedxml in probe workspace.py

## Why

Two semgrep findings on `probe/workspace.py` (`use-defused-xml`, line 40 + `use-defused-xml-parse`, line 269). Native `xml.etree.ElementTree` is XXE-vulnerable. Input today is local developer-owned `pom.xml` files (low real-world risk), but `defusedxml` is the canonical mitigation per OWASP guidance and a drop-in replacement. Belt-and-braces hardening — no downside.

## What changes

- `plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py` line 40 (import)
- `plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py` line 269 (parse call site)
- `plugins/sulis/skills/analyse-codebase/requirements.txt` — add `defusedxml>=0.7.1`

## How

Single-commit change. Replace:
```python
from xml.etree import ElementTree as ET
```
with:
```python
from defusedxml import ElementTree as ET
```

`ET.parse(manifest)` at line 269 needs no change — `defusedxml` exposes the same API.

## Tests

`tests/integration/test_workspace.py::test_xxe_workspace_parse` — new characterisation test: parses a malicious `pom.xml` with an XXE payload; asserts `defusedxml` raises `EntitiesForbidden` (native ET would silently expand). Test is the regression gate.

## Rollback

Revert the commit. `defusedxml` is a drop-in replacement; no data migration, no config change.
```

---

## Executor dispatch contract

The executor (today `sulis-execution:executor`; long-term moving into sulis per the migration plan) reads `kind:` and dispatches:

| `kind:` | Executor | Source |
|---------|----------|--------|
| `backend` | `sulis-execution:executor` (today); future `sulis:execute-backend` | Exists; encodes the RGB-TDD loop documented elsewhere |
| `frontend` | `sulis:execute-frontend` | NEW — to be authored alongside `WP_FRONTEND_STANDARD.md` |
| `async` | `sulis:execute-async` | NEW — to be authored alongside `WP_ASYNC_STANDARD.md` |
| `docs` | `sulis:execute-docs` | NEW — light executor; link-integrity + a11y gates only |
| `infra` | `sulis:execute-infra` | NEW — Terraform plan + drift |
| `composite` | `sulis:execute-composite` | Not directly executable; orchestrates child WPs in `depends_on` order |

The executor refuses to claim a WP whose `depends_on` siblings are not yet `closed` (or `done` if loop-close is pending). The executor refuses to mark a WP `done` until its `verification_gates` all pass. These are bright-line refusals — no override flags.

---

## Lineage chain — what the loop-closed check does

1. **Scanner runs.** Produces findings with stable signatures. State: `code-health-run/<TIMESTAMP>` → `findings/*`.
2. **Characterisation runs.** `/sulis:address-findings` reads findings, produces WP files. Each WP's `derived_from` points to the originating findings; `generated_by` points to the characterisation activity + agent.
3. **Executor claims a WP.** Status `todo` → `in_progress`. Writes commit with trailer `WP: WP-001` + `Addresses: <finding-signature>`.
4. **Merge + deploy.** Status `in_progress` → `done`.
5. **Loop-closed checker fires.** Re-runs the scanner that produced the original findings. Compares finding-signature lists.
   - All `addresses_findings` absent → status `done` → `closed`; sets `invalidated_by`.
   - One or more still present → status stays `done`; flagged for reopen review.
6. **Future scan.** If a `closed` WP's findings reappear → original WP status `closed` → `regressed`; auto-create a new WP with `derived_from` pointing to BOTH the original finding AND the regression scan.

The chain is the empirical proof. No human attestation needed at any step — the scanner result IS the verdict.

---

## What this standard does NOT do

- **Per-kind execution details.** Live in `WP_BACKEND_STANDARD.md` / `WP_FRONTEND_STANDARD.md` / `WP_ASYNC_STANDARD.md` / etc. Authored alongside each kind's executor.
- **Characterisation methodology.** How findings become WPs is `/sulis:address-findings`'s concern. This standard documents the WP shape; characterisation produces files matching it.
- **CI / deploy mechanics.** Each project's CI configuration is project-specific. This standard requires that `verification_gates` produce a verdict; it does not prescribe which CI tool / which deploy script.
- **Git workflow.** Conventional commits + `WP:` / `Addresses:` trailers are recommended (see WP-06 lineage section), but not enforced here. The commit-msg hook lives in the project's `.githooks/`.
- **INDEX.md generator implementation.** WP-10 specifies the contract; the implementation (script that scans `work-packages/*.md` and renders `INDEX.md`) lives in `plugins/sulis/_lib/wp_index.py` (NEW — to be authored).

---

## Vocabulary

- **Work Package (WP)** — atomic unit of executable work; one markdown file in `work-packages/`.
- **Finding signature** — stable string identifier for a finding from any scanner. Already emitted by every check-* skill in `extras.signature`.
- **Lineage** — the PROV-O-aligned chain of pointers from finding → WP → commit → CI → deploy → next-scan verification.
- **Loop-closed** — status when the next scanner run confirms the finding(s) the WP addressed are gone. The proof the WP worked.
- **Characterisation artifact** — the document a characterisation skill writes (HD, refactor plan, skill proposal) before producing WP files from it.
- **Composite WP** — parent WP with child WPs of different kinds; merges atomically when all children merge.
- **Multi-kind WP** — rare; one WP with `kinds: [backend, async]` for genuinely atomic cross-kind work. Default to composite.
- **Regression** — a `closed` WP whose findings reappear in a later scan. Triggers a new WP with lineage pointing to both the original and the regression scan.

---

## Relationship to other standards

| Standard | Relationship |
|----------|-------------|
| CRITICAL_THINKING_STANDARD.md | WP acceptance criteria must be falsifiable per FR-01..FR-04. WP scope must pass MECE (no overlap with sibling WPs). |
| DECOMPOSITION_PROCEDURE.md | Composite WPs decompose into children per PD-01..PD-06 (typed dependencies, fan-out ≤ 7, termination). |
| SPIRAL_TEMPLATES.md | A WP's verification gates run inside the executor's spiral. The executor itself runs under HEAVY_TIER_DEFAULT (Independence Check applies when the verification gate is a sub-agent dispatch). |
| REFERENTIAL_INTEGRITY_STANDARD.md | WP `depends_on` declarations follow forward-only declaration rules. Reference integrity validates that referenced WP IDs exist. |
| STANDARDS_RUBRIC.md | WP-related skills (characterisation, executor) cite this standard in their `processing` phase. |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-24 | Initial sulis-local definition. 11 requirements (WP-01..WP-11). Codifies the WP primitive that `sulis-execution` uses informally; documents the kind-based executor dispatch contract; introduces lineage (PROV-O-aligned vocabulary, no JSON-LD machinery), loop-closed verification, INDEX.md derivation, and composite/multi-kind composition rules. Per-kind execution details deferred to companion standards (WP_BACKEND_STANDARD, WP_FRONTEND_STANDARD, WP_ASYNC_STANDARD, WP_DOCS_STANDARD, WP_INFRA_STANDARD) — authored as each kind's executor is built. |
| 1.1.0 | 2026-05-25 | Added the `change_id:` field to WP-01 Identity as part of Phase 4 of the change-as-primitive build (sulis v0.41.0). Optional for backwards-compat with legacy WPs; required for WPs created via `/sulis:change start` post-Phase 5. Field is a 26-character Crockford-base32 ULID linking the WP to its parent change. Per-change WP-NNN sequencing now disambiguated by change_id (cross-change collisions OK). |
| 1.2.0 | 2026-05-26 | Wired CONTRACT_FIRST_STANDARD into decomposition. Added `contract` to the `kind:` enum + its WP-05 gates row (schema lints, examples cover happy/error/empty, ≥1 consumer mock). Added WP-08.5 — contract-first cross-kind decomposition: cross-kind composites MUST emit a `kind: contract` child first, kind-specific children depend on it (parallel, not sequential), integration child closes with the conformance check. User-facing seams pair the data contract with the visual contract (design artifact per UX_VISUAL_DESIGN_STANDARD UXD-14). Single-kind + `--prototype` exempt. |
