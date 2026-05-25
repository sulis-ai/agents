# Code Review Standard

<!-- summary -->
The Code Review Standard defines what a complete Sulis code-review report
must contain, how every finding must be evidenced, how severity and verdict
are assigned, and how the reviewing agent attests to its own coverage. It
exists because agent judgement alone is unreliable on the cheapest class of
defects — the build-breaker a free linter catches in seconds. CR-01..CR-08
make mechanical floors mandatory, make lens dispatch enforceable, and force
the agent to attest to coverage before the report is written. Applies to
`/code-review` today; designed to apply to any future skill that produces a
code-review report.
<!-- /summary -->

> **Version:** 0.2.0
> **Status:** Active — Calibration Period (90 days from 2026-05-20; CR-10 calibration window starts 2026-05-22)
> **Applies to:** `/code-review` (SEA v0.13.0+). Designed for extension to any future
> code-review-producing skill in the marketplace.

---

## Provenance

A production session against `honestmobile/honest-smart-sim-platform#168`
(2026-05-20) exposed the gap. A 6,454-line / 53-file PR was reviewed by
`/code-review`; the report produced 11 findings across architecture,
security, and quality lenses, none of which was the build-breaking
TypeScript error in the diff (`hasMore` referenced in JSX but never
declared as a runtime variable). A free GitHub bot caught the same bug in
seconds using `tsc --noEmit`.

Two failure modes contributed: an operator failure (the agent collapsed
the three parallel lenses into a single self-read pass and only read the
first 100 lines of the file containing the bug), and a plugin failure (the
skill's SKILL.md made mechanical checks optional, parallel dispatch
permissive, and the quality lens vibes-based with no procedural definition
or coverage gate).

The four edits in `plugins/sulis/skills/code-review/BUG_REPORT.md` patched
the specific failure. This standard generalises the lesson: agent judgement
is unreliable on the cheapest defects; mechanical tooling is the floor;
the skill must demonstrably catch *more* than the cheap tool, not less.

Practitioner knowledge from production agent operation.

---

## Boundary Definition

This standard governs **what a code-review report must contain and how its
findings must be evidenced**. It does not govern:

- The specific scanners / typecheckers / linters used (those belong in the
  skill's tool-commands reference).
- The diff-resolution and neighbour-expansion mechanics (those belong in the
  skill itself).
- The Hardening Delta format produced from accepted findings (handled by
  `references/hardening-deltas.md`, HD-01..HD-NN).
- The Red-Green-Blue implementation of accepted findings (handled by
  `references/red-green-blue.md`).
- Whether `/code-review` posts to a PR, sets status checks, or auto-merges
  (it does not — that boundary is fixed in the skill, not this standard).

This standard sits between the skill and the report. It runs *before* the
report is written, deciding whether the review was thorough enough to
produce one.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block the report from being written; the agent must return to the corresponding step. |
| **SHOULD** | Default. Deviation requires explicit justification recorded in Methodology. |

---

## CR-01: Mechanical Baseline Before Any Lens (MUST)

Before any lens runs, the reviewing agent runs the project's own type-checker
and linter on **both** `BASE` and `HEAD`, diffs the outputs, and surfaces
PR-introduced errors as a dedicated **Build Verification** section at the
top of the report — above all lens findings.

PR-introduced errors are errors present on `HEAD` and absent on `BASE`.
Errors present on both sides are pre-existing and out of scope.

### Detection

| Language signal | Commands to run |
|---|---|
| `tsconfig.json` exists | `npx tsc --noEmit` |
| `.eslintrc*` exists | `npx eslint <changed-files>` |
| `pyproject.toml` with `mypy` / `pyright` / `ruff` config | the configured one |
| `go.mod` exists | `go build ./...` then `go vet ./...` |
| `Cargo.toml` exists | `cargo check` |
| Project `package.json` has `typecheck` / `lint` scripts | prefer those |

Multiple language signals → run all applicable checks.

### When detection fails

If no check command is detectable, this is a **coverage gap** — not a pass.
Document the gap explicitly in Methodology with the reason. Do not skip
silently.

### Verdict implication

Every PR-introduced error becomes a `critical (quality)` finding under
**Build Verification**. Per CR-06, the report's verdict cannot be `PASS`
when Build Verification contains any finding — agent judgement cannot
override this.

### Cost note

For monorepos with slow typecheckers, scope to the changed app/package
(`tsc --noEmit -p apps/<changed-app>`) rather than the workspace root.
Document the scope in Methodology.

---

## CR-02: Mandatory Parallel Lens Dispatch (MUST with carve-out)

The three lenses — **architecture**, **security**, **quality** — run
concurrently as separate sub-agent dispatches. The reviewing agent does
**not** read the diff itself and substitute that for the lens dispatch.

### Why

No single reader reliably holds architectural, security, and line-level
quality concerns in attention simultaneously, especially on diffs over a
few hundred lines. The single-reader collapse is the failure mode that
produced the PR-168 miss.

### Carve-out for tiny diffs

A single-reader pass is permitted **only** when **both**:

- The diff is ≤200 lines (sum of `+` and `−`), **and**
- The diff touches ≤5 files.

If both conditions hold, the agent may run the three lenses as one
sequential pass. The choice must be recorded in Methodology:

> *"Single-reader pass justified by diff size: N lines, M files."*

For diffs above either threshold, parallel dispatch is required regardless
of agent confidence. The carve-out is not a budget choice — it is a size
limit.

---

## CR-03: Full-File Reads for Changed Files >50 Lines (MUST)

Every changed file longer than 50 lines is read **end-to-end** at least
once during the review — either by a lens sub-agent or by the reviewing
agent in the CR-02 carve-out case.

Sampling — reading the first N lines, or the regions around the diff hunks
— is forbidden. The PR-168 miss happened because the agent read lines 1–100
of a 344-line file and considered it covered; the bug was at line 264.

### Files ≤50 lines

May be read in full or sampled, at the lens's discretion. (Files this small
fit in one screen — full read is almost always cheaper than sampling.)

