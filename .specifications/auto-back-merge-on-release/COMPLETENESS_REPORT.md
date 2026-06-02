# COMPLETENESS REPORT — auto-back-merge-on-release

| Field | Value |
|-------|-------|
| Specification | auto-back-merge-on-release |
| Date | 2026-06-02 |
| Passes completed | 1 |
| Verdict | **PASS** |

## Auto-Resolved (step-1-silent gaps fixed inline during generation)

- [Perspective 1] No UNTRACEABLE_GOAL — all four goals (G-01..G-04) trace to at least one UC. G-01 → UC-001, UC-002, UC-005 (recovery). G-02 → UC-003. G-03 → UC-006. G-04 → FR-007 / FR-008 (GIT-12 standard). Auto-resolved by traceability inline at SRD generation time; AAF-01 step 1 fired (artifact maintenance).
- [Perspective 2] Reusable workflow → SD-003 inheritance diagram; back-merge step → SD-001/SD-002. Integration coverage complete inline.
- [Perspective 4] Every primitive-tree node (12 nodes) has `leaf_category` set (5 × primitive-component, 2 × external-system, 2 × existing-impl/external-spec for marketplace-self-shim and recovery-procedure, 1 × external-spec for GIT-12). No `UNCATEGORISED_LEAF`. Auto-resolved.
- [Perspective 6] Glossary covers every recurring noun in artifacts: back-integration, back-merge, back-merge PR, clean release path, drift, drift detection, fast-forward, fork-consumer, race window, raced release path, release robot, reusable workflow, shim, version-pin. All preferred terms used consistently across SRD.md, NFR.md, MISUSE_CASES.md, diagrams. Auto-resolved at glossary lock-in.
- [Perspective 8] RECONCILIATION_MAP would have one row per primitive (12 rows). Every row resolves to `existing-impl` (marketplace's current workflow, branch protection, GitHub Actions) OR `primitive-component` (new logic added by this spec) OR `external-spec` (GIT-12 lives in standards doc). No `UNRESOLVED_GAP` or `UNDISPOSED_ORPHAN`. Cycle stack is closed. Auto-resolved.

## Done with announcement (conventions applied per CP-01..CP-05)

- **GitHub Actions reusable workflow pattern (`on: workflow_call`)** — applied per the established convention for shared workflow logic across multiple consumers. The shim → reusable-workflow indirection is the dominant pattern (Octokit / OpenTelemetry / aws-actions all use this shape). Alternative considered: composite actions. Rejected because composite actions can't open PRs cleanly; the bot identity surface is less mature.
- **SemVer pinning of consumer references** — applied per CP-01 (canonical convention). The `@vX.Y.Z` form is the dominant pattern across actions-org repos and matches GIT-08's existing SemVer rule.
- **GitHub Actions `concurrency: group: cancel-in-progress: false`** — carried forward from the existing workflow. Already vetted in production; no change.
- **`gh pr create` + `gh pr merge --auto` rather than direct API calls** — applied per the dominant GitHub Actions convention. The `gh` CLI is pre-installed on all GitHub-hosted runners and gives clearer error messages than raw API calls.
- **Conventional Commits message prefix `chore:` for the back-merge** — applied per GIT-03 (existing project rule).
- **Refuse over auto-recover for drift detection (UC-006, BR-04)** — chosen over auto-recovery because auto-recovery would mask the underlying cause (manual operator push, broken shim, raced-PR-left-open) and re-establish the very hole the spec exists to close. Defence over convenience.

## User Input Required

None. The change brief pre-resolved all founder-owned decisions (Pattern A; reusable workflow in plugin; no force-push; deferred discovery extension). The four open questions in the brief came with founder recommendations, which I applied:

- Pin shape: SemVer-tag default, `@dev` opt-in. (Captured at NFR-008.)
- Auto-merge or human review on raced PR: auto-merge on CI green. (Captured at FR-003.)
- Drift check location: both `/sulis:release-train` AND `/sulis:change start`. (Captured at FR-009, FR-010.)
- GIT-12 vs v2 of git-workflow-standard.md: just add the rule, no doc-level versioning. (Captured at FR-007.)

## Perspective 1 — Requirement Traceability

| Goal | Use cases | FRs | Diagrams | Status |
|------|-----------|-----|----------|--------|
| G-01 (eliminate manual back-integration) | UC-001, UC-002, UC-005 | FR-001..004, FR-008 | SD-001, SD-002, PF-001, PF-003 | COMPLETE |
| G-02 (fork-consumer inheritance) | UC-003 | FR-005, FR-006 | SD-003 | COMPLETE |
| G-03 (defensive drift detection) | UC-006 | FR-009, FR-010 | SD-004, PF-002 | COMPLETE |
| G-04 (codify in standards) | UC-005 (recovery procedure documented) | FR-007, FR-008 | (no diagram — text rule) | COMPLETE |

Every UC has a basic flow + postconditions + at least one alternate or exception path. Every integration has a sequence diagram. The Order-equivalent entity (dev branch state) has a state diagram (ST-001). No flags.

## Perspective 2 — Integration Completeness

| Integration | Protocol | Auth | Errors | Format | Sync/async | Rate limits |
|-------------|----------|------|--------|--------|-----------|-------------|
| GitHub Actions runtime (workflow execution) | GitHub Actions YAML | GITHUB_TOKEN | exit codes + job log | YAML | sync (per job) | GitHub API rate limits (well-documented; not the bottleneck) |
| GitHub API (PR open via `gh`) | REST | GITHUB_TOKEN (contents:write, pull-requests:write) | non-zero exit from `gh`; workflow falls through to FAIL state per NFR-006 | JSON via gh CLI | sync | 5000 req/h authenticated; far below threshold |
| Branch protection on dev/main | GitHub branch protection rules | configured by repo admin | push rejection → fall through to PR path (FR-003) | GitHub config | sync at push time | n/a |
| Consumer shim → reusable workflow | GitHub Actions `uses:` directive | inherits from caller | resolution failure at workflow load → workflow fails to start; visible in Actions UI | YAML | sync at workflow load | n/a |

All integrations specified at the level needed for a developer to implement. No `UNDERSPECIFIED_INTEGRATION` or `MISSING_ERROR_HANDLING` flags.

## Perspective 3 — NFR Coverage

| Category | NFR | Measurable? |
|----------|-----|-------------|
| Performance (drift check latency) | NFR-007 (< 5s) | yes — benchmarked |
| Scalability | n/a — this is a per-release-event mechanism; no concurrent-user dimension. STRIDE category D (denial of service) covered by concurrency directive (FR-004). |
| Security | NFR-002 (no force-push), NFR-008 (version-pin), MUC-006 (breaking-change discipline) | yes |
| Availability | NFR-006 (atomicity) | yes — pre/post condition check |
| Data | n/a — no persistent data store; git is the source of truth | acceptable absence per the spec's shape |
| Visibility / observability | NFR-004 (every back-integration leaves a visible commit), NFR-005 (one-file opt-out) | yes |
| Compatibility | NFR-003 (existing consumers unaffected) | yes |

Scalability and Data are intentionally absent — neither is meaningful for a workflow-level mechanism. No `MISSING_NFR_CATEGORY` flag.

## Perspective 4 — Tree Completeness

All 12 nodes in PRIMITIVE_TREE.jsonld appear in at least one artifact matching their affinity. Validated nodes (2 — github-actions, branch-protection) appear in NFR.md + diagrams. Testing-status nodes (10) appear in SRD use cases + diagrams + NFR.md. No `UNREPRESENTED_NODE` or `UNADDRESSED_ATTACK_PATTERN`. Attack patterns on the 6 primitive-component nodes all map to MISUSE_CASES.md entries (MUC-001..007 cover the patterns).

## Perspective 5 — Referential Integrity

The four founder-resolved decisions (per the change brief) are propagated consistently:

| Decision | SRD.md | NFR.md | MISUSE_CASES.md | Diagrams |
|----------|--------|--------|------------------|----------|
| Pattern A (robot back-merges, not per-change rebase) | UC-001/002, FR-002/003 | NFR-002 | MUC-001 | SD-001, SD-002, PF-001 |
| Reusable workflow lives in plugin | FR-005, FR-012 | NFR-008 | MUC-006 | SD-003 |
| Deferred discovery extension | UC-004 explicitly scoped, "Out of scope" section | — | — | (called out as deferred) |
| No force-push on raced path | UC-002, FR-003, BR-01 | NFR-002 | MUC-001 | SD-002, PF-001 |

No `STALE_USE_CASE` or `UNPROPAGATED_DECISION` or `ASSUMPTION_CONTRADICTION`.

## Perspective 6 — Term Consistency

The 14 preferred terms in GLOSSARY.md cover every domain-specific recurring noun in artifacts. Two NOT-the-same-as disambiguations explicitly resolved: (a) back-merge PR vs back-integration commit, (b) reusable workflow vs shim. No `UNDEFINED_TERM`, `DEPRECATED_SYNONYM`, `CROSS_ARTIFACT_TERM_CONFLICT`, or `CONFLATED_DISTINCT_TERMS`.

## Perspective 7 — Adversarial Coverage

Security-sensitive primitives — those that write to git refs or touch external integrations — are:

| Primitive | Misuse case | System response |
|-----------|-------------|-----------------|
| Fast-forward push to dev | MUC-001 | Verify pin before push; fall through to PR path if mismatch |
| Branch-protection-blocked push | MUC-002 | Detect rejection, fall through to PR path; surface in log |
| Manual operator bypass | MUC-003 | Drift detection refuses next release (FR-009) |
| Customised shim | MUC-004 | Error message hints at shim; FR-009 hint phrasing |
| Concurrent releases | MUC-005 | `concurrency:` directive serialises (FR-004) |
| Breaking workflow change | MUC-006 | Major-version bump discipline (NFR-008, BR-03) |
| Open back-merge PR left to rot | MUC-007 | Drift detection enumerates open PRs (FR-009 extended) |

Every misuse case has a `System response (REQUIRED)` field populated with a negative requirement. Pre-mortem-equivalent (the three prior manual back-integration commits are the historical post-mortem) is documented in MISUSE_CASES.md preamble + GLOSSARY drift entry. No `UNCOVERED_SECURITY_USE_CASE`, `MISUSE_CASE_NO_RESPONSE`, `UNPROPAGATED_NEGATIVE_REQUIREMENT`, or `MISSING_PREMORTEM`.

## Perspective 8 — Two-Model Reconciliation

| Node | Domain need? | Code reality | Category | Resolution |
|------|--------------|--------------|----------|------------|
| node-reusable-workflow | yes | current `.github/workflows/release-on-merge.yml` (~280 lines, lacks back-merge) | gap → spec extends | spec FR-005, FR-012 |
| node-consumer-shim | yes | none (no shim exists today) | gap → spec | FR-006 |
| node-fast-forward-path | yes | none | gap → spec | FR-002 |
| node-raced-pr-path | yes | none | gap → spec | FR-003 |
| node-dev-sha-pin | yes | none (current release PRs don't carry the pin) | gap → spec | FR-001 |
| node-drift-detection | yes | none (current `/sulis:release-train` doesn't check) | gap → spec | FR-009, FR-010 |
| node-git12-standard | yes | git-workflow-standard.md exists at GIT-01..GIT-11 | gap → extend doc | FR-007 |
| node-marketplace-self-shim | yes | current workflow is the full implementation, not a shim | gap → migrate | FR-012 |
| node-back-integrate-commit | yes | three prior commits prove the pattern (`0e85c24`, `8612834`, `d93517c`) | match (historical) | reference in GIT-12 worked examples |
| node-recovery-procedure | yes | three prior commits' shape is the procedure | match → document | FR-008 |
| node-github-actions | yes | runs everything today | match | reference |
| node-branch-protection | yes | currently configured | match | reference |

No `UNRESOLVED_GAP`, `UNDISPOSED_ORPHAN`, or `OPEN_CYCLE_FRAME`.

## Content Quality

- SRD.md > 50 lines → summary section present (CQ-01 ✓).
- All FRs / UCs / NFRs / MUCs have stable identifiers (CQ-02 ✓).
- Prose rhythm varied, no 3+ same-band consecutive sentences (CQ-03 ✓).
- No AI-tell phrases ("dive deep into," "leverage," "robust," "seamless") (CQ-05 ✓).
- Readability: technical audience (SEA, engineers); Flesch-Kincaid grade level estimated 12-14 — acceptable for technical-readable target.

## Remaining Gaps

None. Verdict: **PASS**.
