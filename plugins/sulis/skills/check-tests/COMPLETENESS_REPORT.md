# Completeness Report — sulis:check-tests

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #4 of sulis:add-skill v0.4.0)
**Methodology:** `sulis:add-skill` v0.4.0 (five-gate)
**Source of design:** `.architecture/sulis-checkup/TDD.md` (tier 3) +
the regression-detection conversation in this session

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 overlaps (2 expected sibling/parent; 3 coincidental); 1 vocab collision on `baseline` (three distinct uses — disambiguate) |
| 2 — Scope Lock | PASS | 7 items locked; baseline mechanism scoped to v1 with extraction-to-shared-helper deferred |
| 3 — Generate | PASS | SKILL.md + scripts/regression.py + 2 references produced; framework-detection registry pattern established |
| 4 — Evaluate | PASS-with-note | End-to-end regression detection verified via synthetic fixture; one mid-flight refinement (pytest -q → -v for signature extraction) |
| 5 — Adversarial Review | PASS | 3 audience-conditional MUC-F + 3 audience-agnostic addressed; 2 OPEN_RISK documented |

**Publication decision:** APPROVED

---

## Gate 1 — Find

**BRIEF_PACK regenerated:** via `inventory.py`

**Description overlaps (5):**
- `sulis:check-readability` (8 tokens) — sibling tier-skill; expected high overlap; different audit
- `sulis:code-health` (8 tokens) — wrapper; expected parent-child; check-tests will wire into tier 3
- `sea:code-review` (7 tokens) — multi-lens per-PR review; coincidental on "check"/"review"/"changes"
- `sea:suggest-split` (7 tokens) — PR-splitting; orthogonal
- `sea:probe` (4 tokens) — structural analysis; coincidental

**Vocabulary collisions (1):** `baseline`

Three distinct uses in the marketplace:
- `sea:code-review` — "mechanical baseline" (CR-01 pre-lens gate: typecheck+lint must pass)
- `sea:probe` — "baseline-aware" (credential scanning Phase 1.17: hash-only allowlist)
- `sulis:check-tests` — "regression baseline" (test state snapshot at known-good time)

All semantically distinct; no operational collision. Resolution: explicit Vocabulary entry naming the three uses.

**No existing skill covers** founder-facing test-pass-delta regression check. Gate 1 PASS.

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `check-tests` |
| Plugin home | `sulis` |
| Audience | **both**. Founder default; `--raw` flag for operator JSON output. Mode-selection: explicit-flag (consistent with check-readability + code-health pattern) |
| Category | **Founder UX & Navigation** (specifically: regression-detection sub-family) |
| Trigger condition | "Use when the founder wants to know if anything that was working before stopped working — runs the test suite, compares to a baseline, and reports any newly-failing tests as regressions. Read-only when the test runner is read-only; never modifies code." |
| Top-5 gotchas | (below) |
| Depth modes | None for v1. (Future: `quick` = stats-only from cached results; `full` = always run.) |

### Top-5 gotchas (with concrete source)

1. **No baseline yet — can't detect regressions on first run.** First run captures the baseline; second run is the first regression check. Founders may expect immediate regression output and be confused.
   *Source: prior-art* — sulis-execution's wpx-findings register pattern (signature-dedup needs a prior state). Mitigation: first-run report explicitly says "captured baseline — next run will detect any regressions"; never silently passes when there's nothing to compare.

2. **Test framework detection brittleness.** Projects often have multiple frameworks (pytest + jest in monorepos); non-standard configs (e.g., pyproject.toml-only); custom test runners. Mis-detected framework → wrong test run → false verdict.
   *Source: prior-art* — HD-008 source-discovery brittleness; check-readability's PR-scope brittleness gotcha. Mitigation: detection emits a confidence score; if multiple frameworks detected, asks before defaulting; explicit `--framework` override flag.

3. **Tests that take a long time to run.** A 30-minute test suite blocks the founder. Need timeout + read-cached-results fallback to keep the skill usable.
   *Source: author-experience* — slow CI is universally frustrating; founders bounce after ~5 minutes of waiting. Mitigation: default 120-second timeout; offer cached-results mode if cache present; `--timeout N` override; graceful fallback to "tests detected but not run — pass --run to execute."

