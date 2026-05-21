---
name: code-review
description: >
  Use when reviewing a pull request, branch, or commit range. Implements the
  Code Review Standard (CR-01..CR-09) at
  `../../references/code-review-standard.md` and applies the PR Hygiene
  Standard (PH-01..PH-08) at `plugins/srd/references/pr-hygiene-standard.md`.
  Runs a mandatory mechanical baseline (typecheck + lint) before any lens
  (CR-01); computes the PR Hygiene signal table — Scope / Size / Safety /
  Completeness — before lens dispatch (CR-09); dispatches three lenses in
  parallel — architectural (Form / Armor / Proof gaps), security
  (diff-scoped viability assessment), and general code quality with
  procedural checks (CR-02, CR-07). Reads every changed file >50 lines
  end-to-end (CR-03). Findings cite file:line + quoted text (CR-04). Severity
  is rubric-driven (CR-05); verdict is computed with four auto-downgrade
  rules including PH-03 high findings (CR-06). Self-attestation in the
  report's Methodology section (CR-08). Outputs a single merged report at
  `.architecture/{project}/code-reviews/` plus draft Hardening Deltas (lens
  findings only — hygiene findings are author recommendations). The report
  is **two-tier**: a plain-English author tier first (no internal IDs, no
  jargon, action-oriented severity labels, optional "Things to take away"
  for educational notes tied to specific findings) and a technical tier
  below for engineers and downstream agents (full CR-NN / PH-NN taxonomy,
  signal tables, self-attestation). Default audience for tier 1 is a
  non-technical founder using AI to generate code; tier 2 is unchanged.
  Advisory only — never posts to the PR, never sets status checks, never
  blocks merge.
---

# Code Review — Three Lenses, Mechanical Floor, One Report

This skill is the implementation of the **Code Review Standard** at
[`../../references/code-review-standard.md`](../../references/code-review-standard.md).
Every workflow step below traces to one or more CR-01..CR-08 rules. Read the
standard first — it defines what a complete code-review report must
contain, how findings must be evidenced, how severity and verdict are
assigned, and how the reviewing agent attests to its own coverage.

When invoked, take a target (PR number, branch ref, or commit range) and
produce:

1. A self-contained review bundle at `.architecture/{project}/code-reviews/PR-{number}-{YYYY-MM-DDTHHMMSSZ}/` containing:
   - `REVIEW.md` — the report
   - `hardening-deltas/HD-NNN-*.md` — draft fixes produced by this review
   - `signals.json` — the PH-06 signal table in machine-readable form
   - `tool-outputs/` — raw outputs from typecheck, lint, scanners (when produced)

   The bundle satisfies CR-01..CR-09. Draft Hardening Deltas inside the
   bundle carry `source: code-review:PR-NNN` and `lens: architecture |
   security | quality`. `/sea:harden` discovers them recursively under
   `.architecture/{project}/` and only implements those whose status is
   `accepted` — the bundle holds drafts at status `proposed` until you
   accept them.

2. A short conversational summary of the top findings — strip internal IDs,
   speak founder English (FE-01..FE-11).

Do **not** post comments on the PR, do **not** set status checks, do **not**
block merge. The report is advisory.

---

## Input

| Parameter | Required | Description |
|---|---|---|
| `target` | Yes | PR number (`142`), branch ref (`feat/payments`), or commit range (`main..HEAD`) |
| `project-name` | No | Output folder under `.architecture/`. Defaults to working-directory basename |

**Example invocations:**

```
/code-review 142
/code-review feat/payments
/code-review main..HEAD
/code-review 142 acme
```

If the target is a number and `gh` is available, treat it as a GitHub PR
and pull metadata. Otherwise resolve from local git.

If arguments are missing, ask the user — do not invent.

---

## Scope — Two Rings

You look at **two rings** of code:

| Ring | What it covers | Why |
|---|---|---|
| **The changes** | Every line in the diff | Gaps the PR introduces directly. Findings here carry full severity (CR-05). |
| **The neighbours** | Code that calls into the changes, code the changes call into, modules sharing imports with changed files | Gaps the PR exposes by integrating with existing code. Findings here are downgraded one severity notch (CR-05); `low` neighbour findings are dropped. |

You do **not** scan beyond the neighbours. If a neighbour finding points at a
gap that pervades the codebase, surface it once with the note
*"recommend full `/sea:codebase-audit` to size the broader gap"* — don't
list every site.

**Neighbour cap: 20 files.** When the diff touches widely-imported utility
code, the neighbour ring can explode. When it does, narrow to the 20 most
strongly-coupled files and note the cap in Methodology.

---

## Workflow

### 1. Resolve the diff

```bash
WORK="/tmp/code-review/{project}-$(date +%s)"
mkdir -p "$WORK"

if command -v gh >/dev/null && [[ "$TARGET" =~ ^[0-9]+$ ]]; then
  gh pr view "$TARGET" --json number,title,baseRefName,headRefName,author,files \
    > "$WORK/pr-meta.json"
  gh pr diff "$TARGET" > "$WORK/diff.patch"
  BASE=$(jq -r .baseRefName "$WORK/pr-meta.json")
  HEAD=$(jq -r .headRefName "$WORK/pr-meta.json")
fi

git diff --name-only "$BASE...$HEAD" > "$WORK/changed-files.txt"
git diff "$BASE...$HEAD" > "$WORK/diff.patch"
```

