---
founder_facing: true
---

# Spec — Testable-state Definition of Done

**Change:** create-testable-state-done · create

## Intent

Redefine what "done" means. Today a change can run all the way through, merge,
and report "done" while the actual application is **not usable** — the
agent-journey change is the proof: it shipped, but there was no way to log in
and no way to test it, locally or deployed. Merged code is not a done product.

This change makes **"done" mean "the application is in a fully testable
state"** — a human (the founder, or a non-technical user) can actually log in
and exercise it, locally *and* deployed, with authentication wired,
integrations reachable, and dependencies + infrastructure standing. And the
proof of that state is a set of **verification cases the user can run
themselves** and watch go green.

This extends — does not replace — the verification-by-design work already in
place (`VERIFICATION_QUESTIONS.md` already asks the right *design-time
questions*: where it's verified local-vs-remote, which integrations + what
credentials, what infra). The gap this closes: nothing today checks, at
*done*-time, that those answers were **realised** into a standing, exercisable
app. We move verification from a design-time *plan* to a done-time *state
assertion*, with runnable proof.

## The four pillars

1. **Upfront verification cases.** At specify/design time, a change defines
   concrete, runnable verification cases — "here's how we'll know it works":
   *log in as a new user*, *complete the core flow*, *the X integration
   returns real data*. Each case records: how to run it (a command / a cockpit
   action), the expected observable result in plain terms, and where it runs
   (local / deployed / both). Not vague acceptance prose — executable cases.

2. **User-runnable.** The founder runs them themselves — one command (or a
   cockpit button) — against a standing app, and sees plain green/red
   ("you can log in ✓", "the sign-up flow works ✓", "billing reachable ✓").
   Not buried in CI logs; legible to a non-technical user, and re-runnable on
   demand.

3. **Testable-state as the real DoD gate.** A change is not "done" until its
   verification cases actually **pass against a standing app** — auth wired,
   integrations reachable, infra up, local *and* deployed — or each missing
   piece is **explicitly deferred** with its blocking need recorded (a
   credential, a test account, a paid resource). This becomes the gate the
   "done" claim is grounded in (the real version of the #81 Definition-of-Done
   discipline: claim done only against the gate that actually matters).

4. **Drift-kept.** The verification cases are defined upfront and **kept in
   sync** with the implementation. If the build diverges from the cases (a
   flow changes, an endpoint moves, auth changes shape), that drift is
   **detected and surfaced** — the same Path-A pattern as our
   canonical↔implementation drift detector — so the cases stay truthful and
   are updated deliberately, never silently bypassed or left stale.

## Scope

- A **verification-cases artifact** produced at specify/design time (the
  upfront, user-runnable cases), with a defined shape (how-to-run, expected
  observable, where-it-runs, real/deferred status).
- A **runner** the founder can invoke (extend `sulis-verify-environment` or a
  sibling) that executes the cases against a standing app (local and/or
  deployed) and reports plain green/red.
- The **DoD gate** wired into the change lifecycle (review/ship stages): a
  change cannot be claimed done until its cases pass or are explicitly
  deferred-with-need.
- **Drift detection** between the verification cases and the implemented
  surface during implement, surfaced like the canonical-drift gate.
- A **plain-English verification view** (the cockpit can render the cases +
  their last green/red state per the ADE vision).

## Non-goals

- Not replacing CI or unit tests — this is the *acceptance / testable-state*
  layer on top, about the running application, not the code's unit coverage.
- Not a general-purpose test framework — cases are exercise paths, expressed
  in the project's own test tooling where possible.
- Not auto-provisioning paid/remote infra — where a case needs a credential or
  paid resource that isn't available, it is **deferred with the need
  recorded**, not faked.

## Acceptance (how we'll know THIS change works)

- A sample change (the agent-journey instance as the grounding case) produces,
  upfront, runnable verification cases including "a user can log in."
- The founder can run those cases themselves with one command/action and see
  plain green/red against a standing app — local, and (where deployable)
  deployed.
- A change whose app is *not* in a testable state (e.g. login broken /
  integration unreachable) **cannot be claimed done** — the gate blocks it and
  says, in plain English, what's missing.
- When the implementation diverges from the upfront cases during the build,
  the drift is surfaced so the cases are updated, not silently stale.
- The agent-journey failure mode (shipped, but no way in / no way to test) is
  caught by this gate before "done" is ever claimed.

## Constraints

- **Extend, don't restate** `VERIFICATION_QUESTIONS.md` / verification-by-design
  — the design-time questions already cover local-vs-remote, integrations,
  credentials, infra. This change consumes those answers and adds the
  done-time realisation + runnable proof + drift layers.
- **Reuse the Path-A drift pattern** (the existing canonical↔implementation
  drift detector) for the cases↔implementation drift — same mechanism, don't
  reinvent.
- **Non-technical-user legible** throughout — the cases, the runner output,
  and the cockpit view are plain green/red, not CI logs or jargon.
- **Local AND remote** — testability is asserted where the app actually runs;
  a deployable app must be exercisable both locally and deployed (or the
  remote leg deferred-with-need).
- **Grounding case:** `/Users/iain/Documents/repos/platform/.specifications/agent-journey`
  — the concrete failure this change must demonstrably fix.

## Next

This is a deep, founder-facing capability — design pass next
(`/sulis:design`), then decomposition. The design must decide: the
verification-case artifact shape, the runner (extend `sulis-verify-environment`
vs new), the DoD-gate wiring point, and the drift mechanism's reuse of the
Path-A detector.
