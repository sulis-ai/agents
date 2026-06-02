# TDD — Testable-state Definition of Done

> **Spec:** `../../.changes/create-testable-state-done.SPEC.md`
> **Change:** create-testable-state-done · create
> **Grounding case:** `/Users/iain/Documents/repos/platform/.specifications/agent-journey`

## Overview

Make "done" mean *the application is in a fully testable state* — provable by
**verification cases the founder can run themselves** and watch go green.
Four components, each reusing existing machinery rather than inventing:

1. **Verification-case artifact** (design-time) — the upfront cases.
2. **Runner** (`sulis-verify-acceptance`) — executes them against a standing app.
3. **DoD gate** — blocks "done" until cases pass-or-deferred-with-need.
4. **Drift detector** — keeps cases↔implementation honest.

This *extends* verification-by-design (`VERIFICATION_QUESTIONS.md` already asks
the design-time questions — local/remote, integrations, credentials, infra).
The new layer is the **done-time realisation**: turning those answers into
runnable, user-legible proof, gated, and drift-checked.

## Form — the four components

### Component 1 — the verification-case artifact (`verification-cases.yaml`)

Produced at specify/design time, lives with the change
(`.architecture/{change}/verification-cases.yaml`). One entry per
user-exercisable check:

```yaml
- id: VC-001
  title: "A new user can sign up and log in"      # plain English, founder-legible
  how_to_run: "pytest -m acceptance tests/acceptance/test_login.py::test_signup_login"
  expected: "Signup returns 200, a session cookie is set, /dashboard loads"
  where: both            # local | deployed | both
  needs: []              # credentials/accounts/infra this case requires
  status: pending        # pending | pass | fail | deferred:<need-id>
```

**Reuse, not a new framework (Decision 1).** A case does NOT embed a bespoke
test runtime — `how_to_run` points at the project's *own* executable test
(pytest marker, Playwright spec, a curl smoke command). The artifact is the
**founder-legible index + run-mapping** over tests that already exist in the
project's toolchain. Options considered: (a) Gherkin/BDD layer — rejected, adds
a parser + step-defs nobody maintains; (b) bespoke DSL — rejected, reinvents
test running; (c) **structured index over the project's real tests — chosen**,
boring and reuses the project's test stack. Founder-legibility comes from
`title` + `expected` in plain English; the machine runs `how_to_run`.

### Component 2 — the runner (`sulis-verify-acceptance`)

A thin orchestrator (stdlib, mirrors `sulis-verify-environment`'s JSON-envelope
+ exit-code contract). It:
- Reads `verification-cases.yaml`.
- For each non-deferred case, runs `how_to_run` against the target
  (`--target local|deployed`, supplying the base URL), captures pass/fail.
- Emits **two surfaces**: a JSON envelope (machine / CI) AND a plain green/red
  founder summary (`"✓ you can log in"` / `"✗ billing unreachable"`).
- `deferred:<need>` cases are reported as "skipped — needs {plain need}", never
  silently green.

**Extend vs new (Decision 2).** `sulis-verify-environment` tests the
*marketplace's own pipeline* (SRD→tests→graph) — wrong subject. A new sibling
`sulis-verify-acceptance` (the *product's* exercise paths) is correct; it reuses
verify-environment's envelope/exit-code conventions (CP — match the established
shape) but targets the built application, local or deployed.

### Component 3 — the DoD gate

A change cannot be claimed done until `sulis-verify-acceptance` reports every
case `pass` OR `deferred:<need>` (with the need recorded). Wires into the
**existing** ship-stage DoD gate (`sulis-verify-requirements` was wired into
change ship as step 4.8 — `b3bd986`); this adds an acceptance-state check
alongside it. The gate's failure message is founder-English: names the failing
case in plain terms + what's missing.

**Honest-done (Decision 3).** This is the real form of the #81 discipline:
"done" is grounded in the gate that *matters to the user* (can they use it),
not in "merged." On an advisory-CI repo, the acceptance gate — runnable
locally — becomes the trustworthy done-signal even when CI can't block.

### Component 4 — the drift detector

The cases are defined upfront; the build can diverge. A drift check verifies
each case's **referent still resolves** against the current implementation —
the `how_to_run` test still exists/collects, the endpoint/flow it names is
still declared (cross-referenced to the ServiceSpec/contract where present). A
case whose referent vanished is flagged drift → the cases must be updated
deliberately, not left stale.

**Reuse the Path-A pattern (Decision 4).** This is the same shape as
`check-canonical-drift.py` (canonical↔implementation): a detector run in CI +
locally, exit-1-on-drift, founder-legible report. Reuse the detector's
structure; don't reinvent the drift-gate.

## Armor — failure modes

| ID | Failure mode | System response |
|---|---|---|
| A-1 | App isn't standing when the runner fires | Runner reports "app not reachable at {target}" — a clear precondition failure, not a false red on the cases themselves. |
| A-2 | A case needs a credential/account that isn't present | Case is `deferred:<need>`; reported as "skipped — needs {plain need}"; the need is recorded, never faked green. |
| A-3 | Integration down at run time | Case fails with the integration named; distinguished from a code failure. |
| A-4 | Cases silently rot during the build | Drift detector flags unresolved referents (Component 4) before done is claimed. |
| A-5 | "Done" claimed with failing cases | DoD gate (Component 3) blocks; founder-English message names the gap. |
| A-6 | Deployed leg unverifiable (no deploy target) | `where: local`-only is honoured; the remote leg is `deferred:<need>` with the infra need recorded (reuses the published-artifact/no-deploy profile detection). |

## Proof — how this change is verified (dogfood)

The grounding case **is** the acceptance test: re-run the agent-journey change
through the new gate and confirm it is **blocked** at "done" because *a user
cannot log in* — the exact failure that slipped through before. A passing
fixture (login works) goes green; the broken one is caught. The drift detector
is proven by mutating a case's referent and asserting the flag fires.

## Design decisions (ADR-level, recorded inline — proportionate for a methodology change)

- **D-1 (Component 1):** structured index over the project's real tests; not a
  new BDD/DSL layer. Founder-legibility via plain `title`/`expected`.
- **D-2 (Component 2):** new `sulis-verify-acceptance` reusing
  `sulis-verify-environment`'s envelope/exit-code conventions; targets the
  built app (local/deployed), not the marketplace pipeline.
- **D-3 (Component 3):** extend the existing ship-stage DoD gate (step 4.8);
  block done unless pass-or-deferred-with-need.
- **D-4 (Component 4):** reuse the Path-A `check-canonical-drift.py` structure
  for cases↔implementation drift.

## Open questions (for build)

- Exact `verification-cases.yaml` schema field set (lock in the contract WP).
- How the runner discovers the local/deployed base URLs (reuse
  `.sulis/repo-contract.yml` deploy_target + a `--target` flag).
- Whether the cockpit verification view ships in this change or is a follow-on
  (lean: emit the JSON envelope here; cockpit render is an ADE follow-on).