Capture diff size (lines + file count) for the CR-02 carve-out decision.

### 2. Mechanical baseline (CR-01 MUST — before any lens runs)

Run the project's typechecker and linter on **both** `BASE` and `HEAD`,
diff the outputs, surface PR-introduced errors. Detection commands per the
CR-01 table:

| Language signal | Commands to run |
|---|---|
| `tsconfig.json` exists | `npx tsc --noEmit` |
| `.eslintrc*` exists | `npx eslint <changed-files>` |
| `pyproject.toml` with mypy/pyright/ruff config | the configured one |
| `go.mod` exists | `go build ./...` then `go vet ./...` |
| `Cargo.toml` exists | `cargo check` |
| `package.json` has `typecheck`/`lint` scripts | prefer those |

Multiple language signals → run all applicable checks.

```bash
# BASE run
git checkout "$BASE"
$PROJECT_CHECK_CMD > "$WORK/typecheck-base.log" 2>&1 || true

# HEAD run
git checkout "$HEAD"
$PROJECT_CHECK_CMD > "$WORK/typecheck-head.log" 2>&1 || true

# Delta — only errors absent on BASE and present on HEAD are PR-introduced
diff "$WORK/typecheck-base.log" "$WORK/typecheck-head.log" \
  | grep '^> ' > "$WORK/typecheck-delta.log"
```

For monorepos with slow typecheckers, scope to the changed app/package
(`tsc --noEmit -p apps/<changed-app>`) rather than the workspace root. Note
the scope in Methodology.

**If no check command is detectable**, record a coverage gap in Methodology
with the reason. Do not skip silently. Per CR-01, the coverage-gap entry is
the visible mark of an unverified mechanical floor.

**Outcome.** Every PR-introduced error from `typecheck-delta.log` becomes a
`critical (quality)` finding in the report's **Build Verification** section,
which appears above all lens findings. Per CR-06, this section non-empty →
verdict cannot be `PASS`.

### 3. PR Hygiene check (CR-09 MUST — before lens dispatch)

Apply the **PR Hygiene Standard** at
`plugins/srd/references/pr-hygiene-standard.md` (PH-01..PH-08). Compute
the PH-06 signal table from the diff:

```bash
# Diff metrics (PH-02)
git diff --shortstat "$BASE...$HEAD" > "$WORK/diff-shortstat.txt"
git diff --name-only "$BASE...$HEAD" | wc -l > "$WORK/files-changed.txt"

# Scope signals (PH-01) — Conventional Commit type spread + module fan-out
git log --format='%s' "$BASE..$HEAD" \
  | grep -oE '^[a-z]+(\([^)]+\))?:' \
  | sort -u > "$WORK/commit-types.txt"
git diff --name-only "$BASE...$HEAD" \
  | awk -F/ '{print $1}' | sort -u > "$WORK/top-dirs.txt"

# Safety signals (PH-03)
git diff --name-only "$BASE...$HEAD" \
  | grep -E '(migrations?/|db/migrate/|alembic/versions/|prisma/migrations/)' \
  > "$WORK/migrations.txt"
git diff --name-only "$BASE...$HEAD" \
  | grep -iE '\.(sql|proto|graphql|avsc)$|openapi\.(ya?ml|json)|swagger\.json' \
  > "$WORK/schema-files.txt"
git diff --name-only "$BASE...$HEAD" \
  | grep -E '(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|Gemfile\.lock|poetry\.lock|go\.sum)' \
  > "$WORK/lock-files.txt"
git diff --name-only "$BASE...$HEAD" \
  | grep -iE '(\.tf$|\.tfvars$|Dockerfile|docker-compose|k8s/|kubernetes/|\.github/workflows/|\.gitlab-ci)' \
  > "$WORK/infra-files.txt"

# Completeness signals (PH-04)
git diff --name-only --diff-filter=A "$BASE...$HEAD" \
  | grep -vE '(test|spec|__tests__)' > "$WORK/new-source.txt"
git diff --name-only --diff-filter=A "$BASE...$HEAD" \
  | grep -E '(test|spec|__tests__)' > "$WORK/new-tests.txt"
```

Apply the severity rubric from PH-01..PH-04. Produce the **PR Hygiene**
section of the report between Build Verification and the lens findings.

**Hygiene-informed dispatch (interaction with CR-02).** When hygiene
severity is `high` on any primitive, the lens work runs with extra
conservatism: severity scoring tilts toward higher rather than lower,
neighbour ring expansion is more eager. The hygiene severity is recorded
in Methodology.

**Auto-downgrade trigger.** PH-03 `high` finding (4+ migrations,
plaintext secret pattern, etc.) feeds CR-06 auto-downgrade rule 4 →
minimum verdict `Request changes`. Record the trigger in Methodology.

**Hygiene findings do not produce Hardening Deltas.** Per CR-09 in the
Code Review Standard, hygiene findings are recommendations to the PR
author (split, add tests, review migration order) — not deltas. Lens
findings still produce deltas as before.

### 4. Decide the dispatch shape (CR-02 MUST)