### Verdict implication

Per CR-06, if any changed file >50 lines was not read end-to-end, the verdict
cannot be `PASS`. The Methodology must list the unread files explicitly so
the reader can see what was skipped.

---

## CR-04: Evidence Discipline — File:Line + Quoted Text (MUST)

Every finding cites **both**:

1. A file path and line number (`apps/dashboard/app/coupons/page.tsx:264`)
2. A direct quote of the offending text (a code snippet, log entry, header
   value — whatever the finding is about)

Findings missing either piece are excluded from the report. They do not
appear in the count, do not contribute to severity, and do not produce a
Hardening Delta.

### Why both

The file:line lets the reader navigate; the quoted text lets the reader
verify the agent actually saw the thing it claims to have seen. Either alone
is insufficient — a file:line without a quote is an unverifiable claim; a
quote without a file:line is an ungrouped observation.

### Anti-pattern

> *"I noticed unused code in dialog.tsx"* — not a finding.

> *"`Props.schemes` declared at `dialog.tsx:36` but never read in the
> component body"* — finding.

---

## CR-05: Severity Rubric With Objective Conditions (MUST)

Severity is assigned by **conditions**, not by vibes. Four levels:

| Severity | Triggering conditions (any one is sufficient) |
|---|---|
| **critical** | Exploitable security flaw now (hardcoded production credential, missing authz on data-mutating endpoint, injection vector on user input). OR correctness bug that breaks production (build/typecheck error, runtime crash on the golden-path render, data corruption). |
| **high** | Production incident probable within 90 days (unbounded external call on a hot path, missing circuit breaker on a payment provider, race condition under documented load, missing rate limit on a password-reset endpoint). |
| **medium** | Operational pain or test gap (missing observability on a handler, mock-based integration test where a real adapter exists, dead surface — unused props/state/exports, contract drift — enum/union with unreachable values). |
| **low** | Drift that has not yet caused failure (naming, complexity in non-hot code, comment quality, TODO/FIXME density introduced). |

### Ring downgrade

Findings in the diff itself carry full severity. Findings in the neighbour
ring (pre-existing code the diff merely touched) are downgraded one notch:
a neighbour `critical` becomes `high`; a neighbour `low` is dropped entirely.

The PR did not introduce the neighbour gap — it merely exposed it. The PR
author should not be blocked on it.

### Anti-inflation

Severity is operational, not aesthetic. Do not inflate to drive attention.
A `medium` is a real finding. Not every PR finding is `high`.

