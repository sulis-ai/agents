# Self-Heal Budget

The executor's bounded retry budgets per failure type per WP. Composes
with `executor-loop-standard.md` EL-07 (Self-heal budget per failure
type) and EL-08 (Escalation contract).

When a budget is exhausted, the executor halts and writes a structured
`BLOCKER-WP-NNN.md` record per the EL-08 format. **Never silently
exceed the budget. Never silently give up before the budget.**

---

## Budget table

| Failure category | Step(s) | Budget | Rationale |
|---|---|:---:|---|
| **Test failure during GREEN** | 3 | 3 | Most test failures are root-causeable in 1-2 cycles via Five Whys. 3rd attempt is the safety margin before declaring "I can't make this test pass within scope." |
| **Refactor regression during BLUE** | 4 | 2 | Blue's purpose is improvement, not heroics. After 2 failed refactor attempts, the code stays in green-but-unrefactored state. **Does not trigger BLOCKER** — quality debt note in journal instead. |
| **Docs lint / link-check fail** | 5 (v0.6+) | 3 | Markdown lint and broken cross-refs are usually mechanically fixable (path typos, anchor changes after heading rename). 3 attempts covers most. |
| **Lint / type / format** | 6 | 5 | Most lint issues are auto-fixable (formatter, `eslint --fix`). High budget because cycle is cheap and recovery is mechanical. Exhaustion typically signals a formatter ↔ linter rule conflict at the project root (out of scope). |
| **Code-review inline fix loop** (v0.20.1+) | 6.5 | 3 | `/sea:code-review` produces findings → inline fix → re-run `/code-review` → loop. Most fixes converge in 1-2 cycles; the 3rd is a safety margin before switching to Path B (auto-draft remediation WP) or Path C (founder-flagged exception via BLOCKER). On 3rd iteration with findings still remaining: stop the loop and escalate. Do NOT loop indefinitely — the gate fails closed via BLOCKER `trigger=code-review-unaddressed` if neither remediation nor exception path resolves the residue. |
| **Pre-commit hook failure** | 7 | 3 | Hooks are signal. If 3 attempts to address the hook output don't satisfy it, the hook config itself is likely the issue (out of scope). |
| **Push rejection** | 7 | 2 | Most push rejections are out-of-scope (concurrent executor collision, branch protection, auth). Low budget. |
| **CI failure on branch** | 8 (v0.2+) | 3 | CI runs are slow (minutes); each attempt costs real time. After 3 the cause is likely environmental (out of scope). |
| **Merge-to-dev conflict / stale-dev rebase** | 8 (v0.2+) | 2 | Covers two scenarios in v0.8.1+: (a) rebase has file conflicts (another WP merged something incompatible — usually structural; out of scope after 2 attempts); (b) dev advances during the WP's CI run (parallel peer merged in between — the rebase reconciles; bounded at 2 to prevent livelock under very high parallelism where dev keeps moving). |
| **Deploy failure** | 9 (v0.3+) | 3 | Deploys can fail transiently (registry timeout, capacity); 3 retries cover most transients. Beyond → infra issue. |
| **Health-check timeout** | 10 (v0.3+) | 5 | Health checks need warm-up time; exponential backoff covers slow starts. Beyond 5 → rollback trigger. |
| **Smoke-test failure** | 10 (v0.3+) | 2 | Smoke tests are deterministic; if they fail, retry rarely helps. Low budget; usually a regression or wrong assertion. |
| **Security-reviewer tooling error** | 11 (v0.6+) | 2 | Errors in the assessor itself (not findings — crashes, missing deps). 2 attempts cover transients; beyond → BLOCKER ("Step 11 could not run; assess manually before marking done"). |
| **Five Whys non-convergence** | any | 1 | One attempt to find the root cause. If Five Whys doesn't converge in 5 levels, the agent doesn't get 5 more levels — escalate. |

**Note on Step 11 CRITICAL findings.** A CRITICAL finding from the
security-reviewer is **not a budget failure** — it's a halt-and-
escalate. The WP introduced or exacerbated a critical issue and is
not done. No retries; write BLOCKER per EL-08 immediately.

---

## Counting rules

- **Per WP, per failure category.** Each new WP gets fresh budgets.
  Within a WP, attempts accumulate across steps for the same
  category — e.g. 2 lint failures at step 5 and 1 lint failure
  re-triggered by step 6's pre-commit hook = 3 lint attempts
  consumed.
- **Successful attempts don't consume budget.** Only failures count.
  A test that passes on the first attempt doesn't consume any of the
  GREEN budget.