| Diff size | Dispatch shape |
|---|---|
| ≤200 lines **AND** ≤5 files | Single-reader pass permitted. Record in Methodology: *"Single-reader pass justified by diff size: N lines, M files."* |
| >200 lines **OR** >5 files | **Parallel dispatch required.** No exceptions. Reading the diff yourself in place of dispatching is forbidden. |

The carve-out is a size limit, not a budget choice. Above the threshold, the
agent **must** dispatch the three lenses concurrently as sub-agents via the
Agent tool — it cannot decline.

### 5. Expand to neighbours

For each changed file, find direct callers and callees of the symbols the
diff touched. Tools, in order of preference:

| Tool available | Use it for |
|---|---|
| `ast-grep` | Symbol-precise caller/callee discovery |
| `gh pr diff` + `git grep` | Fast string-based caller scan when ast-grep is unavailable |
| Probe output at `.architecture/{project}/CODE_INTELLIGENCE.html` | Pre-computed import graph; avoid recomputing |

Cap at 20 files. Record the expansion (which files, which excluded, why) in
Methodology.

### 6. Run the three lenses (CR-07 MUST produce structured output per lens)

Each lens reads every changed file >50 lines **end-to-end** (CR-03 — sampling
forbidden). Each lens produces structured output before claiming "complete";
a lens that surfaced no findings emits an explicit *"nothing surfaced. Checks
run: …"* entry — never silence.

#### Architecture lens

Apply the gap-type checklist from
[`../codebase-audit/SKILL.md`](../codebase-audit/SKILL.md). Each finding is
tagged with the HD-02 gap type from `references/hardening-deltas.md`
(`dependency-direction`, `timeout`, `circuit-breaker`, `secrets`,
`observability`, `contract-test`, etc.). Most relevant to a PR:

**Structure (Form)**
- New code that imports from `infrastructure/`, `db/`, `http/` into domain
- Newly added module-level singletons or `getInstance()` accessors
- New circular import paths
- New cross-module reach-through into `internal/`

**Resilience (Armor)**
- New HTTP/RPC/DB calls with no explicit timeout
- New retries with no backoff/jitter; retries on non-idempotent operations without idempotency keys
- New external calls with no circuit breaker
- Hardcoded credentials, API keys, or secrets in the diff
- New service-to-service calls over plain HTTP
- New handlers/operations missing OpenTelemetry spans
- New log statements without `trace_id`
- New endpoints with no RED/USE metrics
- PII or token-shaped strings newly visible in logs/traces

**Verification (Proof)**
- New ports with no contract test
- New adapter tests that don't share a contract test with the in-memory adapter
- New integration tests using mocks instead of real adapters/testcontainers
- New resiliency primitives (CB, timeout, retry) with no chaos test

**Completion output:** list of findings tagged with HD-02 gap type, OR
explicit *"Architecture lens: nothing surfaced. Checks run: …"*.

#### Security lens (CR-07 — must produce structured output)

Invoke `/sulis-security:codebase-assess` in "Quick" mode — Cycle 1 + Cycle 2
only, scoped to the diff plus neighbour ring. Findings against the 25
primitives at `plugins/sulis-security/skills/codebase-assess/references/primitives.md`,
filtered to those applicable.

Focus categories: **SEC** (access control, auth, injection, validation, XSS,
SSRF, secrets exposure) and **SC** (dependency CVEs). Other categories run
if signals are present in the diff (new Dockerfile → INF-01; new logging
call → DAT-03).

**Completion output:** list of findings keyed by primitive ID, OR explicit
*"Security lens: nothing surfaced. Primitives checked: SEC-01..07, SC-01..04, INF-04. Scanners run: Gitleaks, Semgrep, Trivy."*.

#### Quality lens (CR-07 — must produce all six outputs)

Runs after the CR-01 mechanical baseline. Reads every changed file
end-to-end (CR-03). Produces **all** of:

1. **Build Verification follow-up.** For every CR-01 finding, a translated
   entry with file:line, quoted text, recommended fix. Don't restate raw
   typecheck output.
2. **JSX / template identifier scan.** For every TSX/JSX/Vue/Svelte file
   in the diff, grep for `{identifier}` and `${identifier}` patterns
   introduced by the diff; verify each identifier is in lexical scope.
   Save to `$WORK/jsx-ident-scan.log`. Catches the PR-168 class of bug
   (`hasMore` referenced in JSX but never declared) regardless of TS
   strictness.

   ```bash
   for f in $(grep -lE '\.(tsx|jsx|vue|svelte)$' "$WORK/changed-files.txt"); do
     # Extract identifier references the diff introduced
     git diff "$BASE...$HEAD" -- "$f" \
       | grep '^+' \
       | grep -oE '\{[a-zA-Z_][a-zA-Z0-9_]*\}|\$\{[a-zA-Z_][a-zA-Z0-9_]*\}' \
       >> "$WORK/jsx-ident-scan.log"
   done
   # Then verify each identifier resolves in the file's lexical scope.
   ```

3. **Dead-surface findings.** Unused props/state/exports, unreferenced
   imports, JSDoc contracts the code doesn't honour.
4. **Contract-drift findings.** Enum/union values the implementation never
   emits, DTO fields the service never sets, response shapes whose consumer
   assumes more than the producer provides.
5. **Test-coverage observation.** Does the diff include tests for new
   behaviour? A source-only diff with no tests is a finding.
