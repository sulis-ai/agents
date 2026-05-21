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
  findings only — hygiene findings are author recommendations). Advisory
  only — never posts to the PR, never sets status checks, never blocks merge.
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

1. A merged report at `.architecture/{project}/code-reviews/PR-{number}-{YYYY-MM-DD}.md`
   that satisfies CR-01..CR-08.
2. Draft Hardening Deltas under `.architecture/{project}/hardening-deltas/`
   for accepted findings, with `source: code-review:PR-NNN` and
   `lens: architecture | security | quality`.
3. A short conversational summary of the top findings — strip internal IDs,
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

### 13. Write the report

See structure below. Methodology section appears with the CR-08
self-attestation checklist filled in.

### 14. Summarise to the user (FE-01..FE-11 MUST)

Walk through the top 3-5 findings conversationally — **not** the full
report. The report is the persistent artifact; the conversation is for
the human to understand what matters.

In the summary:
- Strip internal IDs (HD-NNN, CR-NN, Form/Armor/Proof, SEC-NN, etc.).
- Use plain language. Translate "MECE-3 Armor gap" → "missing timeout";
  translate "CR-01 finding" → "the compiler caught X".
- Lead with the merge-blocking findings (if any), then exposures, then
  hygiene.
- End with: *"Report at `.architecture/{project}/code-reviews/...`. Verdict:
  {verdict}. {N} draft fixes ready. Hand to `/sea:harden` to implement."*

---

## Report Format

Write to `.architecture/{project}/code-reviews/PR-{number}-{YYYY-MM-DD}.md`.

```markdown
# Code Review: PR-{number} — {title}

> **Date:** YYYY-MM-DD
> **Author:** {author}
> **Base:** {baseRef} → **Head:** {headRef}
> **Files changed:** N (+ N neighbours)
> **Verdict:** {Block / Request changes / Approve with fixes / PASS}

## Summary

- **Build Verification:** {N} PR-introduced errors (CR-01)
- **PR Hygiene:** {N} findings ({N} high — split recommended, {N} medium, {N} note) (CR-09 / PH-01..PH-04)
- **In the changes:** {N} findings ({N} critical, {N} high, {N} medium, {N} low)
- **In the neighbours:** {N} findings (downgraded one severity per CR-05)
- **Draft fixes:** {N} (lens findings only — hygiene findings are author recommendations, not deltas)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | N | N | New domain → infrastructure import in `src/orders/...` |
| Security | N | N | Hardcoded Stripe key in `src/config/...` |
| Quality | N | N | New handler missing tests |

## Build Verification (CR-01)

{Each PR-introduced typecheck/lint error becomes a critical (quality) finding here. File:line, quoted error, recommended fix. Empty section shows "No PR-introduced errors detected. Commands run: <list>."}

### `apps/dashboard/app/coupons/page.tsx:264` — critical (quality)

**Error:** `TS2304: Cannot find name 'hasMore'.`

**Quoted text:**
```typescript
{loading ? "Loading..." : `${codes.length}${hasMore ? "+" : ""} code${codes.length === 1 ? "" : "s"} shown`}
```

**Why it matters:** `hasMore` is a type-annotation field on the response shape (line 113), never destructured or stored in state. Build fails under `--strict`; runtime throws `ReferenceError` on every render.

**Recommendation:** Destructure `hasMore` from the response and store in state alongside `codes` and `total`.

**Draft fix:** HD-019 — "Declare hasMore as runtime variable in coupons page"

---

## PR Hygiene (CR-09 — applies PH-01..PH-08)

### Signal table (PH-06)

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

### Findings

{Each hygiene primitive with severity, signal, and recommendation. Hygiene findings are author recommendations — they do NOT produce Hardening Deltas. Lens findings remain the source of deltas.}

#### PH-03 Safety — medium: 3 migrations in this PR

**Signal:** `safety.migration_count = 3` — exceeds the "single migration" threshold; within the "review ordering" band.

**Why it matters:** Multiple schema changes deployed atomically increase rollback complexity. Apply order matters; running code mid-deploy may see an intermediate state.

**Recommendation:** Confirm migrations are designed to apply in any order, OR enforce a strict apply order in the deploy plan. Verify Expand-Contract was applied if any consumer changes are paired with the schema. Consider splitting into per-migration PRs if not.

---

## Findings in the Changes

{Critical and high first. Each finding: file:line, quoted text, recommendation, draft delta ID, lens.}

## Findings in the Neighbours

{Pre-existing gaps the PR touched but didn't introduce. Downgraded severity per CR-05. No draft deltas — listed for awareness.}

## Watch List

{Theoretical gaps with no failing-test grounding (CR-04 incomplete). No deltas. Just notes.}

## Cross-Reference

- **Existing Hardening Deltas covered:** {list IDs}
- **Existing security report:** {path if exists}
- **Pattern suggesting full audit:** {one bullet per neighbour pattern that suggests a broader gap}

## Methodology

### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p apps/dashboard`; `npx eslint <changed>`. Base: 0 errors. Head: 1 new error (see Build Verification). Coverage gap: none.
- [✓] **CR-02 Parallel dispatch used.** Three lenses dispatched concurrently. Diff: {N} lines / {N} files ({above carve-out threshold | within carve-out — single-reader justified}).
- [✓] **CR-03 Full-file reads.** All {N} changed files >50 lines read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line and quoted text.
- [✓] **CR-05 Severity rubric.** Applied. {N} critical, {N} high, {N} medium, {N} low.
- [✓] **CR-06 Verdict computed.** Verdict: {value}. Auto-downgrade triggers: {list any that fired, e.g. "CR-01 Build Verification non-empty → minimum Block"}.
- [✓] **CR-07 Lens completion.** Architecture: {N} findings + scan log. Security: {N findings | "nothing surfaced"} + scan log. Quality: {N findings} + jsx-ident-scan.log + dead-surface + contract-drift + test-coverage observation.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: {severity} ({signal summary}). PH-02 Size: {severity} ({N} lines / {N} files). PH-03 Safety: {severity} ({migrations: N, schemas: N, secrets: N, infra: N}). PH-04 Completeness: {severity} ({signal summary}). PH-03 high → CR-06 auto-downgrade fired: {yes/no, with reason}.

### Run details

- **Diff source:** {gh pr / git diff range}
- **Neighbour expansion:** {ast-grep | git grep | probe output}
- **Neighbour cap:** {N of N considered, N excluded due to 20-file cap}
- **Scanners run:** {gitleaks, trivy, semgrep, ...}
- **Scanners unavailable:** {list — explains coverage gaps}
- **Lenses dispatched in parallel:** yes ({wall-clock seconds})
```

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
