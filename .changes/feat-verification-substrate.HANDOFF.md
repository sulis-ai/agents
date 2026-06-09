# Handoff — feat-verification-substrate (CH-01KTMA) — task #98

> Seed for a fresh, scoped session. Written from the originating session while two
> critical-thinking spirals were fresh, so this build stays true to their conclusions
> (the "catch deviations" insurance). Read this before `/sulis:recon` → `/sulis:specify`.
> This is the LEAD change of a 4-change methodology program; it is UPSTREAM of #95.

## Why this change exists (the problem it closes)

Two failures cause "ships green but never works / long find-one-fix-one cycle":
1. **Verification gap** — WPs tested hermetically against builder-authored fixtures
   certify the SHAPE of each slice, never the REAL data crossing the SEAM between
   slices. Real-drive deferred to ship → each pass surfaces the next un-driven seam.
2. **Decision-quality gap (context drift)** — the agent makes calls with the wrong
   context: a long session accumulates noise and drifts (vibe-coding), or a unit lacks
   the decision history it needs.

This change builds the **substrate** that fixes both at the execution layer. The
seam-DoD *gate* that consumes it is a separate, downstream change (#95, fix "A").

## The substrate — what to build (verdicts from two spirals)

**It is the EXISTING headless scenario runner (`_scenario_runner` / `sulis-verify-acceptance`), made tiered + isolated + context-scoped. NOT a terminal per scenario.**

1. **Driver tier (formalise what dispatch half-does).** Make the step driver a
   first-class field mirroring the governed-process mechanism split:
   - `scripted` (http_call / subprocess / Playwright; mechanism = deterministic)
   - `agent-step` (browser-MCP / LLM-judged; mechanism = probabilistic)
   No new process model — surface what `_scenario_dispatch` already does.
2. **Isolation ladder, default-cheapest.** Per scenario-RUN, achieve state isolation by
   the cheapest sufficient rung: **reset fixture/state in the change's existing worktree
   (default) → fresh process → fresh env**. A scenario may declare `isolation: process`
   / `isolation: env` for the genuinely-stateful minority. **Do NOT spawn a worktree or
   terminal per scenario** (that re-buys the latency + bug-surface paid down in #93/#94).
   *Isolation — not data-determinism — is the reliability lever* (Bazel hermeticity /
   ephemeral-env-per-test / Testcontainers cost evidence).
3. **Verdict-invariant field on the Scenario contract.** Each scenario's verdict is
   `equality` (saved record == expected shape) OR `property` (a record matching shape X
   appeared; optional bounded retry/poll for timing/ordering seams). This is the field
   #95's gate reads for observed-vs-blocked. **"Deterministically verified" = a
   deterministic VERDICT in an isolated repeatable context, NOT deterministic data.**
4. **Context-scoped agent execution (the founder's actual "why" — keep context low,
   pass the right level for decisions).** Each atomic unit is dispatched in a FRESH,
   right-sized agent context via **subagent dispatch** (not a terminal), seeded with a
   **working-set-derived brief** (problem / current solution / decisions-so-far) **plus
   the scoped contract** (the seam's inputs/outputs + the scenario definition + the
   relevant spec slice) — *not* the whole session history. The **terminal is reserved
   for the human-in-the-loop change session only** (change-authoring), orthogonal to
   verification. The working-set thus does double duty: chain-of-sessions handoff AND
   per-unit context seed.

## Atomic unit
The **scenario-RUN** (an ephemeral execution of the scenario-DEFINITION) — REFINES, does
not change, the prior "unit = scenario." The per-run ledger is the existing
**TestRun/TestResult** (a blocked run is resumable by re-drive, auditable from evidence).

## Hard scope-guards (negative results — do NOT violate)
- **Terminal = change-authoring only.** Do not extend `_terminal_launcher` (#93/#94 is
  correctly scoped) into per-scenario verification.
- **Working-set stays CHANGE-scoped (#91).** Do not push it down to scenario-run
  granularity — TestRun/TestResult is the per-run ledger. This change is a scope-guard
  *for* working-set, not a consumer that bloats it.
- **No new abstraction on n=1.** Driver-tier + isolation are enforcement/surfacing over
  existing primitives, not new engines.

## Relationships / fold-ins
- **Upstream of #95** (fix A, seam-DoD gate). #95 is blocked on this. Sequence: this → A.
- **Agent-step tier IS the deferred browser-proving machine-half — FOLD INTO #92.**
- **Decoupled from** the terminal-launcher (#93/#94) and working-set (#91) — both
  confirmed correctly-scoped; a useful negative result that protects that bug-surface.
- Sibling methodology fixes: #96 (spiral-back), #97 (dependency-as-child-change).

## Load-bearing uncertainties to instrument (don't block on them — measure)
1. Do enumerated Scenarios tile the seam set 1:1 (is each seam the last hop of some
   Scenario)? If not, #95's unit drops from Scenario to the seam/contract-WP.
2. What fraction of real scenarios need the heavier isolation rungs (process/env) vs
   cheap reset? That ratio sizes the isolation machinery to build.

## Full reasoning (read if you need the why behind any call)
- Spiral 1 (the unit + seam-gate): `~/.claude/plugins/cache/sulis-plugins/sulis-brain/0.14.0/instances/critical-thinking/.runs/01KTJ3X9SEAMSPIRALFIX0001.md`
- Spiral 2 (the substrate, this change): `~/.claude/plugins/cache/sulis-plugins/sulis-brain/0.14.0/instances/critical-thinking/.runs/01KTKD16E06A7F9F342A0.md`

## Suggested next step
`/sulis:recon` then `/sulis:specify` — this is a methodology/standard + runner change
(engineering-architect territory): specify the driver-tier + isolation-ladder +
verdict-invariant + context-scoped-dispatch as the substrate #95 will consume.