6. **Style / readability** — naming, complexity, comments, TODO/FIXME
   density. Lowest priority; come last. May be empty without blocking
   completion.

A quality lens missing any of items 1–5 is **incomplete** — return to the
step that produced the gap.

### 7. Score severity (CR-05 MUST — objective conditions, not vibes)

Severity by condition, not vibes:

| Severity | Triggering conditions (any one is sufficient) |
|---|---|
| **critical** | Exploitable security flaw now (hardcoded production credential, missing authz on data-mutating endpoint, injection vector). OR correctness bug breaks production (build/typecheck error, runtime crash on golden-path render, data corruption). |
| **high** | Production incident probable within 90 days (unbounded external call on hot path, missing circuit breaker on payment provider, race condition under documented load). |
| **medium** | Operational pain or test gap (missing observability on handler, mock-based integration test, dead surface, contract drift). |
| **low** | Drift that has not yet caused failure (naming, complexity in non-hot code, comments, TODO density). |

**Ring downgrade.** Findings in the diff carry full severity. Findings in
the neighbour ring are downgraded one notch (neighbour `critical` →
`high`); neighbour `low` is dropped entirely.

Do not inflate severity to drive attention. `medium` is real.

### 8. Merge findings across lenses

Deduplicate — a hardcoded secret will surface in both security and
architecture lenses. Keep one entry; cite all lenses as evidence sources in
the finding's `lens:` field (e.g., `lens: security + architecture`).

### 9. Compute the verdict (CR-06 MUST — agent cannot override)

Verdict is **computed**, not chosen:

| Verdict | Conditions |
|---|---|
| **PASS** | No critical/high in diff AND Build Verification empty AND every file >50 lines was read end-to-end AND all three lenses produced output. |
| **Approve with fixes** | Only medium/low in diff. No merge-blockers. All CR-01/03/07 floors satisfied. |
| **Request changes** | At least one `high` in the diff. |
| **Block** | At least one `critical` in the diff, OR Build Verification non-empty, OR any file >50 lines not read end-to-end. |

**Auto-downgrade rules — agent cannot override:**

1. Build Verification non-empty → minimum verdict `Block`.
2. Any file >50 lines not read end-to-end → minimum verdict `Request changes`.
3. Any lens produced no output (literal silence, not "nothing surfaced") →
   minimum verdict `Request changes`.
4. PR Hygiene Standard PH-03 `high` finding (4+ migrations, plaintext
   secret pattern, etc.) → minimum verdict `Request changes`.

### 10. Self-attestation (CR-08 MUST — before report write)

Write the Methodology section with the CR-01..CR-09 checklist before
proceeding to the report body. Each box is `[✓]`, `[✗]`, or `[—]` with a
one-line reason.

If any box claims `[✓]` without a reason, the report is malformed —
regenerate.

If any box is `[✗]`, the corresponding verdict downgrade per CR-06 applies.

### 11. Draft Hardening Deltas

One logical change per delta under `.architecture/{project}/hardening-deltas/`.
Provenance:

```yaml
source: code-review:PR-142
lens: security                # or "architecture" or "quality" or "security + architecture"
```

Per CR-04, each delta references a failing characterisation test. If you
cannot construct it, drop the delta — theoretical gaps belong in the
report's **Watch List**, not in the delta queue.

### 12. Cross-reference sibling artifacts

- `.security/{project}/viability-report-*.md` from prior
  `sulis-security:codebase-assess` runs → cite findings instead of restating.
- `.architecture/{project}/hardening-deltas/` accepted deltas → cite existing
  delta ID instead of drafting a duplicate.

### 13. Write the report (two tiers — author first, technical detail second)

The report has **two tiers in one file**, written for two readers (see
"Report Format — Two Tiers" below).

**Tier 1 (top of file) — for the author.** The person who opened this
pull request reads this. They may be a non-technical founder using AI to
generate code, or a developer learning the codebase. The tier 1 sections
are: At a glance / What to fix / How this pull request is shaped /
Things to take away (optional).

Tier 1 writing discipline:
- No internal IDs (`CR-NN`, `PH-NN`, `HD-NNN`, etc.).
- Translate engineer jargon. "Circuit breaker" → "a back-up plan when the
  other service is slow or down". "Timeout" → "a maximum wait time".
- Use the severity/verdict translation table in the Report Format section.
- Recommendations cite a pattern in the codebase by file path when one exists.
- "Things to take away" is optional — omit if the PR is clean. At most 3
  lessons; tied to specific findings in *this* PR. Acknowledge difficulty;
  don't open with "next time".

**Tier 2 (below `## Technical detail` heading) — for engineers and downstream
agents.** Current report structure intact — CR-NN, PH-NN, signal tables,
self-attestation. This is what `/sea:harden` and future `/code-review`
runs read.

The author tier writes itself from the same finding set as the technical
tier — same data, different audience.

### 14. Summarise to the user (FE-01..FE-11 MUST — short, the report does the work)

Because the report's Tier 1 is now founder-readable on its own, the chat
summary is short — a pointer plus the single most important thing the
author should do next.

**Standard shape (3-4 sentences):**

