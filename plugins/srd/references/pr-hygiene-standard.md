# PR Hygiene Standard

<!-- summary -->
The PR Hygiene Standard governs the **shape of a code change**, separate from
the **shape of the resulting system** (MECE-3) or **the rules for reviewing
the change** (Code Review Standard). It is a synthesis of established
industry conventions — Google's CL practices, SmartBear's review research,
DORA's change-failure-rate findings, Squawk/Strong Migrations for schema
safety, Fowler's Expand-Contract pattern — into four primitives: **Scope,
Size, Safety, Completeness**. Each primitive is irreducible at the
PR-review level of analysis (different remediations) and individually
SUPPORTED by 3-4 independent sources; the four-primitive synthesis itself
is UNVALIDATED and in 90-day calibration. The standard's primary
consumer is `/code-review` via CR-09; it is designed to compose with any
future skill that touches PR-shape concerns.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-21)
> **Applies to:** Any Sulis-marketplace skill that produces or consumes a
> code change in pull-request form. Today: `/code-review` (SEA v0.14.0+).
> Designed for extension to `sulis-execution` PR-validation and any future
> PR-touching skill.

---

## Provenance

The four primitives synthesise five practitioner traditions. None of the
inputs alone constitutes a MECE framework; their combination here is a
novel structural arrangement specific to the Sulis marketplace.

| Source | Year | Contribution to this standard |
|---|---|---|
| **Google's public engineering practices** (`google/eng-practices`) | Ongoing | "Small CLs" (preferred <200 lines, hard ceiling at 400). "Single Responsibility CL" (one logical change). "Self-contained CL" (includes tests). → PH-01, PH-02, PH-04. |
| **SmartBear / Cisco code-review study** | 2006 | Review effectiveness drops sharply above 400 lines reviewed in one sitting. → PH-02. **Recency caveat: 20 years old; tooling and AI-assisted review may have shifted the threshold.** |
| **DORA metrics** (Forsgren / Humble / Kim, *Accelerate*) | 2018 | "Change failure rate" — small changes empirically correlate with lower failure rate. The outcome-level evidence base for size and scope discipline. → PH-01, PH-02. |
| **Squawk** (Stripe), **Strong Migrations** (Andrew Kane) | 2018-present | Allow-list / deny-list approach to risky migration patterns: locks on large tables, irreversible operations, missing indexes-not-concurrently. → PH-03. |
| **Expand-Contract pattern** (Martin Fowler, "ParallelChange") | 2014 | Schema changes split across multiple deploys: add new shape, migrate consumers, drop old shape. → PH-03. |
| **Conventional Commits 1.0.0** | 2017 | Type prefixes (feat/fix/refactor/...) implicitly encourage one type per commit/PR. → PH-01. |
| **Trunk-Based Development handbook** (Paul Hammant, DORA-endorsed) | Ongoing | Short-lived branches, small frequent integrations. → PH-02. |

The four primitives are an honest synthesis — no claim is made that
external literature has packaged them this way. The synthesis is itself a
Sulis-marketplace contribution analogous to MECE-3's synthesis of
Cockburn (hexagonal), Nygard (resilience), and OpenTelemetry
(observability).

---

## Counter-Evidence (BI-02 disclosure)

The case for strict PR-shape rules is not unanimous. Disclosed honestly so
readers can calibrate their adoption:

- **Facebook engineering practice** has historically tolerated very large
  diffs (often >5,000 lines) and ships them safely. Their experience
  challenges the "<400 lines or split" doctrine as universally true; they
  rely on tooling, infrastructure, and review process maturity that
  smaller teams may not have.
- **Microsoft research on PR review effectiveness** has identified contexts
  where larger PRs are reviewed effectively, particularly refactoring-heavy
  diffs reviewed with tooling assistance.
- **"Splitting theatre."** Strict PR-size enforcement can produce artificial
  splits that make the work *harder* to review because cohesion is lost
  across PRs. A 1000-line cohesive refactor may be more reviewable than
  five 200-line slices of the same refactor.
