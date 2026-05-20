---
name: code-review
description: >
  Use when reviewing a pull request, branch, or commit range. Runs three
  reviews in one pass — architectural (Form / Armor / Proof gaps),
  security (secrets, injection, dependency CVEs, headers), and general code
  quality — then merges findings into a single report under
  `.architecture/{project}/code-reviews/`. Draft fixes are emitted as
  Hardening Deltas the author can hand to `/sea:harden` to implement.
  Does not block merge — it advises.
---

# Code Review — Three Lenses, One Report

When invoked, take a target (PR number, branch ref, or commit range) and run
**three reviews in parallel**:

1. **Architectural** — Form / Armor / Proof gaps the changes introduce or expose.
2. **Security** — the relevant subset of the 25-primitive viability assessment, scoped to the diff.
3. **General quality** — code correctness, readability, test coverage on the diff itself.

Merge the findings into a single report at
`.architecture/{project}/code-reviews/PR-{number}-{YYYY-MM-DD}.md` and draft
Hardening Deltas for the fixes. Do **not** post comments on the PR, do **not**
set status checks, do **not** block merge. The report is advisory — the author
or reviewer decides what to act on.

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

## Scope

You look at **two rings** of code:

| Ring | What it covers | Why |
|---|---|---|
| **The changes** | Every line in the diff | Gaps the PR introduces directly — these are the ones the author can fix before merge. |
| **The neighbours** | Code that calls into the changes, code the changes call into, modules sharing imports with changed files | Gaps the PR exposes by integrating with existing code — surfaced but never grounds to block merge. |

You do **not** scan beyond the neighbours. If a neighbour finding points at a
gap that pervades the codebase, surface it once with the note
*"recommend full `/sea:codebase-audit` to size the broader gap"* — don't
list every site.

**Neighbour cap: 20 files.** When the diff touches widely-imported utility
code, the neighbour ring can explode. When it does, narrow to the 20 most
strongly-coupled files and note the cap in the report's Methodology.

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

### 2. Expand to neighbours

For each changed file, find direct callers and callees of the symbols the
diff touched. Tools, in order of preference:

| Tool available | Use it for |
|---|---|
| `ast-grep` | Symbol-precise caller/callee discovery |
| `gh pr diff` + `git grep` | Fast string-based caller scan when ast-grep is unavailable |
| Probe output at `.architecture/{project}/CODE_INTELLIGENCE.html` | Pre-computed import graph; avoid recomputing |

Cap at 20 files. Record the expansion in the report.

### 3. Run the three reviews in parallel

Use the Agent tool to dispatch three reviewers concurrently against the
resolved diff + neighbour set. Each returns a list of findings.

#### Architectural review (Form / Armor / Proof)

Apply the gap-type checklist from
[`../codebase-audit/SKILL.md`](../codebase-audit/SKILL.md). Most relevant
to a PR:

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

#### Security review (diff-scoped viability assessment)

Invoke `/sulis-security:codebase-assess` in "Quick" mode — Cycle 1 + Cycle 2
only, scoped to the diff. Focus categories: **SEC** (access control, auth,
injection, validation, XSS, SSRF, secrets exposure) and **SC** (dependency
CVEs). Other categories run if signals are present in the diff (e.g. new
Dockerfile → INF-01; new logging call → DAT-03).

Pass `--scope=diff` semantics by limiting Gitleaks / Semgrep / Trivy to the
changed file paths plus the neighbour ring.

#### General quality review

Built-in code review concerns scoped to the diff:

- Correctness — obvious bugs in changed lines
- Readability — naming, complexity, comment quality
- Test coverage — does the diff include tests for new behaviour?
- Style consistency with surrounding code
- Dead code, unused imports, TODO/FIXME density introduced

This lens is intentionally lighter-weight than the architectural and
security lenses — it's checking the *changes themselves*, not the system.

### 4. Score severity

Same rubric across all three lenses:

- `critical` — security flaw exploitable now, or correctness bug that breaks production
- `high` — production incident probable within 90 days
- `medium` — operational pain or test gap
- `low` — drift that has not yet caused failure

Findings in **the changes** can be any severity. Findings in **the neighbours**
are downgraded one notch (a neighbour `critical` becomes `high` in the report)
because the PR didn't introduce them — it exposed them.

### 5. Merge findings

Deduplicate across the three lenses — a hardcoded secret in the diff will be
flagged by both the security and architectural lenses. Keep one entry; cite
both lenses as evidence sources.

### 6. Draft Hardening Deltas

One logical change per delta file under
`.architecture/{project}/hardening-deltas/`. Mark provenance:

```yaml
source: code-review:PR-142
lens: security        # or "architecture" or "quality"
```

Each delta references a failing characterisation test that proves the gap.
If you cannot construct that test, drop the delta — theoretical gaps belong
in the report's "Watch List" section, not in the delta queue.

### 7. Write the report

See structure below.

### 8. Cross-reference siblings

- If `.security/{project}/viability-report-*.md` exists from a prior
  `sulis-security:codebase-assess` run, cite findings instead of restating.
- If `.architecture/{project}/hardening-deltas/` already has accepted deltas
  covering findings in this PR, cite the existing delta ID instead of
  drafting a duplicate.

### 9. Summarise to the user

Walk through the top 3-5 findings conversationally — **not** the full report.
The report is the persistent artifact; the conversation is for the human to
understand what matters.