> Reviewed your pull request. {Outcome in plain English — Ready to merge / Approve, but apply small fixes first / Needs changes before merge / Don't merge yet.}
>
> {The single most important thing to look at, in one sentence — without restating the report.}
>
> Full review at `.architecture/{project}/code-reviews/PR-{number}-{YYYY-MM-DDTHHMMSSZ}/REVIEW.md`. {If draft fixes were queued: "N draft fixes are ready in the review's `hardening-deltas/` folder — run `/sea:harden` to apply them when you're ready."}

**Examples**

Clean PR:

> Reviewed your pull request. **Ready to merge.** No build errors, well-scoped, tests included. Full review at `.architecture/acme/code-reviews/PR-142-2026-05-21T143052Z/REVIEW.md`.

Problem PR:

> Reviewed your pull request. **Don't merge yet.** The build is failing — there's a variable referenced in the coupons page that was never actually declared, so the page would crash. Full review at `.architecture/acme/code-reviews/PR-168-2026-05-21T091200Z/REVIEW.md`. Two draft fixes are ready in the review's `hardening-deltas/` folder — run `/sea:harden` to apply them.

**Anti-patterns** (MUST NOT in the chat summary):

- Walking through every finding (the report already does this)
- Using internal IDs (`CR-NN`, `PH-NN`, `HD-NNN`)
- Saying "applied the Code Review Standard" or naming the rules
- Asking "want me to do X?" when the report already states what to do

---

## Report Format — Two Tiers

The report is **two tiers in one file**, written for two different readers:

| Tier | Reader | What they need |
|---|---|---|
| **Tier 1 — For the author** | The person who opened the pull request (often a non-technical founder) | Plain English. What's wrong, why it matters, what to do, what to take away. No internal IDs (CR-NN, PH-NN, HD-NNN), no engineer jargon. |
| **Tier 2 — Technical detail** | Engineers reviewing the PR, downstream agents (`/sea:harden`, future runs of `/code-review`) | Internal taxonomy intact (CR-NN, PH-NN, etc.), signal tables, self-attestation, full evidence trail. |

Tier 1 comes first. Tier 2 sits below a clear `## Technical detail` heading so the founder reading top-to-bottom can stop naturally when they've understood what's needed.

The translation table for severity and verdict, used in Tier 1:

| Internal (CR-05 / CR-06) | Tier 1 plain English |
|---|---|
| Verdict `PASS` | **Ready to merge** |
| Verdict `Approve with fixes` | **Approve, but apply small fixes first** |
| Verdict `Request changes` | **Needs changes before merge** |
| Verdict `Block` | **Don't merge yet** |
| Severity `critical` | **Must fix** |
| Severity `high` | **Strongly recommend fixing** |
| Severity `medium` | **Worth fixing** |
| Severity `low` / `note` | **Minor — for awareness** |

Write the bundle to `.architecture/{project}/code-reviews/PR-{number}-{TIMESTAMP}/` where `TIMESTAMP` is an ISO 8601 UTC timestamp generated at report-write time. This prevents same-day rerun collisions (e.g., reviewing the same PR twice in one morning).

```bash
TIMESTAMP=$(date -u +%Y-%m-%dT%H%M%SZ)
# Produces: 2026-05-21T143052Z

BUNDLE_DIR=".architecture/${PROJECT}/code-reviews/PR-${PR_NUMBER}-${TIMESTAMP}"
mkdir -p "${BUNDLE_DIR}/hardening-deltas" "${BUNDLE_DIR}/tool-outputs"
# REVIEW.md     → the report
# hardening-deltas/HD-NNN-*.md → draft fixes (status: proposed)
# signals.json  → PH-06 signal table, machine-readable
# tool-outputs/ → raw typecheck/lint/scanner outputs (when produced)
```

### Bundle layout

```
.architecture/{project}/code-reviews/PR-{number}-{TIMESTAMP}/
├── REVIEW.md                       ← the report (Tier 1 + Tier 2)
├── hardening-deltas/
│   ├── INDEX.md                    ← drafts produced by this review
│   ├── HD-018-add-timeout-stripe.md
│   └── HD-019-declare-hasMore.md
├── signals.json                    ← PH-06 signal table
└── tool-outputs/                   ← raw scanner / typecheck outputs
    ├── typecheck-base.log
    ├── typecheck-head.log
    ├── jsx-ident-scan.log
    └── ...
```

Self-contained: reading any one bundle tells the full story of that
review. `/sea:harden` finds the deltas because it scans
`.architecture/{project}/` recursively for `HD-*.md`. Drafts ship at
`status: proposed`; promoting to `status: accepted` in the delta's
frontmatter is what tells `/sea:harden` to implement them.

```markdown
# Code Review: PR-{number} — {title}

> **Timestamp:** YYYY-MM-DDTHHMMSSZ (ISO 8601 UTC)
> **Author:** {author}
> **Branch:** {headRef} → {baseRef}
> **Files changed:** N
>
> **Outcome:** {Ready to merge / Approve, but apply small fixes first / Needs changes before merge / Don't merge yet}

---

## At a glance

{Two to four sentences in plain English. What's the state of this pull request? What's the single most important thing to look at? If there's nothing serious, say so — don't manufacture concern.}

Example for a clean PR:
> Your pull request looks good. There are no build errors and the changes are well-scoped. Two small things to consider before merge — see "What to fix" below.

Example for a problem PR:
> This pull request introduces a build error that would crash the coupons page when it loads. It also covers a lot of ground — 6,454 lines across 53 files including 3 database migrations and a refactor mixed with the new feature. Recommend fixing the build error first, then thinking about whether the refactor and migrations could move into their own pull requests.

## What to fix

{Plain-English findings, ordered by severity. Each finding has three parts:
- **What's happening** — plain language, no jargon. Quote the offending code if useful.
- **Why it matters** — concrete consequences for the founder's product or users. Avoid "best practice" framing; say what could actually go wrong.
- **What to do** — specific next step. If a fix pattern exists in the codebase, point to it by file path. If a draft fix is queued, mention it can be applied with `/sea:harden`.

Order: must-fix first, then strongly-recommend, then worth-fixing. Skip minor/awareness items here — they go below.

If nothing to fix, this section says: "No issues that need attention." Done.}

### Must fix — `apps/dashboard/app/coupons/page.tsx`, line 264

**What's happening:** Your code is trying to use a value called `hasMore` that was never actually stored anywhere. It's declared as part of the *type* of the data coming back from the API, but the code never pulls it out into a variable it can use.

**Why it matters:** The build will fail (TypeScript catches this). If it somehow got past the build, the page would crash with "hasMore is not defined" every time someone loaded it.

**What to do:** When the response comes back from the API, pull `hasMore` out alongside `codes` and `total`. The pattern is on line 113 — you've already declared the shape, you just need to use it: `const { data, total, hasMore } = body`. A draft fix is queued — run `/sea:harden HD-019` to apply it.

### Strongly recommend fixing — `src/payments/stripe-client.ts`, line 42

**What's happening:** You added code that calls Stripe (the payment service) without any protection if Stripe is slow or down.

**Why it matters:** Stripe has outages — they had three significant ones in 2025. When that happens, your code will hang waiting for a response. New users trying to do things on your app see the app freeze, sometimes for over a minute, because nothing stops the wait.

**What to do:** The codebase has a pattern for this at `src/lib/http-client.ts` — it has built-in protections that give up after 5 seconds and stop trying if Stripe seems broken. Wrap the `fetch(stripeUrl)` call using that helper. A draft fix is queued as HD-018.

## How this pull request is shaped

{The PR Hygiene findings translated into plain English. Skip categories that are clean. Use observations, not commandments. Acknowledge difficulty where it's real (e.g., big end-to-end PRs).}

**Size — strongly recommend looking at**

Your pull request is large — 6,454 lines across 53 files. This is a common pattern when you're building an end-to-end feature for the first time, and it's not always obvious how to split it as you go. The hygiene check flagged this because large pull requests are harder for any reviewer (human or AI) to thoroughly check, so bugs are easier to miss.

**Scope — worth looking at**

Your changes include both new-feature work (`feat:` commits) and refactoring (`refactor:` commits). When something goes wrong later, it's harder to debug if a single pull request did two different things. The two types of change have different risk profiles — refactors shouldn't change behaviour, features do.

**Safety — strongly recommend looking at**

There are 3 database migrations in this pull request. Database migrations change the shape of your data — they can lock tables, take time to run on large datasets, and are harder to undo than code changes. With 3 migrations bundled, the order matters and a problem in any one of them affects the whole deploy.

**Completeness — worth looking at**

You added 4 new source files and 0 new test files. Tests are how the codebase protects against future changes breaking the thing you just built. Without tests, the next person to change this code (which may be you, six months from now) has no safety net.

## Things to take away

{Maximum 3 lessons. Often 1 is enough. Tied to specific findings in *this* PR, not generic lessons. Acknowledge what got done. Phrase as observations, not commandments. If the PR is well-shaped and clean, omit this section entirely — silent is better than condescending.

Anti-condescension rules:
- Don't open with "next time". Acknowledge first.
- Don't lecture about basics the PR already does well.
- If two findings would teach the same lesson, pick one and teach it once.
- Don't include this section if there's nothing specific to take away.}

1. **You built one big pull request covering several changes at once** — a new feature, a refactor, and 3 database migrations. You're not the first; this is a common pattern when you're building an end-to-end solution and it's not obvious where to split. A technique that helps next time: as soon as you finish a piece that stands on its own — a database migration, a refactor that doesn't change behaviour, a new shared utility — open a separate pull request for just that piece and merge it before building the rest on top.

2. **The build error here came from declaring a TypeScript type but forgetting to use the value.** Easy to miss when you're focused on the feature. A useful habit: after you add a new field to an API response, search the file you're going to display it in for the field name — make sure the code actually pulls it out of the response, not just declares it should be there.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sea:harden`. The author tier above contains everything the PR author needs to act.

### Verdict

`{Block / Request changes / Approve with fixes / PASS}` per CR-06.

### Summary

- **Build Verification:** {N} PR-introduced errors (CR-01)
- **PR Hygiene:** {N} findings ({N} high, {N} medium, {N} note) (CR-09 / PH-01..PH-04)
- **In the changes:** {N} findings ({N} critical, {N} high, {N} medium, {N} low)
- **In the neighbours:** {N} findings (downgraded one severity per CR-05)
- **Draft fixes:** {N} (lens findings only — hygiene findings are author recommendations, not deltas)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | N | N | New domain → infrastructure import in `src/orders/...` |
| Security | N | N | Hardcoded Stripe key in `src/config/...` |
| Quality | N | N | New handler missing tests |

### Build Verification (CR-01)

#### `apps/dashboard/app/coupons/page.tsx:264` — critical (quality)

**Error:** `TS2304: Cannot find name 'hasMore'.`

**Quoted text:**
```typescript
{loading ? "Loading..." : `${codes.length}${hasMore ? "+" : ""} code${codes.length === 1 ? "" : "s"} shown`}
```

**Why it matters:** `hasMore` is a type-annotation field on the response shape (line 113), never destructured or stored in state. Build fails under `--strict`; runtime throws `ReferenceError` on every render.

**Recommendation:** Destructure `hasMore` from the response and store in state alongside `codes` and `total`.

**Draft fix:** HD-019 — "Declare hasMore as runtime variable in coupons page"

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat, refactor}        → smell
  module_fan_out: 4 distinct top-level dirs    → smell
  severity: medium (2 concerns bundled)