- **The SmartBear study is 20 years old.** Tooling, IDE assistance,
  AI-assisted code review, and team practices have evolved. The 400-line
  threshold is a starting point, not a law.

**Implication:** the size and scope thresholds in PH-02 and PH-01 are
**calibration starting points**, not bright-line gates. Teams calibrate to
their own context — tooling, review culture, risk appetite.

---

## Adversarial Comparison: Alternatives Considered (AT-01 disclosure)

Three structural alternatives were considered and explicitly rejected:

| Alternative | Why it might be right | Why rejected |
|---|---|---|
| **Extend MECE-3 to a fourth pillar (e.g., "Cadence")** | Keeps all change-concerns in one framework | Dilutes MECE-3's "destination" framing — MECE-3 is about the system as built, not the journey to get there. The architectural cohesion of MECE-3 is its main virtue; adding a fourth dimension weakens it. |
| **Fold change-risk into the Quality lens of `/code-review`** | No new standard; minimal surface | Conflates code quality with PR shape; does not compose to other skills (e.g., a future `/sulis-execution:pr-validate`); requires every consumer to re-derive the primitives. |
| **Distribute across existing standards** (EP for tests, GIT for size, RC for safety) | Uses existing homes | No single place to look when reviewing a PR; loses cohesion of the four-primitive synthesis; each home would have to grow its own incomplete change-shape vocabulary. |

The decisive criterion is **cohesion**: a dedicated standard gives any
PR-touching skill one place to consult. The alternative architectures all
fragment the change-shape concern across multiple homes.

---

## Boundary Definition

This standard governs **the artifact shape of a code change** — what the
diff itself looks like. It does **not** govern:

- **Process context** (timing of the deploy, author tenure, time-of-day risk).
  These are real risks but live in deployment-window standards, not PR-shape standards.
- **Code quality inside the diff** (correctness, naming, complexity).
  Handled by the Code Review Standard's Quality lens.
- **System architecture properties** (Form / Armor / Proof).
  Handled by MECE-3 and the Code Review Standard's Architecture lens.
- **Security primitives** (the 25-primitive viability framework).
  Handled by `sulis-security`.
- **Branching strategy and commit message format**.
  Handled by GIT-01..GIT-10.

This standard sits **between** the change being made and the review of it.
It runs before the lens work in `/code-review` because hygiene signals
inform how cautious the lens work needs to be.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block the consumer skill from declaring the change "reviewed". |
| **SHOULD** | Default. Deviation requires explicit justification recorded in the consumer skill's Methodology. |

---

## PH-01: Scope Discipline (MUST)

**Every PR governs one logical change.** Bundling unrelated concerns —
refactor + feature, refactor + dependency upgrade, infrastructure + product
code, two unrelated features — produces a Scope violation.

### Detection signals

- **Conventional Commit type spread:** if the PR's commits use more than
  one Conventional Commit type (e.g., `feat` and `refactor` and `chore`),
  this is a Scope smell to investigate. Not automatically a violation —
  honest follow-up commits (a feat with chores around it) may be legitimate.
- **Module fan-out without thematic coherence:** changes touching unrelated
  directories (`src/payments/` AND `src/notifications/` AND `infra/dns/`)
  in one PR are a Scope smell.
- **Mixed test:source ratio across directories:** test additions
  concentrated in one subsystem and source changes in another suggest
  bundling.

### Severity mapping

| Signal | Severity |
|---|---|
| 2 logical concerns bundled | **medium** |
| 3+ logical concerns bundled | **high** |
| Refactor mixed with feature in the same PR | **high** (the canonical anti-pattern; refactor diff drowns the feature) |

### Remediation

Recommend the author split the PR by concern. Each split PR carries its
own logical change.

### Source

