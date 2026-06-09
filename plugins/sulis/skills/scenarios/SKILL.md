---
name: scenarios
description: "Shows the verifiable scenarios defined for a change — the journey each checks, its observable pass condition, and whether it's been driven green, blocked, or not yet run."
---

# /sulis:scenarios — what's defined, and is it real?

## Conclusion (lead with the answer)

`/sulis:scenarios` answers one question for a change: **what verifiable
scenarios has the design process actually defined, and have they been
driven for real?** It reads the change's authored scenarios + the brain
and reports, per scenario, in plain English:

1. the **user journey** it checks,
2. what you'd **actually observe** if it works (its pass condition), and
3. whether it's been **driven for real** — green, blocked, or not-yet-run.

Then it **flags any part of the journey with no scenario covering it** —
the gap. And if no scenarios are defined yet, it says so plainly and
names the stage (specify / design) that should have produced them.

This makes the journey-rigor verifiability discipline *glanceable* — the
visibility a founder needs to know the "scenarios-first, verifiable"
discipline is live for a piece of work, not skipped. It is **read-only**:
it never drives, mints, or changes anything (use `/sulis:prove` to
actually drive the scenarios; this skill reports what's defined + the
evidence already on record).

This skill runs **inline** in the invoking session — no `Agent()` spawn.

## Usage

```
/sulis:scenarios            # the change you're in (resolves SULIS_CHANGE_ID)
/sulis:scenarios CH-XXXXXX  # a specific change by handle
```

## Resolving the tool path (MUST — first action)

The query helpers live in the sulis plugin's scripts dir. Resolve it once
as `$SCRIPTS_DIR` (same block every change/wpx skill uses):

```bash
SCRIPTS_DIR=""
_sulis_bin=$(printf '%s\n' "$PATH" | tr ':' '\n' | grep -E 'sulis-ai-agents/sulis/[^/]+/bin$' | head -1)
if [ -n "$_sulis_bin" ] && [ -d "$(dirname "$_sulis_bin")/scripts" ]; then
  SCRIPTS_DIR="$(dirname "$_sulis_bin")/scripts"
fi
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/_brain_query.py" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
if [ -z "$SCRIPTS_DIR" ]; then
  SCRIPTS_DIR=$(find ~/.claude/plugins/cache -name _brain_query.py -type f -path '*/sulis/*/scripts/*' 2>/dev/null \
    | sed -E 's#(.*/sulis/)([^/]+)(/scripts/.*)#\2 &#' | sort -t. -k1,1n -k2,2n -k3,3n \
    | tail -1 | cut -d' ' -f2- | xargs -I{} dirname {} 2>/dev/null)
fi
echo "SCRIPTS_DIR=$SCRIPTS_DIR"
```

## How to find what's defined

1. **Resolve the change.** If a `CH-XXXXXX` handle was passed, resolve it
   (the same handle resolution `/sulis:change` uses). Otherwise read
   `SULIS_CHANGE_ID` via `resolve_current_change()` in `_wpxlib.py`. If
   neither resolves, say so plainly and point at `/sulis:change list`.
   Capture the change's `primitive`, `slug`, and `worktree_path`.

2. **Read the authored scenarios file.** The specify step (deep mode)
   writes a durable
   `{worktree_path}/.changes/{primitive}-{slug}.scenarios.jsonld` and emits
   the Scenario / Workflow / Steps into the brain. Read that file — it is
   the "what was defined" artifact. Each entry carries the scenario id, the
   journey (its Workflow + Steps), and the Requirements it `verifies`.

   ```bash
   SCEN="{worktree_path}/.changes/{primitive}-{slug}.scenarios.jsonld"
   ```

   If the file is absent or empty AND the brain has no Scenarios for this
   change's journey (`find_scenarios_for_journey` in `_brain_query.py`),
   that's the **"none defined"** case — see rendering below.