Size (PH-02):
  lines_added: 1043, lines_removed: 157, total: 1200
  files_changed: 18
  generated_ratio: 0.05
  lock_file_ratio: 0.02
  severity: medium (501-1000 line band; 16-30 file band)

Safety (PH-03):
  migration_count: 3                           → medium concern
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: medium (review migration order + atomicity)

Completeness (PH-04):
  new_source_without_test: 4                   → medium
  api_change_without_schema: false
  severity: medium
```

### Findings in the Changes

{Critical and high first. Each finding: file:line, quoted text, recommendation, draft delta ID, lens.}

### Findings in the Neighbours

{Pre-existing gaps the PR touched but didn't introduce. Downgraded severity per CR-05. No draft deltas — listed for awareness.}

### Watch List

{Theoretical gaps with no failing-test grounding (CR-04 incomplete). No deltas. Just notes.}

### Cross-Reference

- **Existing Hardening Deltas covered:** {list IDs}
- **Existing security report:** {path if exists}
- **Pattern suggesting full audit:** {one bullet per neighbour pattern that suggests a broader gap}

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p apps/dashboard`; `npx eslint <changed>`. Base: 0 errors. Head: 1 new error (see Build Verification). Coverage gap: none.
- [✓] **CR-02 Parallel dispatch used.** Three lenses dispatched concurrently. Diff: {N} lines / {N} files ({above carve-out threshold | within carve-out — single-reader justified}).
- [✓] **CR-03 Full-file reads.** All {N} changed files >50 lines read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line and quoted text.
- [✓] **CR-05 Severity rubric.** Applied. {N} critical, {N} high, {N} medium, {N} low.
- [✓] **CR-06 Verdict computed.** Verdict: {value}. Auto-downgrade triggers: {list any that fired, e.g. "CR-01 Build Verification non-empty → minimum Block"}.
- [✓] **CR-07 Lens completion.** Architecture: {N} findings + scan log. Security: {N findings | "nothing surfaced"} + scan log. Quality: {N findings} + jsx-ident-scan.log + dead-surface + contract-drift + test-coverage observation.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: {severity} ({signal summary}). PH-02 Size: {severity} ({N} lines / {N} files). PH-03 Safety: {severity} ({migrations: N, schemas: N, secrets: N, infra: N}). PH-04 Completeness: {severity} ({signal summary}). PH-03 high → CR-06 auto-downgrade fired: {yes/no, with reason}.