---

## CR-06: Verdict Rubric With Auto-Downgrade Rules (MUST)

The report's verdict is **computed**, not chosen by the agent. Four values:

| Verdict | Conditions |
|---|---|
| **PASS** | No critical or high findings in the diff AND Build Verification (CR-01) shows no PR-introduced errors AND every changed file >50 lines was read end-to-end (CR-03) AND all three lenses produced output (CR-07). |
| **Approve with fixes** | Only medium and low findings in the diff. No merge-blockers. All CR-01/03/07 floors satisfied. |
| **Request changes** | At least one `high` finding in the diff. |
| **Block** | At least one `critical` finding in the diff, OR Build Verification contains any PR-introduced error, OR any changed file >50 lines was not read end-to-end. |

### Auto-downgrade rules (MUST)

The reviewing agent **cannot** override these:

1. **Build Verification has findings → verdict cannot be PASS.** Minimum
   verdict: `Block`. (Mechanical failure beats agent confidence.)
2. **Any file >50 lines not read end-to-end → verdict cannot be PASS.**
   Minimum verdict: `Request changes`. (Coverage gap blocks the highest
   verdict.)
3. **Any lens produced no output (not "nothing surfaced" — *no output*) →
   verdict cannot be PASS.** Minimum verdict: `Request changes`. (Silent
   lens absence is the PR-168 failure mode.)
4. **PR Hygiene Standard PH-03 high finding → verdict cannot be PASS.**
   Minimum verdict: `Request changes`. A high-severity Safety signal
   (4+ migrations, plaintext secret in diff, etc.) requires explicit
   reviewer attention before merge. (Per CR-09; see
   `plugins/sulis/references/pr-hygiene-standard.md`.)

### Advisory only

The verdict is reported, not enforced. `/code-review` never sets a status
check, never posts to the PR, never blocks merge. Branch protection and
human reviewers own the gate. This standard sets what the agent **says**,
not what the system **does**.

---

## CR-07: Lens Completion Criteria (MUST)

Each lens must produce a structured output before "complete" can be claimed.
A lens that produces no output is **not complete** — it produces an
explicit "nothing surfaced" entry listing the checks that ran.

### Architecture lens

Must produce a list of Form / Armor / Proof findings, each tagged with the
gap type from `references/hardening-deltas.md` (HD-02 table —
`dependency-direction`, `timeout`, `circuit-breaker`, etc.). If no
findings, the lens emits:

> *"Architecture lens: nothing surfaced. Checks run: dependency-direction
> scan, timeout scan, circuit-breaker scan, secrets scan, observability scan,
> contract-test scan."*

### Security lens

Must produce a list of findings against the 25 primitives at
`plugins/sulis/skills/codebase-assess/references/primitives.md`,
filtered to those applicable to the diff. Empty findings → explicit
"nothing surfaced" entry with the primitives that were applicable and the
scanners that ran.

### Quality lens

Must produce **all** of the following:

1. **Build Verification follow-up** — for every CR-01 finding, a quality-lens
   entry that translates the raw error into a finding (file:line, quoted
   text, recommended fix). Don't restate raw typecheck output.
2. **JSX / template identifier scan log** — for every TSX/JSX/Vue/Svelte file
   in the diff, a scan log confirming each new `{identifier}` reference is
   in lexical scope. Saved to `$WORK/jsx-ident-scan.log`.
3. **Dead-surface findings** — unused props/state/exports, unreferenced
   imports, JSDoc contracts the code doesn't honour.
4. **Contract-drift findings** — enum/union values the implementation never
   emits, DTO fields the service never sets, response shapes whose consumer
   assumes more than the producer provides.
5. **Test-coverage observation** — does the diff include tests for new
   behaviour? A source-only diff with no tests is a finding in itself.
6. **Style / readability** — naming, complexity, comments, TODO/FIXME
   density. Lowest priority; come last.

A quality lens missing any of items 1–5 is incomplete. Item 6 may be empty
without blocking completion.

---

## CR-08: Self-Attestation in Methodology (MUST)

Before the report is written, the reviewing agent attests to each CR-01..CR-07
rule in the report's Methodology section. The checklist appears verbatim:

```markdown
## Methodology

### Code Review Standard self-attestation

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p apps/dashboard`; `npx eslint <changed>`. Base: 0 errors. Head: 1 new error (see Build Verification). Coverage gap: none.
- [✓] **CR-02 Parallel dispatch used.** Three lenses dispatched concurrently. Diff: 6454 lines / 53 files (above carve-out threshold).
- [✗] **CR-03 Full-file reads.** 2 files >50 lines were sampled. Files: `apps/dashboard/app/coupons/page.tsx` (read 1-100, total 344); `apps/dashboard/lib/coupons.ts` (read 1-80, total 210). Verdict downgrade applied per CR-06.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line and quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 1 critical, 2 high, 5 medium, 3 low.
- [✓] **CR-06 Verdict computed.** Verdict: Block (Build Verification finding + CR-03 unread file).
- [✓] **CR-07 Lens completion.** Architecture: 3 findings + scan log. Security: nothing surfaced + scan log. Quality: 4 findings + jsx-ident-scan.log + dead-surface findings + contract-drift findings + test-coverage observation.
- [✓] **CR-10 Performance procedural checks.** Patterns scanned: 10. Findings: 1 N+1 DB (HIGH) at `apps/api/services/notifications.py:42`.
```

Each box is `[✓]`, `[✗]`, or `[—]` (N/A) with a one-line reason.

The reader of the report sees what the agent attests to. A failed box is
not a hidden gap — it is an admitted one, paired with the corresponding
verdict downgrade.

### Forbidden shape

The self-attestation cannot be silent. A report missing the Methodology
checklist is malformed and must be regenerated. A box claiming `[✓]`
without a one-line reason is malformed.

---

## CR-09: PR Hygiene Application (MUST)

The reviewing agent applies the **PR Hygiene Standard** at
`plugins/sulis/references/pr-hygiene-standard.md` (PH-01..PH-08) alongside
the three lenses. Hygiene checks run **before** lens dispatch — they
inform how cautious the lens work needs to be (a 6,000-line / 53-file PR
with 5 migrations warrants more conservative lens severity scoring than
a 150-line / 3-file single-concern PR).

### Output location

Hygiene findings appear in a dedicated **PR Hygiene** section of the
report, **between** Build Verification and the lens findings. Hygiene
findings do **not** mix with lens findings — they have different
provenance (artifact shape vs code defects) and different remediations
(split PR vs fix code).

### Signal table

The hygiene check produces the deterministic PH-06 signal table verbatim.
The signal table is the contract between this skill and any future
PR-touching skill — readers (human or agent) can recompute the verdict
from the signals.

### Severity feed into CR-06

PH-03 `high` severity findings (4+ migrations, plaintext secret pattern,
etc.) feed CR-06 auto-downgrade rule 4 — minimum verdict `Request
changes`. Other hygiene severities (`medium`, `low`, `note`) appear in
the report but do not trigger CR-06 auto-downgrades; they inform agent
judgement only.

### Hygiene findings do not produce Hardening Deltas

Lens findings (Architecture / Security / Quality) produce Hardening
Deltas with `source: code-review:PR-NN`. Hygiene findings produce
**recommendations to the PR author** (split, add tests, review migration
order) — not deltas. Splitting a PR is not a delta-shaped change; it's a
restructuring of the change itself.

### Calibration disclosure

The PR Hygiene Standard is in its own 90-day calibration window (see
PH-07). The reviewing agent records each hygiene finding's severity and
the threshold that triggered it in the report's PR Hygiene section, so
threshold calibration data accrues across real reviews.

### Self-attestation row

The CR-08 Methodology checklist gains one row:

```markdown
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: medium (feat+refactor mix). PH-02 Size: high (1,847 lines / 32 files). PH-03 Safety: high (4 migrations). PH-04 Completeness: medium (4 new source files, no tests). PH-03 high → CR-06 auto-downgrade to Request changes minimum.
```

---

## CR-10: Performance Procedural Checks (MUST)

Scan the diff for a defined set of performance anti-patterns and report
any matches as findings. The patterns are mechanically detectable
(regex + file-type filter) and applied uniformly across reviews, so
the same N+1 / O(N²) / waterfall / unbounded-materialisation defects
get caught on every review regardless of which language model is
dispatching the quality lens.

CR-10 fills a real gap surfaced from a live production session: an
executor session against the platform repo composed two WPs in
parallel — one added `get_user(id)`; the other added a notifications
loop — that together became an N+1 query in production. Neither WP
in isolation looked wrong; the LLM-driven quality lens didn't flag
the composition. Mechanical checks scan the diff for the signature
regardless of which review path runs.

### Pattern catalog

Defined in [`performance-procedural-checks.md`](performance-procedural-checks.md)
(sibling doc; same directory as this standard). Ten patterns at v0.1.0:

1. **N+1 DB query** — loop body contains ORM call (HIGH default; CRITICAL on hot path)
2. **N+1 RPC / HTTP** — loop body contains network call (HIGH; CRITICAL on hot path)
3. **N+1 filesystem read** — loop body contains file-open (HIGH)
4. **O(N²) over same collection** — nested iteration over same variable (HIGH if unbounded; CONCERN otherwise)
5. **Synchronous waterfall** — chained `await` where outputs are independent (CONCERN)
6. **Unbounded materialisation** — `.all()` / `list(qs)` / `.collect()` without limit (HIGH if request-bound; CONCERN otherwise)
7. **Repeated invariant computation in loop** — `len(items)` or similar invariant recomputed each iteration (ADVISORY)
8. **Wasted DB roundtrips** — multiple sequential `.first()` / `.get()` (CONCERN)
9. **String concat in hot loop** — `+=` on string in Python/Java loops (ADVISORY)
10. **Scan-heavy filter on non-indexed column** — filter expression on column known to be non-indexed (CONCERN; requires schema knowledge — best-effort)

The sibling doc has, per pattern: detection signature (regex + file-type
filter), severity default per CR-05, evidence-template citing CR-04
(file:line + quoted text), and false-positive guidance.

### When detection fires

Each detection produces a finding under the Quality lens (CR-07
output item 7 — see SKILL.md) with:

- **Severity:** per the pattern's severity default; reviewer agent may
  adjust per CR-05's rubric (e.g., downgrade if outside hot path; upgrade
  if request-handler-scoped) with a one-line justification
- **Evidence:** file:line + the matched line verbatim + at minimum 2
  lines of surrounding context (per CR-04)
- **Rule cite:** `CR-10 pattern #N` referencing the catalog entry
- **Recommendation:** the pattern's standard remediation (e.g., "batch
  with `select_related` / `prefetch_related`"; "wrap in `Promise.all`";
  "stream via paginated query"); follows CP-01..CP-05 (Convention
  Preference)