In the summary:
- Strip internal IDs (HD-NNN, Form/Armor/Proof, SEC-NN, etc.)
- Use plain language: "structure", "resilience", "verification" — or just
  describe the gap directly
- Lead with the merge-blocking findings (if any), then exposures, then
  hygiene
- End with: *"Report at `.architecture/{project}/code-reviews/...`. {N}
  draft fixes ready. Hand to `/sea:harden` to implement."*

---

## Report Format

Write to `.architecture/{project}/code-reviews/PR-{number}-{YYYY-MM-DD}.md`.

```markdown
# Code Review: PR-{number} — {title}

> **Date:** YYYY-MM-DD
> **Author:** {author}
> **Base:** {baseRef} → **Head:** {headRef}
> **Files changed:** N (+ N neighbours)
> **Lenses run:** architecture, security, quality

## Summary

- **In the changes:** {N} findings ({N} critical, {N} high, {N} medium, {N} low)
- **In the neighbours:** {N} findings (all downgraded by one severity)
- **Draft fixes:** {N}
- **Suggested action:** {Block / Request changes / Approve with fixes / Approve}

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | N | N | New domain → infrastructure import in `src/orders/...` |
| Security | N | N | Hardcoded Stripe key in `src/config/...` |
| Quality | N | N | New handler missing tests |

## Findings in the Changes

{Critical and high first. Each finding has file:line, evidence, recommendation, draft delta ID, originating lens.}

### `src/payments/stripe-client.ts:42` — high (architecture)

**Gap:** New `fetch(stripeUrl)` call has no timeout, no retry policy, no circuit breaker.

**Why it matters:** Stripe outages happen. An unbounded fetch blocks the request thread for ~75s on Linux, starving the request pool.

**Recommendation:** Wrap in the project's existing resilience policy at `src/lib/http-client.ts`.

**Draft fix:** HD-018 — "Add timeout + circuit breaker to Stripe client"

---

## Findings in the Neighbours

{Pre-existing gaps the PR touched but didn't introduce. Downgraded severity. No draft deltas — listed for awareness.}

## Watch List

{Theoretical gaps with no failing-test grounding. No deltas. Just notes.}

## Cross-Reference

- **Existing Hardening Deltas covered:** {list IDs}
- **Existing security report:** {path if exists}
- **Pattern suggesting full audit:** {one bullet per neighbour pattern that suggests a broader gap}

## Methodology

- **Diff source:** {gh pr / git diff range}
- **Neighbour expansion:** {ast-grep | git grep | probe output}
- **Neighbour cap:** {N of N considered, N excluded due to 20-file cap}
- **Tools run:** {gitleaks, trivy, semgrep, ...}
- **Tools unavailable:** {list — explains coverage gaps}
- **Lenses run in parallel:** yes ({wall-clock seconds})
```

---

## Depth modes

- **Quick** ("smoke check before approve") — changes only (no neighbour ring), severity `high`+ only, architectural + security lenses only. ~5 minutes.
- **Standard** (default) — changes + neighbours (20-file cap), all severities, all three lenses, draft fixes.
- **Deep** ("this PR touches load-bearing code") — changes + neighbours (no cap), all three lenses, recommend full `/sea:codebase-audit` afterwards.

---

## Composition

- **With `/sulis-security:codebase-assess`** — `/code-review` invokes it in Quick mode internally. If a full security audit already exists, cite findings instead of re-running.
- **With `/sea:harden`** — the draft fixes this skill produces are handed to `/sea:harden` if the user accepts them. Provenance preserved via `source: code-review:PR-NNN`.
- **With `/sea:codebase-audit`** — when neighbour-ring patterns suggest a broader gap, recommend the full audit. Don't try to do its job.

---

## Gotchas

- **No auto-blocking.** This skill never sets a status check, never posts to the PR, never enforces. It reports. Branch protection and human reviewers own the gate.
- **Neighbour findings never block.** A finding in pre-existing code the PR merely touched isn't grounds to block merge. Surface it as exposure, not as introduction.
- **One-hop can explode on utility changes.** When a PR touches `lib/logger.ts` or similar, every file is a neighbour. The 20-file cap exists for this reason — narrow to highest-coupling files and note the cap explicitly.
- **Severity is operational, not aesthetic.** Don't inflate findings to drive attention. `medium` is real; not every PR finding is `high`.
- **Test discipline still applies.** A draft fix without a failing characterisation test is theoretical. Drop it to the Watch List.
- **Speak plain in the summary.** The PR author may not be the architect. Strip internal IDs. Translate "MECE-3 Armor gap" to "missing timeout"; translate "SEC-07 finding" to "API key exposed in code".
- **Don't double-count across lenses.** A hardcoded secret will be flagged by both security and architecture. Merge into one finding; cite both lenses as evidence.

---

## See Also

- [`../codebase-audit/SKILL.md`](../codebase-audit/SKILL.md) — full-repo architectural audit (same gap types, broader scope)
- [`../harden/SKILL.md`](../harden/SKILL.md) — implementing accepted fixes
- [`../../references/hardening-deltas.md`](../../references/hardening-deltas.md) — fix file format and `source:` field schema
- [`../../references/mece-3-architecture.md`](../../references/mece-3-architecture.md) — the three architectural lenses
- [`../../references/red-green-blue.md`](../../references/red-green-blue.md) — characterisation-test discipline
- `plugins/sulis-security/skills/codebase-assess/SKILL.md` — the security lens this skill invokes