3. **Read each scenario's pass condition + surface + drive status.** For each
   scenario:
   - **Pass condition** — the observable outcome on the scenario / its
     terminal Step (what you'd see if it works). It's in the scenarios
     file; render it in plain English.
   - **Surface** — the consumer surface this scenario exercises: `ui` (the
     screen / CLI / host-rendered surface a human drives) or `tool` (the
     API / SDK / MCP surface a machine consumer drives). It's the `surface`
     tag authored on the scenario (WP-007, ADR-005; a closed `{ui, tool}`
     enum) — read it straight off the entry. Group the per-scenario report
     **by surface** so the founder sees per-surface flow coverage (DESIGN
     §6.5 hop A6): which UI flows are verified, and — separately — which
     **tool** flows are. A change with a tool surface that walked only its UI
     is the gap this surfaces.
   - **Drive status** — has it actually been run green? Read the deposited
     evidence from the brain: for the Requirements the scenario `verifies`,
     `find_passing_testresults_verifying` in `_brain_query.py` returns the
     passing TestResults (a green Scenario run, or a `@verifies` unit test,
     deposits one). Map to:
     - **green** — a passing TestResult exists for it,
     - **blocked** — a TestResult exists but failed / the scenario is
       recorded blocked or deferred,
     - **not-yet-run** — no TestResult on record yet.

     ```bash
     python3 -c "
     import sys, json; sys.path.insert(0, '$SCRIPTS_DIR')
     from _brain_query import find_passing_testresults_verifying
     base='{worktree_path}/.brain/instances'
     # per requirement id the scenario verifies:
     print(json.dumps(find_passing_testresults_verifying(base, '<dna:requirement:…>')))
     "
     ```

4. **Find the gaps.** A journey hop with no scenario covering it is the
   honest gap. The plan-work coverage check already encodes this
   (`_verify_scenario_coverage.py`); reuse its read to list journey
   steps/seams with no covering scenario rather than re-deriving. Report
   each gap plainly ("the *checkout* step has no scenario — nothing
   verifies it").

5. **Read the three gate verdicts and roll them up (BDR-002).** The report's
   honest headline unifies **three distinct gates** — each asks a different
   question, and the rollup must keep them distinct (never collapse their
   logic). Read each verdict; do not re-derive any of them (read-only — the
   brain + gates are truth):
   - **Scenarios-required (#103)** — *is this change in scope for scenarios at
     all?* If it is and none are defined, that's the "none defined" case
     above.
   - **Journey-coverage (#86)** — *is every hop of an existing scenario's
     journey covered?* This is the per-hop gap read in step 4
     (`_verify_scenario_coverage.py`).
   - **UC-flow-coverage (WP-008)** — *does every use-case flow (main +
     alternate + exception), on each surface, have a covering scenario at
     all?* Read the verdict from the WP-008 gate
     (`_verify_uc_flow_coverage.py`); it returns `covered` (every flow has a
     covering scenario, or a planned WP, or a recorded out-of-scope decision)
     or `gaps` (≥1 flow with none — fail-closed). Surface its
     `uncovered_flows` as **plain titles**, never scenario or flow ids
     ("3 flows nothing covers yet: *cancel mid-checkout*, *expired card*,
     *retry after timeout*").

     ```bash
     python3 "$SCRIPTS_DIR/_verify_uc_flow_coverage.py" \
       --uc-flows @{worktree_path}/.changes/uc-flows.json \
       --journey '<dna:workflow:…>' \
       --base-dir '{worktree_path}/.brain/instances'
     # verdict: covered | gaps ; uncovered_flows lists the GAP flows
     ```

   These three roll up into **one** founder-facing result — distinct gates,
   one rollup (BDR-002). The headline names all three so the founder sees
   *which* gate is unhappy, not a single merged pass/fail.

## How to render (founder English, scannable)

Lead with the headline count, then the per-scenario blocks **grouped by
surface** (UI scenarios, then tool scenarios), then the gaps, then the
three-gate rollup. No internal ids in the founder's face — translate
`dna:scenario:…` to the journey's plain name, and show uncovered UC flows as
**plain titles** (never `SC-NN` / flow ids).

```
Verifiable scenarios for {change name} ({CH-XXXXXX}):

Screen surface (what a person drives)
  ✓ Sign in with email — you reach the dashboard.  (run green)
  • Checkout with a saved card — an order confirmation appears.  (defined, not driven)
  ✗ Password reset — the reset email is never observed.  (blocked: email step unconfirmed)

Tool surface (what a machine consumer drives)
  ✓ Create order via the API — the order id comes back.  (run green)
  • Cancel order via the API — the order shows cancelled.  (defined, not driven)

Gaps — journey steps with NO scenario:
  • "Delete account" — nothing verifies this path.

The three checks:
  • Scenarios expected here? Yes (this change touches a user journey).
  • Every step of each scenario covered? Yes.
  • Every use-case flow has a scenario (both surfaces)? No — 3 flows nothing
    covers yet: "cancel mid-checkout", "expired card", "retry after timeout".

Honest headline: {M} scenarios defined, {green} proven real, {gaps} gap(s);
UC-flow coverage: gaps (3 flows uncovered).
```

When nothing is defined:

```
No verifiable scenarios are defined for {change name} yet.
That means the scenarios-first step was skipped — they should be authored
at specify (/sulis:specify deep mode) and the journey walked at design.
```

## When to invoke

- A founder (or you) wants to see whether a change actually defined
  verifiable scenarios — the visibility check on the journey-rigor
  discipline.
- Before trusting that "the design covered the journeys" — confirm, don't
  assume.

## When NOT to invoke

- To *drive* the scenarios for real — that's `/sulis:prove` (the
  consumer-level reality check) or the ship-time acceptance gate.
- For Work Package build status — that's `/sulis:status` / `/sulis:wp-status`.
- For a trivial change (CW-05) with no journey — there are no scenarios to
  show, and that's expected.

## Gotchas

- **Read-only — never drives.** This reports what's *defined* and the
  evidence *already on record*. "Not yet run" is an honest status, not a
  failure to fix here; `/sulis:prove` or the ship gate is what drives them.
- **"None defined" is a real, useful answer.** An empty result is the
  signal the founder asked for — it means scenarios-first got skipped for
  this change. Say so plainly + name the stage that owns it; never paper
  over it.
- **No internal ids in the founder's face (FE-06).** Translate
  `dna:scenario:…` / `dna:requirement:…` to the journey's plain name and a
  plain pass condition. The handle (`CH-XXXXXX`) is the only id shown.
- **The scenarios file is the authored source; the brain is the evidence.**
  The `.scenarios.jsonld` says what was defined; the deposited
  TestRun/TestResult says whether it's been driven. Read both — don't infer
  drive-status from the file alone.

## See also

- `/sulis:prove` — actually drive the critical scenarios against the real
  thing (this skill shows what's defined; prove shows it works).
- `../../scripts/_brain_query.py` — `find_scenarios_for_journey`,
  `find_scenarios_verifying`, `find_passing_testresults_verifying`.
- `../../scripts/_verify_scenario_coverage.py` — the plan-work coverage
  read (journey hops with no covering scenario, the #86 gate).
- `../../scripts/_verify_uc_flow_coverage.py` — the UC-flow-coverage gate
  (WP-008): does every use-case flow, on each surface, have a covering
  scenario? The `covered | gaps` verdict this report rolls up.
- `../../scripts/sulis-verify-acceptance` — drives authored scenarios (the
  ship-time gate); the source of the green/blocked evidence this reads.