### When patterns don't fire

Empty CR-10 output is valid. The Quality lens records:

```markdown
**CR-10 performance procedural scan:** No anti-pattern matches in the diff.
```

This is the same self-attestation shape as the quality lens's
"nothing surfaced" patterns elsewhere.

### Verdict implication

CR-10 findings flow through the standard CR-05 severity rubric and
CR-06 verdict computation:

- 1+ CRITICAL → verdict `Block` minimum
- 2+ HIGH → verdict `Request changes` minimum
- Otherwise: findings contribute to verdict without auto-downgrade

The standard's existing auto-downgrade rules apply unchanged; CR-10
doesn't add new downgrade rules.

### False positives

Regex-based detection produces false positives. Two mitigations:

1. **Reviewer review**: the agent reads each CR-10 finding's surrounding
   context (per CR-03) before including it in the report. If the
   context shows the pattern is safe (e.g., the "loop with DB call"
   is bounded to N≤3 items in a one-shot init path), the agent may
   downgrade to ADVISORY or omit with a one-line justification in the
   self-attestation row.
2. **Calibration window**: same 90-day window as CR-08 + PH-07. The
   reviewer records each CR-10 finding's severity + downgrade
   justification (if any) so threshold + signature calibration data
   accrues.

### Cost note

CR-10 detection runs in the same loop as CR-01 mechanical baseline
(grep over diff hunks). Per-review cost is O(diff lines) — negligible
compared to the LLM cost of the three lens reads.

### Self-attestation row

The CR-08 Methodology checklist gains one row:

```markdown
- [✓] **CR-10 Performance procedural checks ran.** Patterns scanned: 10. Findings: 1 N+1 DB (HIGH) in `apps/api/services/notifications.py:42`; downgraded from CRITICAL because the loop is bounded by `limit(50)`.
```