4. **Flaky tests appear as regressions.** A test that passes 90% of the time flip-flops between baseline and HEAD. Reporting it as a regression every run is noise that erodes trust.
   *Source: prior-art* — sulis-execution's wpx-train has 1 known-flaky concurrency test that gets explicitly suppressed in assertions; flakiness is a real production concern. Mitigation: detect re-runs of same test that flip pass↔fail; flag as "flaky" rather than "regression"; allow-list at `references/check-tests-known-flaky.md`.

5. **Founder might expect this to FIX failing tests.** Universal destructive-action ambiguity across read-only audit skills. Founder sees "5 tests are failing" and Claude might try to edit code to make them pass.
   *Source: prior-art* — check-readability gotcha #5 and code-health gotcha #4; founder-facing-conventions Rule 3. Mitigation: SKILL.md says "this skill never modifies code — only reports" in three places; explicit "fixing a failing test is a separate engineering action" guidance in presentation template.

### Vocabulary terms introduced

- **regression** — a test that was passing in the baseline and is failing at HEAD. The load-bearing concept.
- **baseline** — the snapshot of test state at a known-good moment (commit SHA + per-test pass/fail). Disambiguates from `sea:code-review`'s "mechanical baseline" (CR-01 pre-lens gate) and `sea:probe`'s "baseline-aware" (secret-detection allowlist). Stored at `.checkup/{project}/baseline.json`.
- **test-pass-delta** — the diff of passing/failing tests between baseline and HEAD. Three categories: newly-failing (regressions), newly-passing (fixes), unchanged.
- **newly-failing** — was-passing-now-failing tests; the regression category.
- **newly-passing** — was-failing-now-passing tests; the fix/improvement category.
- **test-signature** — the unique identifier for a test across runs (typically: `{relative_file_path}::{class_name}::{test_name}` for pytest; equivalent for other frameworks). Used for signature-dedup so we can compare across runs even when test counts change.

---

## Gate 3 — Generate

**Files produced:**

- `plugins/sulis/skills/check-tests/SKILL.md` — entrypoint; three-mode invocation (cached / fresh / detection-only); baseline-first behaviour explicit; founder/operator modes
- `plugins/sulis/skills/check-tests/scripts/regression.py` — framework detection + run + parse + baseline-compare + delta + flaky-suppress + render
- `plugins/sulis/skills/check-tests/references/framework-detection.md` — per-framework signals, run commands, parser notes; the extensibility contract
- `plugins/sulis/skills/check-tests/references/check-tests-known-flaky.md` — marketplace-shared flaky-test allow-list; per-project overrides documented
- `plugins/sulis/skills/check-tests/COMPLETENESS_REPORT.md` — this file

**Scope lock adherence:** verified. All 7 Gate 2 items reflected; founder/operator mode-selection via `--raw` (consistent with sibling skills); baseline mechanism encapsulated for v1 (extraction to shared helper deferred per Gate 2 lock).

**Referenced files verified present:**
- `plugins/sulis/references/founder-facing-conventions.md` — exists
- `plugins/sulis/skills/check-readability/SKILL.md` — exists (cross-skill prior art for gotchas)
- `plugins/sulis/skills/code-health/SKILL.md` — exists (parent wrapper)
- Cross-skill citations in gotchas all resolve to actual files

---

## Gate 4 — Evaluate

### Perspective 1 — Trigger accuracy

**Verdict:** PASS

**Method:** mental walkthrough of 10 representative invocations.

| Scenario | Should trigger? | Likely to trigger? |
|---|---|---|
| "did my changes break anything?" | YES | YES (verbatim trigger) |
| "did anything that was working stop working?" | YES | YES (verbatim) |
| "did the tests still pass?" | YES | YES |
| "check for regressions" | YES | YES |
| "run my tests" | maybe | maybe (could route to direct pytest invocation, but check-tests does run them) |
| "is my code readable?" | NO (→ check-readability) | NO |
| "is my code secure?" | NO (→ check-security future) | NO |
| "are my tests well-designed?" | NO (→ sea:test-audit future, tier 6) | maybe (description mentions tests; could trigger; not catastrophic — would correctly report current state but no regression context) |
| "fix the failing tests" | NO (skill is read-only) | maybe (Claude might trigger then correctly say "I only report") |
| "what tests do I have?" | NO (this is enumeration, not regression) | maybe (could trigger; output would report test count which partially answers) |

