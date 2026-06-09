---
founder_facing: false
---

# Spec — seam-DoD gate: drive real-data acceptance at seam-close

**Change:** CH-01KTP7 · feat

> Fix "A" of the 4-change methodology program. Upstream substrate (#98, shipped
> as PR #259) delivers the verdict-invariant this gate consumes. Siblings #96
> (spiral-back transitions) and #97 (dependency-as-child-change) are separate
> changes, not blockers. Durable baton: `.changes/feat-seam-dod-gate.HANDOFF.md`.

## Intent

The build loop tests each work package hermetically against builder-authored
fixtures — that certifies the *shape* of each slice, but the **real data
crossing the seam between two slices** is never driven until ship. The
observed-or-blocked acceptance drive (`sulis-verify-acceptance`) fires only at
the ship stage today. By then the slices are merged-adjacent, so a blocked seam
is expensive to unwind, and every ship surfaces the next un-driven seam — a
slow, serial find-one-fix-one tail ("ships green but never works").

Re-time the catch: drive the real-data Scenario acceptance check at
**seam-close** — the moment a contract-first seam between two pieces of work
closes — and read the shipped equality|property verdict-invariant over the real
saved record → `observed | blocked`. Catch an un-driven seam when it is cheap to
fix, not after merge.

## Scope

- A **seam-close gate** in the build loop (`run-wp` / `run-all`) that fires when
  a contract-first seam closes: a producer WP and its consumer WP both reach
  done, or an integration / composite WP completes.
- The gate drives the **real-data Scenario acceptance** for that seam via the
  existing runner (`sulis-verify-acceptance` + the shipped tiered/isolated
  substrate), reading the equality|property **verdict-invariant** over the REAL
  saved record (ADR-003 — never synthesised).
- **Gate trigger unit = the seam (contract-WP boundary), not the Scenario.**
  Resolved at recon: Scenarios key to requirements + a journey and do not tile
  seams 1:1. At a closing seam the gate drives the Scenarios that verify the
  requirements the seam's two sides implement.
- **Verdict semantics (observed-or-blocked):**
  - `observed` — a covering Scenario drove green (equality or property verdict).
  - `blocked` — a step failed, the seam could not be driven, the drive was
    deferred, **or the closing seam has no covering Scenario at all** (its
    real-data behaviour was never driven).
- A `blocked` verdict halts seam-close as "not done" and is surfaced in **plain
  English**: which seam, and what wasn't driven.
- An explicit escape hatch (consistent with the existing ship gate's
  `--allow-deferred`) lets a knowingly-deferred seam proceed, recorded.
- **Standards updates:** add the seam-close DoD rule to
  `CONTRACT_FIRST_STANDARD.md` (analogous to CF-07 integration conformance) and
  the seam-close DoD wording to `WORK_PACKAGE_STANDARD.md`.

## Non-goals

- **Not building the verification substrate** — it shipped (#259): the tiered
  (scripted vs agent-step) runner, the isolation ladder, and the
  equality|property verdict-invariant. This change is the *consumer*.
- **Not building the agent-step execution tier** — deferred to #92
  (`agent-step-execution-mcp`). Seams that need live-subagent / browser-MCP
  execution report `blocked` until #92 lands. That is correct behaviour, not a
  bug (observed-or-blocked: couldn't-drive-for-real = not done).
- **Not removing the ship-stage drive** (gate 4.8). It remains as a backstop on
  the same runner; this change moves the *primary* catch earlier. Defence in
  depth, not replacement.
- Not the sibling program changes (#96 / #97).
- No new user-visible product surface.

## Acceptance

Test-first (MUST): author these as failing tests before the gate logic, mirroring
the existing `test_ship_acceptance_gate_wiring.py` pattern.

1. A seam closes with its real-data Scenario **un-driven** → gate **BLOCKS** at
   seam-close (today it passes silently until ship — that is the bug being fixed).
2. A seam whose covering Scenario drives green (**equality** verdict) → gate
   **PASSES** at seam-close.
3. A **property**-verdict seam (a record matching shape X appeared) → **PASSES**.
4. A **deferred / blocked** seam → **BLOCKS** (deferred ≠ done), surfaced in
   founder English naming the seam and what wasn't driven.
5. A closing seam with **no covering Scenario** → **BLOCKS** (the seam's
   real-data behaviour was never driven).
6. The explicit deferred escape hatch lets a knowingly-deferred seam proceed,
   and the deferral is recorded.

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

- **How this change is verified:** unit tests on the seam-close gate wiring
  (acceptance criteria 1–6 above), authored failing-first. The gate is itself a
  blocking gate — its own "done" is grounded in those tests passing, not in
  advisory branch-CI (this repo's `main` is unprotected, so branch-CI does not
  block; that is precisely the failure class this change addresses).
- **Real-data, not mock:** the verdict-invariant evaluates the REAL saved record
  produced by the runner (ADR-003). Tests drive the scripted-tier runner that is
  live today; agent-step-tier paths assert the `blocked` result.
- **Observable outcome:** a closing seam either reports `observed` (drove green)
  or halts with a plain-English `blocked` message identifying the seam and the
  un-driven behaviour.

## Constraints

- **Consume, don't reimplement:** reuse `sulis-verify-acceptance` and the shipped
  substrate's verdict-invariant; do not rebuild the runner.
- **Ground "done" in the blocking gate**, never advisory branch-CI (RC-02:
  `main` is unprotected on this plan).
- **Gate unit = seam / contract-WP boundary** (resolved: Scenarios don't tile
  seams 1:1).
- **Agent-step-tier seams report `blocked`** until #92 lands; escapable via the
  deferred flag.
- **Test-first**, mirroring the existing ship-acceptance-gate-wiring tests.
- **Plain-English surfacing** of every block (which seam, what wasn't driven) —
  no operator vocabulary leaked.
- The seam definition is owned by `CONTRACT_FIRST_STANDARD.md`; this change adds
  the DoD timing rule there, it does not redefine the seam.