---

## Composition with other standards

This standard composes with — does not replace — the marketplace's existing
rules:

- **FE-01..FE-11 (Founder English)** — every founder-facing surface of the
  report (the conversational summary, the verdict line, the lead-with-outcome
  framing) passes the FE-06 five-point check. The Methodology self-attestation
  is internal-taxonomy by design and lives in a section the founder doesn't
  need to read — that is consistent with FE-09 (no mechanism narration in
  founder-facing surfaces) because Methodology is a transparency aid for the
  technical reader, not part of the founder summary.
- **AAF-01..AAF-09 (Audience-Adapted Framing)** — findings in the
  conversational summary translate to business risk language. CVE IDs, CWE
  numbers, algorithm names stay in the report body.
- **CP-01..CP-05 (Convention Preference)** — every "recommended fix" in
  every finding defaults to the established convention.
- **HD-01..HD-NN (Hardening Delta format)** — fixes produced from accepted
  findings emit as deltas with `source: code-review:PR-NN` and
  `lens: architecture | security | quality`.
- **GIT-01..GIT-10 (Git Workflow)** — `/code-review` is advisory; it never
  bypasses the merge gate that GIT-04 establishes.

---

## Anchor Case 1: PR-168 — the bug this standard exists to prevent

**Repo:** `honestmobile/honest-smart-sim-platform`
**PR:** #168 (`feature/hon-431-manage-coupons-in-dashboard`)
**Diff:** 6,454 lines, 53 files

**The bug:** `apps/dashboard/app/coupons/[schemeId]/page.tsx` references
`hasMore` as a runtime variable in JSX at line 264. The identifier exists
only as a type-annotation field on the response shape (line 113). No
destructure, no state assignment, no closure capture. Effect:
`tsc --noEmit --strict` errors `TS2304: Cannot find name 'hasMore'`. At
runtime, every render of the scheme-detail page throws
`ReferenceError: hasMore is not defined`.

**What `/code-review` reported (pre-CR-01..CR-08):** 11 findings, none of
them the `hasMore` bug. The agent decided not to dispatch the three lenses
("I have enough context from reading the source to produce a thorough
review without dispatching sub-agents"), read lines 1–100 of the affected
file, considered it covered, and moved on.

**What a free `claude[bot]` GitHub App reported on the same PR:** the
`hasMore` bug, file:line, type and runtime consequence, in one paragraph.
Plus three other findings the agent missed (dead `Props.schemes`,
unreachable enum value, unused parameter contract).

**Why the cheap tool won:** mechanical static analysis ran. Agent judgement
did not have to compete with it; it sat on top of it.

**What CR-01..CR-08 do about it:**

- CR-01 makes `tsc --noEmit` mandatory before any lens runs → the `hasMore`
  error appears in Build Verification at the top of the report.
- CR-02 forbids the single-reader collapse for diffs above 200 lines / 5
  files → the agent cannot decline to dispatch lenses.
- CR-03 forbids sampling on files >50 lines → reading 1-100 of a 344-line
  file no longer counts as coverage.
- CR-06 auto-downgrades the verdict to Block when Build Verification has
  findings → the agent's judgement of "looks fine" cannot override a
  failing typecheck.
- CR-07 requires the Quality lens to produce a JSX-identifier scan log →
  even without CR-01, the lens-level check catches it.
- CR-08 forces the agent to write down what it did and didn't do → the
  next reader sees the gap.

Edit 1 alone would have caught PR-168's build-breaker. The other rules
close the door on adjacent failure modes.

---

## Calibration

This standard is in calibration for 90 days from 2026-05-20. The agent
applying it journals every CR-NN application in the report's Methodology
section per CR-08. After calibration, rules with no evidence of triggering
in real reviews may be demoted to SHOULD; rules that triggered repeatedly
may have their thresholds tightened.

Anchor cases accrue here as production sessions surface new failure modes.
Each anchor case names the date, repo, PR, and which CR-NN rules would
have prevented the failure.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-20 | Initial standard. CR-01..CR-08, anchor case PR-168. Authored after `/code-review` v0.12.0 missed a build-breaker that a free GitHub bot caught. |