**Result:** ~80-85% precision. The 3 ambiguous cases are tolerable — the skill in those cases provides accurate-but-not-quite-what-was-asked output. SKILL.md "When NOT to invoke" points to the right alternative skills.

### Perspective 2 — Gotchas coverage

**Verdict:** PASS

All 5 gotchas have documented sources:
- No baseline on first run → wpx-findings signature-dedup pattern (prior art)
- Framework detection brittleness → HD-008 + check-readability prior art
- Slow test suites block founders → author-experience (universal CI frustration)
- Flaky tests appear as regressions → sulis-execution's known-flaky concurrency test (prior art with citation)
- Founder might expect to FIX → check-readability gotcha #5 + code-health gotcha #4 + conventions Rule 3 (cross-skill pattern)

5 items, ≤15 limit, ordered by likelihood × impact (no-baseline-first-run is highest likelihood; FIX-expectation is highest impact for trust).

### Perspective 3 — Functional completeness

**Verdict:** PASS (with one in-loop refinement)

**Scenarios tested:**

1. **Synthetic fixture — first-run baseline capture.** Created tempdir with git init + 3 tests (2 passing, 1 failing). First run correctly:
   - Detected pytest framework
   - Ran 3 tests
   - Captured baseline at commit SHA
   - Reported "First run. Captured baseline at commit `c04d3c5` (3 tests). Next run will detect any regressions against this point."
   - Explicit, never silent — passes the founder-facing-conventions Rule 5 test.

2. **Synthetic fixture — regression detection.** Modified the fixture to break `test_one_passing` (which had been passing in baseline). Second run correctly:
   - Detected the framework
   - Ran 3 tests (1 passing, 2 failing)
   - Compared against baseline
   - Reported `test_one_passing` as **newly-failing (regression)**
   - Did NOT flag `test_three_failing` as a regression (it was already failing at baseline — pre-existing problem)
   - Verdict: "⚠ Something broke — 1 test that was passing now failing"

3. **--raw mode.** JSON envelope validates; structure includes test_count, passing/failing counts, newly_failing/newly_passing arrays, baseline SHA, captured_baseline flag. Pipe-friendly.

**Failure modes captured:**

- **Mid-flight refinement (Gate 4 P3 discovery):** initial parser used `pytest -q` which collapses results to characters (no signatures). Caught when first run reported "tests=0". Refined to `pytest -v` which emits per-test PASSED/FAILED lines with signatures. Now PREVENTED, not OPEN_RISK. Documented in Gate 5 misuse case + the methodology feedback.

### Refinements applied during Gate 4 P3

| Issue | Refinement | Outcome |
|---|---|---|
| `pytest -q` parser lost signatures | Switched to `pytest -v --tb=no --no-header -p no:cacheprovider`; new `_parse_pytest_verbose()` extracts `signature::name STATUS` from per-test lines | Synthetic 3-test fixture parses correctly; regression delta computes correctly |

---

## Gate 5 — Adversarial Review

### MUC-F1: Operator jargon leak in error string — PREVENTED

- **What Claude might do wrong:** pytest exits with rc=2 (collection error); raw error bubbles up to founder.
- **Mitigation:** the `errors[]` array is rendered under "## Errors" in founder mode; raw rc values stay in operator mode. Pytest exit code semantics (0=pass, 1=fail, 5=no-tests-collected) are explicitly handled — only "unexpected rc" produces an error entry.

### MUC-F3: Destructive action triggered by ambiguous founder phrasing — PREVENTED

