# Build hand-off — testable-state DoD gate (the final mile)

> For the session that builds this. The dependency (`Scenario`) is now LIVE.
> READ FIRST: `SPEC.md`, `TDD.md`, `scenario-entity.md`, `DISCUSSION.md`,
> `work-packages/INDEX.md` (all on this change branch).

## Status (what's done)

- **`Scenario` entity is minted + vendored + live on `dev`** (agents `78e99b6`;
  schema at `plugins/sulis/brain/compiled/product-development/scenario.schema.json`).
  Source mint on plugins `mint/scenario-entity` (`4d7a9e1`, DR-028).
- The discover-project verify-gate bug is fixed + shipped (`02f165a`, #140).

## ⚠ Design reconcile REQUIRED before building (the TDD is partly superseded)

`SPEC.md`/`TDD.md` were written *before* the `Scenario` decision. They place
verification cases in a change-dir `verification-cases.yaml`. **That is
superseded** — the whole point of the `DISCUSSION.md` + `scenario-entity.md`
thread is that cases are **living graph entities, not change-dir files.** So:

**The cases ARE `Scenario` entities.** A `Scenario`:
- `verifies → Requirement[]`, `exercises → Design`, `journey → Workflow`
  (a graph of IDEF0 `Step`s — login→onboard→use).
- Each `Step` carries `mechanism` (`deterministic|human|mixed`) +
  `agent_instructions` + `input_artifacts` (needs/data/credentials) +
  `preconditions`/`postconditions` (the asserts).
- Lives in the brain graph; a change PROPOSES/EVOLVES Scenarios, merged on ship.

**Re-decompose against this model first** (`/sulis:plan-work` on the reconciled
TDD), then build. The 4 components, re-aligned:

1. **Scenario authoring (specify/design wiring)** — the design stage defines/
   evolves the change's `Scenario` entities (graph), replacing the change-dir
   `verification-cases.yaml`. Founder-legible: plain title + the journey steps.
2. **Runner `sulis-verify-acceptance`** — reads the Product's in-scope
   `Scenario`s (blast-radius slice: those verifying Requirements/Designs the
   change touches), runs each Scenario's `journey` Steps against a standing app
   (`--target local|deployed`): `mechanism: deterministic` → run the command;
   `mechanism: human` → surface as a manual checklist item. Records a `TestRun`
   + `TestResult` per Scenario (`TestRun.of_scenario`, `TestResult.scenario`
   are now in the schema). Emits machine JSON + plain green/red.
   `input_artifacts` missing a credential → `deferred:<need>`, never silent-green.
3. **DoD gate** — extend the ship-stage gate (step 4.8): block "done" unless
   every in-scope Scenario's latest `TestResult.outcome == pass` OR
   deferred-with-need. Founder-English failure naming the gap.
4. **Drift detector** — a Scenario's `journey` Step referents (commands/
   endpoints) still resolve against the implementation; reuse the Path-A
   `check-canonical-drift` structure. A Scenario whose referent vanished is
   flagged before done.

## The end state (definition of done for THIS change)

A non-technical founder can define `Scenario`s up front, run them themselves
against a standing app (local + deployed) via one command/cockpit action and
see plain green/red, and "done" is gated on them passing. **Proven** by
re-running the agent-journey change through the gate and confirming it is
**blocked at done because login fails** (the failure that slipped through
before). Drift fires on a mutated Step referent.

## Discipline

- TDD-first (RGB per WP); tests in `tests/unit/` (CI only runs that path —
  see task #60).
- Reuse: `Step`/`Workflow` (the journey), the verify-environment envelope/exit
  shape, the Path-A drift structure. Don't reinvent.
- Ship to `dev` when green (the autonomous flow used all session).
- Commits end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Follow-ons (NOT blocking this build — tracked)

- Plugins `mint/scenario-entity` → merge in the plugins repo (their flow).
- Full agents vendor catch-up v0.5→v0.9 (11 new entities + drift) — separate
  integration (#65).
- `Scenario`-from-source emitter via `add-entity-emitter` (n=2).