Google "Single Responsibility CL"; Conventional Commits type-per-change
implication; widespread engineering vocabulary ("atomic PR", "one thing
per PR").

---

## PH-02: Size Discipline (MUST, with calibration)

**A PR should be reviewable in one sitting.** Size thresholds are
calibration starting points, not bright lines (see Counter-Evidence
section).

### Calibration starting points

| Diff size (lines added + lines removed) | Signal |
|---|---|
| ≤200 lines | **clean** — no signal |
| 201-500 lines | **note** — within Google's preferred range, may want a second reviewer |
| 501-1000 lines | **medium** concern — recommend deep review |
| 1001-2000 lines | **high** concern — recommend split or scheduled review session |
| 2001+ lines | **high** concern + recommend split as default; "intentional bulk" must be justified in PR description |

### Files-touched starting points

| Files touched | Signal |
|---|---|
| ≤5 files | clean |
| 6-15 files | note |
| 16-30 files | medium concern |
| 31-50 files | high concern |
| 51+ files | high concern + recommend split |

### Combined-threshold note

A PR can hit both size triggers (e.g., 1500 lines AND 40 files) — the
higher severity wins. A PR that hits only one trigger may still be
reviewable (a 5000-line generated-code-only diff that touches 2 files is
not really a 5000-line review).

### Exemptions (documented, not silent)

- **Generated code** (lock files, code-generation outputs, schema-derived
  types) contributes to line count but not to reviewer load. The hygiene
  finding cites the *human-authored* size separately when generated-code
  dominance is detected.
- **Refactor-only PRs** with strong mechanical tooling support (rename,
  extract, move) may legitimately exceed thresholds. The author justifies
  this in the PR description; the hygiene finding still records the size
  but downgrades severity.

### Remediation

Recommend split, or recommend scheduling a deep review session. Never
auto-blocks (advisory only — see PH-08 composition).

### Source

Google eng-practices (200 preferred, 400 ceiling); SmartBear / Cisco study
(recency-capped at 2006); DORA implication ("smaller changes = lower
change failure rate"); Trunk-Based Development doctrine.

---

## PH-03: Safety Discipline (MUST)

**High-risk surfaces are surfaced as separate observations, regardless of
total PR size.** A 50-line PR with one risky migration is a high-risk PR;
PH-02 says nothing about it.

### High-risk surfaces

| Surface | Detection | Why it's high-risk |
|---|---|---|
| **Database migrations** | Files in `migrations/`, `db/migrations/`, `prisma/migrations/`, `alembic/versions/`, `db/migrate/`, etc. | Schema changes are difficult to roll back; can lock tables; can break running production code if deploy is not atomic. |
| **Schema / IDL files** | `*.sql`, `*.proto`, `openapi.yaml`, `swagger.json`, `*.graphql`, `*.avsc` | Interface contracts — consumers must be updated in lockstep. Expand-Contract pattern applies. |
| **Secrets / credentials surfaces** | New environment-variable references, `*.env*` files, lines matching token-shaped patterns | Risk of accidental commit; risk of exposure. |
| **Infrastructure config** | `*.tf`, `*.tfvars`, Kubernetes manifests, Helm charts, `Dockerfile*`, `docker-compose*.yml`, CI workflow files (`.github/workflows/*.yml`, `.gitlab-ci.yml`) | Affects deploy and runtime topology; often hard to roll back. |
| **Lock files dominating the diff** | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `Gemfile.lock`, `poetry.lock`, `go.sum` constituting >50% of the diff | Hidden transitive upgrades; supply-chain risk. |

### Severity by signal

| Signal | Severity |
|---|---|
| 0 migrations in diff | clean |
| 1 migration | **note** — review reversibility |
| 2-3 migrations | **medium** — review ordering and atomicity |
| 4+ migrations | **high** — recommend split into per-migration PRs |
| Any schema/IDL change | **note** — verify consumer compatibility (Expand-Contract) |
| Any plaintext secret pattern | **high** — block (security; not really a hygiene call) |
| Any infra config change | **note** — verify deploy strategy |
| Lock-file >50% of diff | **note** — flag hidden upgrades |
| Migration + code in same PR | **medium** — verify backward compatibility (no atomic deploy in most systems) |

### Remediation

For migrations: review apply order, verify reversibility (Squawk / Strong
Migrations patterns), apply Expand-Contract for schema changes.

For schemas/IDLs: confirm all consumers updated or compatibility maintained.

For secrets: block; route through vault.

For infra: confirm deploy plan and rollback strategy.

For lock-file dominance: confirm intentional upgrade.

### Source

Squawk (Stripe Postgres migration linter); Strong Migrations (Andrew Kane,
Rails); Expand-Contract pattern (Fowler, 2014); DORA "change failure rate"
research; widespread industry convention on schema-change safety.

---

## PH-04: Completeness Discipline (MUST)

**Code, tests, and documentation ship together.** A diff that adds
production code without corresponding test additions is a Completeness
violation, even if every other primitive is clean.

### Detection signals

| Signal | Detection |
|---|---|
| **No tests for new source files** | Source files added in `src/` (or equivalent) with zero test files added in `tests/`, `__tests__/`, `*_test.*`, etc. |
| **Tests-only PR** | Test additions without source additions — usually fine (filling a gap), but flag for awareness. |
| **API change without OpenAPI/IDL update** | Endpoint added in code but no schema change. |
| **User-facing behaviour change without docs touch** | Reasonable heuristic: if `src/` changed and `README.md` / `docs/` is older than 30 days, note for review. (Not a violation — too many false positives — but a note.) |
| **Migration without corresponding code change** | Schema added but no application code uses it yet. Possibly Expand-Contract step 1 (legitimate); possibly orphan migration. Flag for awareness. |

### Severity mapping

| Signal | Severity |
|---|---|
| New source files added, 0 tests added | **medium** |
| New API endpoints, no schema update | **medium** |
| User-facing change, no docs touch in last 30 days | **note** |
| Orphan migration (no consumer code in same PR) | **note** (may be legitimate Expand-Contract) |

### Remediation

Request tests / schema / docs. For Expand-Contract patterns, confirm the
intent in the PR description.

### Source

Google "Self-contained CL"; universal industry convention ("tests included
with the change"); Expand-Contract for legitimate orphan-migration cases.

---

## PH-05: Severity Mapping for Hygiene Findings (MUST)

Hygiene findings carry the same severity vocabulary as code-review
findings (critical / high / medium / low / note) so they can be merged
into one report.

| Severity | Meaning in hygiene context |
|---|---|
| **critical** | Reserved — hygiene findings rarely reach critical. The one exception: plaintext secret detected in diff (PH-03), which is a security finding routed through `sulis-security` rather than hygiene. |
| **high** | Recommend split, recommend block-pending-clarification, or recommend deep-review session. Examples: 4+ migrations, 2001+ line PR, 3+ logical concerns bundled. |
| **medium** | Recommend changes before merge. Examples: 2-3 migrations, 501-2000 line PR, 2 concerns bundled, missing tests on new source. |
| **low / note** | Surface for awareness; no action required. Examples: 1 migration, 201-500 line PR, single concern with minor side touches. |

### Composition with code-review severity

Hygiene findings appear in a dedicated **PR Hygiene** section of the
report (per PH-08), separate from lens findings. Their severity feeds
the verdict computation in the consumer skill (e.g., CR-06 in
`/code-review`).

---

## PH-06: Computed Signals (MUST)

The hygiene check produces a **deterministic, structured signal set**.
Every consumer skill produces the same signal table, regardless of which
human reads the report.

| Signal | Source | Computation |
|---|---|---|
| `diff.lines_added` | `git diff --shortstat` | Integer |
| `diff.lines_removed` | `git diff --shortstat` | Integer |
| `diff.files_changed` | `git diff --name-only \| wc -l` | Integer |
| `diff.generated_ratio` | Detect via filename patterns (lock files, `*.pb.go`, generated suffix conventions) | Float (0.0–1.0) |
| `diff.lock_file_ratio` | Lines in lock-file paths / total lines | Float (0.0–1.0) |
| `scope.commit_type_spread` | Unique Conventional Commit types across the PR's commits | Set of strings |
| `scope.module_fan_out` | Distinct top-level directories touched | Integer |
| `scope.test_source_split` | Test-files dirs ∩ source-files dirs; 0 = disjoint (smell), >0 = co-located | Integer |
| `safety.migration_count` | Files matching migration-path patterns | Integer |
| `safety.schema_idl_count` | Files matching schema/IDL patterns | Integer |
| `safety.infra_files` | Files matching infra-config patterns | Integer |
| `safety.secret_pattern_hits` | Lines matching token-shaped patterns (Gitleaks rule subset) | Integer |
| `completeness.new_source_without_test` | Source files added with no corresponding test addition | Integer |
| `completeness.api_change_without_schema` | API/endpoint additions without IDL update | Boolean |

The consumer skill records this signal table in the report's hygiene
section verbatim. Downstream readers (humans, future skills) can recompute
the verdict from the signals.

---

## PH-07: Calibration Status and Threshold Authority (MUST)

This standard is in 90-day calibration from 2026-05-21. Per CC
(Confidence Calibration), the confidence tier disclosure:

| Element | Confidence tier | Evidence basis |
|---|---|---|
| **PH-01 Scope** | SUPPORTED | Google CL practice + Conventional Commits + universal engineering vocabulary |
| **PH-02 Size** | SUPPORTED (with recency caveat on SmartBear) | Google 200/400 + SmartBear 2006 + TBD doctrine + DORA implication |
| **PH-03 Safety** | SUPPORTED | Squawk + Strong Migrations + Expand-Contract + DORA "change failure rate" |
| **PH-04 Completeness** | EMERGING | Google "self-contained CL" + universal convention; less codified |
| **The four-primitive synthesis** | UNVALIDATED | Novel structural arrangement; no prior literature packages it this way |

### Threshold authority

Numeric thresholds in PH-02 and PH-03 are **calibration starting points**.
Teams may override per-project; the standard's job is to give a defensible
starting point, not to mandate the right answer for every codebase.

### Falsification criteria (FR-01..FR-04)

**We will STOP applying this standard if:**
- After 90 days of calibration, no hygiene finding has caught a real issue
  the Quality lens missed.
- The four primitives co-trigger >80% of the time in real reviews,
  suggesting they're not actually independent.

**We will PIVOT if:**
- One primitive proves consistently irrelevant (zero findings across 50+
  reviews).
- Teams uniformly override the size thresholds, suggesting the calibration
  starting points are wrong for this user population.

**We will RE-EVALUATE if:**
- A widely-adopted external framework emerges that subsumes this
  (e.g., a hypothetical "Conventional PRs" specification analogous to
  Conventional Commits).
- Anchor cases accrue showing systematic misses or false positives.

### Pre-mortem

If this standard fails, the most likely reasons are:

1. **Primitive overlap in practice.** Scope and Size co-trigger on most
   real misses (because big PRs almost always bundle concerns). If so,
   one primitive merges into the other.
2. **Threshold arbitrariness.** Teams find 200/400/etc. arbitrary and
   ignore them. If so, the standard becomes a tick-box.
3. **Computation reliability.** The agent cannot reliably compute
   mixed-concern detection or lock-file dominance across all language
   ecosystems. If so, the signal set in PH-06 shrinks.
4. **Friction-without-catch.** The standard surfaces noise more than
   real issues. If so, severity thresholds tighten.

---

## PH-08: Composition (MUST)

This standard is consumed by — does not replace — the consumer skill's
own framework. Composition contracts:

### With `/code-review` (SEA v0.14.0+)

`/code-review` applies this standard via **CR-09** of the Code Review
Standard. Hygiene findings appear in a **PR Hygiene** section of the
review report, distinct from lens findings. PH-03 `high` severity findings
trigger CR-06 verdict downgrade: minimum verdict `Request changes` when
PH-03 surfaces a high finding (e.g., 4+ migrations).

### With future PR-validation skills

Any future skill that validates a PR (e.g., a `sulis-execution`
pre-merge gate) consumes the same primitives. The signal table from PH-06
is the contract: a consumer reads the signal set, applies its own verdict
rubric, produces its own report.

### With `sulis-security`

Plaintext-secret detection in PH-03 hands off to `sulis-security:codebase-assess`
under SEC-07 / DAT-04. PH-03 reports the secret-pattern hit; the security
review owns the remediation.

### With MECE-3

Disjoint domains. MECE-3 governs the resulting system; PH governs the
shape of the change. A clean MECE-3 system can receive a PH-violating PR
and vice versa.

### With GIT-01..GIT-10

GIT-01..GIT-10 governs branching strategy and commit message format. PH
governs PR-artifact shape. Compatible — PH-01 (Scope) reads Conventional
Commit prefixes (a GIT-03 concern) as one detection signal.

### With Engineering Principles (EP-01..EP-08)

EP-02 (no implementation without failing test) and PH-04 (Completeness)
share the "tests included" concern. EP is about the developer's
discipline; PH-04 is about the artifact this discipline produces.
EP-02 violation typically implies PH-04 violation but not vice versa
(PH-04 also covers schema / docs completeness).

---

## Anchor Cases

Production cases accrue here. Each anchor names the date, repo, PR, which
primitives fired, and what the agent did with the signal.

### Anchor Case 1: PR-168 — the trigger feedback (2026-05-21)

**Repo:** `honestmobile/honest-smart-sim-platform`
**PR:** #168 (`feature/hon-431-manage-coupons-in-dashboard`)
**Diff:** 6,454 lines, 53 files, includes coupon-management feature.

**Hygiene signals (had the standard existed):**

| Primitive | Signal | Severity |
|---|---|---|
| PH-01 Scope | feature + refactor mixed (commit types include `feat`, `refactor`, `chore`); module fan-out across `apps/dashboard/`, `services/`, `infra/` | high |
| PH-02 Size | 6,454 lines / 53 files — both metrics above the "high" threshold | high |
| PH-03 Safety | Migration count: unknown at time of feedback; review noted "Number of migration files present in the PR should have been flagged" → migrations existed and were not flagged | high (assumed from feedback) |
| PH-04 Completeness | Tests included; no docs touch noted | medium |

**Outcome:** all four primitives would have fired on this PR. The feedback
that triggered this standard ("Number of migration files present in the PR
should have been flagged and is a missing indicator") is the PH-03 case
specifically; PH-01, PH-02, PH-04 all show the broader gap.

**Lesson:** the standard's value is not catching one signal — it's
producing the **structured set** of signals so a reviewer (human or agent)
sees the full shape of the change before reading any code.

---

## Worked Example: Signal Output for a Real PR

For a PR with 3 migrations, 1,200 lines across 18 files, mixed
feat+refactor commits, code without new tests:

```
PR Hygiene Signals
==================
Scope:
  commit_type_spread: {feat, refactor}        → smell
  module_fan_out: 4                            → smell
  severity: medium (2 concerns bundled)

Size:
  lines_added: 1043, lines_removed: 157, total: 1200
  files_changed: 18
  generated_ratio: 0.05
  lock_file_ratio: 0.02
  severity: medium (lines), medium (files)

Safety:
  migration_count: 3                           → medium concern
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: medium (review migration order + atomicity)

Completeness:
  new_source_without_test: 4                   → medium
  api_change_without_schema: false
  severity: medium

Overall: 4 findings (1 medium-Scope, 1 medium-Size, 1 medium-Safety, 1 medium-Completeness)
Suggested action: Request changes — see hygiene findings 1-4
```

---

## Linguistic Audit (NH compliance)

This standard avoids:
- Superlatives without metrics ("comprehensive", "best", "most effective")
- Prohibited terms ("revolutionary", "disruptive", "game-changing", etc.)
- Volume-based claims without source ("everyone agrees…")

Every numeric threshold cites a primary source or is explicitly marked as
a calibration starting point.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-21 | Initial standard. PH-01..PH-08 synthesised from Google eng-practices, SmartBear (with recency caveat), DORA, Squawk, Strong Migrations, Expand-Contract, Conventional Commits, Trunk-Based Development. CTS analysis pre-flight passed (MECE, PG, BI counter-evidence, FR falsification, CC tier disclosure, AT adversarial alternatives, OI outside-in direction). Anchor case PR-168. 90-day calibration begins. |