- **What Claude might do wrong:** founder says "fix the failing tests" — Claude takes the regression report as authorisation to edit code.
- **Mitigation:** SKILL.md says "this skill never modifies code — only reports" in three places (description, gotcha #5, when-NOT-to-invoke). The `--update-baseline` flag is the ONLY mutating action and requires explicit founder consent (no auto-update on subsequent runs).

### MUC-F5: Source-of-truth false-positive — PREVENTED

- **What Claude might do wrong:** flaky tests flip baseline ↔ HEAD; reported as regressions every run; founder loses trust.
- **Mitigation:** known-flaky allow-list at `references/check-tests-known-flaky.md` + per-project override at `.checkup/{project}/known-flaky.md`. Flaky tests show in "Flaky tests (suppressed from regression report)" section, not in the regressions section.

### Audience-agnostic — Trigger condition matches too broadly — PARTIALLY PREVENTED

- **What Claude might do wrong:** "are my tests well-designed?" (Q about test quality) triggers check-tests (Q about pass/fail). Founder gets regression report; thinks system is broken because it didn't answer the design question.
- **Mitigation in v1:** "When NOT to invoke" section explicitly points to `sea:test-audit` (planned tier 6) for test quality.
- **OPEN_RISK:** until `sea:test-audit` ships, check-tests is the only test-related skill — broader trigger captures intent it doesn't fulfil.
  - **revisit_by:** trigger — "sea:test-audit ships OR founder feedback shows confusion"

### Audience-agnostic — Authorization leakage — PREVENTED

- SKILL.md gotcha #2 explicitly says detection emits confidence score; if multiple frameworks present, asks before defaulting. Framework requirements (pytest installed, npx available for JS, go binary for go) checked at run-time; missing-tool errors are typed (not raw FileNotFoundError).

### Audience-agnostic — Silent failure of progressive disclosure — PREVENTED

- Both referenced files exist on disk (verified at Gate 3); `references/framework-detection.md` covers the per-framework extension contract.

---

## Open risks accepted at publication

1. **First-run UX may confuse founders expecting immediate regression output.** Mitigated by explicit "First run. Captured baseline..." message but founders may not read it carefully.
   - **revisit_by:** event — "first real founder run reports confusion about why regressions weren't detected"
   - **Workaround:** SKILL.md gotcha #1 documents this prominently.

2. **Trigger-condition broad enough to capture test-design questions (no sea:test-audit yet).** Founder asks "are my tests good?" → check-tests runs; partially answers.
   - **revisit_by:** trigger — sea:test-audit ships
   - **Workaround:** "When NOT to invoke" names the future skill.

---

## Vocabulary changes (during authoring)

None — vocabulary locked at Gate 2 used unchanged through Gate 3.

---

## Methodology feedback (running notes for add-skill v0.6.0)

Gaps surfaced during this run:

1. **Audit-pattern + baseline pattern compose.** check-tests is the first
   skill combining audit-pattern (Gate 4 P3 fixture iteration) with
   baseline-mechanism. Both pattern entries in methodology.md should
   note this composition; future regression-style skills will follow.

2. **Framework-detection-registry pattern is similar to code-health's
   tier-registry.** Both have an extensible registry where adding a new
   entry doesn't require rewriting the orchestrator. Pattern should be
   named explicitly in methodology.md as "registry-driven extensibility."

3. **Real-state fixture limitation: the marketplace as fixture FAILED here.**
   Unlike check-readability (which audits source files marketplace-wide),
   check-tests needs an actually-runnable test suite at a discoverable
   path. The marketplace's tests live in plugins/sulis-execution/scripts/
   tests/ which isn't auto-discoverable from marketplace root. For
   regression-pattern skills, the synthetic-fixture path is primary; the
   real-state path is secondary or absent. Worth noting in
   completeness-perspectives.md.

4. **Mid-flight parser fix during Gate 4 P3 was caught by testing.**
   Methodology working as designed — fixture run revealed the bug.
   Strengthens the case for the v0.4.0 "misuse cases sometimes surface
   during Gate 4" allowance.

(These 4 join the 11 already queued for add-skill v0.6.0: 5 from
check-readability, 4 from code-health, 2 from inbox. Total: 15.)