#### Run details

- **Diff source:** {gh pr / git diff range}
- **Neighbour expansion:** {ast-grep | git grep | probe output}
- **Neighbour cap:** {N of N considered, N excluded due to 20-file cap}
- **Scanners run:** {gitleaks, trivy, semgrep, ...}
- **Scanners unavailable:** {list — explains coverage gaps}
- **Lenses dispatched in parallel:** yes ({wall-clock seconds})
```

### Tier 1 writing rules (MUST)

When writing the author-facing tier:

1. **No internal IDs.** No `CR-NN`, `PH-NN`, `HD-NNN`, `SEC-NN`, `MECE-3`, `Form/Armor/Proof`. These belong below the `## Technical detail` heading.
2. **Translate engineer jargon to plain language.** "Circuit breaker" → "a back-up plan when the other service is slow or down". "Timeout" → "a maximum wait time". "Resilience policy" → "a pattern that protects against the external service breaking". "Migration" stays as is (it's the right name for it) but the *consequence* is explained.
3. **Recommendations cite a pattern in the codebase by file path when one exists**, not a doctrine. "See `src/lib/http-client.ts` for the project's pattern" is better than "use the resilience policy pattern."
4. **Use the severity / verdict translation table** above. Don't say `critical` in Tier 1 — say "Must fix".
5. **The "Things to take away" section is optional** — omit when there's nothing specific. Don't manufacture lessons.
6. **Acknowledge difficulty.** Big PRs, mixed-scope PRs, missing tests — name them as common patterns first, then offer a technique. Don't open with the criticism.

### Tier 1 anti-patterns (MUST NOT)

- Opening any Tier 1 sentence with "Per CR-01...", "Following the PR Hygiene Standard...", "Per FE-06..."
- Listing the same lesson in "Things to take away" two reports in a row (assume the author already heard it)
- Writing "Things to take away" when the PR is clean — silence is the right call
- Treating all PRs as opportunities to teach. Most PRs need correction, not curriculum.
- Condescension in any form. The author shipped working code (or tried to). Acknowledge what got done before pointing at what could be different.

---

## Depth modes

- **Quick** ("smoke check before approve") — CR-01 mechanical baseline + architecture + security lenses only, severity `high`+ only. CR-02 carve-out path. ~5 minutes.
- **Standard** (default) — full CR-01..CR-09 compliance, all three lenses, all severities, draft fixes, PR Hygiene signal table.
- **Deep** ("this PR touches load-bearing code") — Standard + no neighbour cap, recommend full `/sea:codebase-audit` afterwards.

---

## Composition

- **With the Code Review Standard** — every workflow step traces to a
  CR-NN rule. When the standard changes, this skill changes with it.
- **With the PR Hygiene Standard** — CR-09 applies PH-01..PH-08. Hygiene
  findings inform lens severity scoring and feed the CR-06 verdict
  auto-downgrade for PH-03 high findings. When PH thresholds calibrate
  (per PH-07), this skill picks them up by reference.
- **With `/sulis-security:codebase-assess`** — invoked in Quick mode internally
  for the security lens. If a full security audit already exists in
  `.security/{project}/`, cite it instead of re-running.
- **With `/sea:harden`** — draft fixes produced here are handed to
  `/sea:harden` if accepted. Provenance preserved via
  `source: code-review:PR-NNN`. **Hygiene findings do not produce deltas**
  — they are author recommendations (split, add tests, review migration
  order).
- **With `/sea:codebase-audit`** — when neighbour-ring patterns suggest a
  broader gap, recommend the full audit. Don't try to do its job.

---

## Gotchas

- **CR-01 is non-negotiable.** Skipping the mechanical baseline because
  "the agent already read the file" is the failure mode this skill exists
  to prevent. The cheapest tooling has to run first; agent judgement sits
  on top of it.
- **CR-02 carve-out is a size limit, not a budget.** Above 200 lines or 5
  files, parallel dispatch is required. Single-reader is forbidden even
  if the agent feels confident.
- **CR-03 forbids sampling.** Reading lines 1-100 of a 344-line file is
  not coverage. Per CR-06 auto-downgrade, the verdict cannot be PASS if
  any file >50 lines was sampled.
- **CR-06 verdict is computed, not chosen.** The agent declares findings;
  the verdict follows from the findings + the auto-downgrade rules. The
  agent cannot say "looks fine" when the compiler disagrees.
- **CR-08 self-attestation cannot be silent.** A report missing the
  Methodology checklist is malformed. Regenerate.
- **No PR comments, no status checks, no auto-blocking.** The skill never
  posts to the PR, never sets status, never enforces. Branch protection
  and human reviewers own the gate.
- **Neighbour findings never block.** A finding in pre-existing code the
  PR merely touched isn't grounds to block merge. Surface as exposure,
  not as introduction.
- **One-hop can explode on utility changes.** When a PR touches
  `lib/logger.ts` or similar, every file is a neighbour. The 20-file cap
  exists for this reason — narrow to highest-coupling files and note the
  cap in Methodology.
- **The author tier of the report is founder-readable. The technical tier
  below is not.** When a finding lives in Tier 1, it cannot use internal IDs,
  cannot reference standards by code, and cannot use unexplained engineer
  jargon. When the same finding appears in Tier 2, IDs and taxonomy are
  expected. The same evidence, two writeups.
- **"Things to take away" stays small or stays silent.** Three lessons max.
  Often one is enough. If the PR is clean, omit the section entirely. The
  goal is helping the author learn over time, not turning every review into
  a tutorial. Silence beats condescension.
- **Acknowledge difficulty before pointing at improvements.** A 6,000-line PR
  is usually a sign of someone building end-to-end for the first time, not
  carelessness. Naming the pattern as common takes the sting out of the
  finding and makes the advice land.
- **Founder English on the conversational summary.** Strip internal IDs.
  Translate `CR-NN`, `HD-NNN`, `MECE-3`, `Form/Armor/Proof` to plain
  language for the chat surface; the report Methodology section is for
  the technical reader and may carry the rule IDs verbatim.
- **Test discipline applies to draft fixes.** A delta without a failing
  characterisation test is theoretical. Move to Watch List, drop from
  the delta queue.

---

## See Also

- [`../../references/code-review-standard.md`](../../references/code-review-standard.md) — **the standard this skill implements** (CR-01..CR-09, anchor cases, calibration)
- `plugins/srd/references/pr-hygiene-standard.md` — **PR Hygiene Standard** (PH-01..PH-08) applied via CR-09; Scope / Size / Safety / Completeness primitives + computed signal table
- [`../codebase-audit/SKILL.md`](../codebase-audit/SKILL.md) — full-repo architectural audit (same gap types, broader scope)
- [`../harden/SKILL.md`](../harden/SKILL.md) — implementing accepted fixes
- [`../../references/hardening-deltas.md`](../../references/hardening-deltas.md) — fix file format and `source:` field schema
- [`../../references/mece-3-architecture.md`](../../references/mece-3-architecture.md) — the three architectural lenses
- [`../../references/red-green-blue.md`](../../references/red-green-blue.md) — characterisation-test discipline
- `plugins/sulis-security/skills/codebase-assess/SKILL.md` — the security lens this skill invokes