- **Different failure types have separate budgets.** A test failure
  at step 3 (budget 3) and a lint failure at step 5 (budget 5) are
  independent — exhausting one doesn't affect the other.
- **The journal tracks all attempts** at `.executor-WP-NNN.md` under
  `## Self-heal attempts`. Each row: step, attempt number, failure
  summary, root cause, change applied, outcome.

---

## Budget exhaustion — what happens

1. Executor stops attempting that step.
2. Writes `BLOCKER-WP-NNN.md` per EL-08 format:
   - Verbatim failure output (the latest attempt's failure).
   - Five Whys trace from the latest attempt.
   - Root cause statement.
   - Scope verdict: **`in-scope (budget exhausted)`** (distinct from
     `out-of-scope (scope guard fired)`).
   - All previous attempts (from the journal).
   - Plain-English summary for the concierge.
   - Suggested next step.
3. Updates INDEX entry to `status: blocked`, references BLOCKER
   file.
4. Emits one plain-English status line for the orchestrator.
5. Exits cleanly.

The "Suggested next step" varies by failure category:

- **GREEN exhausted** — "The test's expected behaviour may be wrong,
  or the WP's Contract may be internally inconsistent. Re-verify
  the Contract; consider re-decomposing the WP."
- **Lint exhausted** — "Likely a formatter ↔ linter rule conflict
  at the project root. Check `pyproject.toml` / `eslint.config.js`
  / `.golangci.yml` for conflicting rules; resolve, then retry."
- **CI exhausted** — "CI failure root cause is environmental or
  pre-existing in `dev`. Check the CI logs; if dev's main branch
  is currently red, fix that first, then retry."
- **Deploy exhausted** — "Staging environment is unhealthy or
  capacity-constrained. Check `kubectl get pods -n staging` (or
  equivalent); free up capacity; then retry."
- **Health-check exhausted** — "The deployed change is unhealthy —
  this is likely a code regression. Trigger rollback (GIT-10); the
  WP returns to `pending` for re-attempt after the regression is
  understood."
- **Smoke exhausted** — "The deployed change doesn't satisfy the
  WP's smoke-test contract. Either the WP's expected behaviour is
  wrong, or the implementation drifted. Re-verify the contract
  against the implementation."
- **Docs lint exhausted (Step 5)** — "Markdown lint failures persist
  beyond 3 attempts. Likely a project-root markdown-lint config
  issue (out of scope for this WP). Investigate
  `.markdownlint.json` / `.markdownlintrc` or the equivalent."
- **Security-reviewer tooling error (Step 11)** — "Security-reviewer
  agent failed to complete its assessment (not a finding — a
  tooling failure). Possible causes: sulis-security plugin not
  installed, missing system tools (Trivy, Semgrep, Gitleaks), or
  staging URL unreachable from the assessor's environment. Step 11
  could not run; recommend assessing manually via
  `/sulis-security:codebase-assess <project> <repo> <staging-url>`
  before marking the WP done."
- **Step 11 CRITICAL finding** (not a budget exhaustion; halt-and-
  escalate directly) — "The security-reviewer surfaced a CRITICAL
  finding on the merge SHA. The WP introduced or exacerbated a
  critical issue and must be fixed before marking done. See the
  BLOCKER record for the specific finding, the Five Whys trace,
  and the scope verdict (in-scope: fix in this WP; out-of-scope:
  rollback + separate investigation)."

---

## Blue's special case (does NOT trigger BLOCKER)

Step 4 (BLUE) is the **only** step whose budget exhaustion does **not**
trigger a BLOCKER. After 2 failed refactor attempts:

1. The code stays in its green-but-unrefactored state.
2. The journal records the attempted refactors and the reason for
   stopping.
3. The executor proceeds to step 5 (lint).

**Rationale.** Blue's purpose is "leave code better than found." If
the agent can't find a clean refactor in 2 attempts, the code is
likely already at its boring shape — that's success-with-no-Blue, not
failure. The quality-debt note in the journal lets a human reviewer
revisit if they spot a refactor opportunity later.

This is the **only** exception. All other budget exhaustions trigger
BLOCKER.

---

## Composition with EL-07

This budget table is the executor's specific implementation of the
EL-07 (Self-heal budget) principle. Other agents that compose with
`executor-loop-standard.md` (future orchestrator, future agents)
publish their own budget tables — same shape, different numbers
calibrated to their failure modes.

The marketplace standard is:

- Bounded budgets per failure type.
- Per-scope reset (one WP's exhaustion doesn't affect the next WP).
- Exhaustion = halt + escalate (with Blue's exception above).
- Never silent.
