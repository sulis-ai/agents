# VERIFICATION_REPORT — `/sulis:change`

**Skill:** `plugins/sulis/skills/change/SKILL.md`
**Authored via:** `sulis:add-skill` v0.7.0 (five-gate methodology)
**Tier:** STANDARD (orchestration skill — routes to existing primitives;
not a methodology/authoring skill, not a founder-visible verdict skill)
**Audience:** founder-facing (dual-register, default founder-mode)
**Date:** 2026-05-26
**Verdict: PASS**

---

## Gate 1 — Find (discovery + primitive discovery)

### Sub-step 1a — BRIEF_PACK

Ran `inventory.py --target-plugin sulis --target-skill change`. 91 skills
across 7 plugins reviewed.

- **No skill named `change` exists** — no collision. CC verdict:
  **VALIDATED** (full marketplace skill list enumerated; the closest
  matches are references, not skills).
- Adjacent prior art reviewed and reused, not duplicated:
  - `../../scripts/sulis-change` (the CLI) — `start`/`adopt`/`finish`/
    `list`/`status` subcommands; `start` has `--spawn` + `--intent`;
    `finish` has `--merge`/`--pr`. This skill drives it.
  - `../../scripts/_terminal_launcher.py` — `launch_change_terminal`
    (verified signature: `change_id`, `worktree_path`, `visible`,
    `entry_command`, `extra_env`, `pre_prompt`).
  - `../../scripts/_wpxlib.py` — `resolve_current_change()` (reads
    `SULIS_CHANGE_ID` → manifest) + `back_integrate_change_branch()`
    (verified 5 return statuses: `already_current` / `merged_ok` /
    `merge_conflict` / `fetch_failed` / `internal_error`).
  - `run-all` / `start` — shape reference for orchestration skills.
- **Vocabulary collision check:** "change" already names references
  (`change-work-standard.md`, `change-primitives.md`) and the
  `sulis-change` script — these are the SAME concept this skill surfaces,
  so reuse is correct, not collision. `handle` / `ship` / `focus` /
  `rebase` introduce no conflicting meaning elsewhere in the marketplace.

### Sub-step 1b — Primitive discovery

**N/A — non-analysis skill.** This is an orchestration/CLI-routing skill,
not an analysis/audit/aggregator skill. It invokes no Semgrep/Trivy/lizard
tool stack. Its "primitives" are the five subcommands, which are
independently invokable and already decomposed by the design doc's Phase 6
deliverables. Fan-out = 5 (≤ 7, PD-02 satisfied).

**Gate 1: PASS.**

---

## Gate 2 — Scope Lock

| Lock item | Value |
|---|---|
| Skill name | `change` (kebab; non-colliding per Gate 1) |
| Plugin home | `sulis` |
| Audience | **founder-facing** (dual-register; founder-mode default) |
| Category | Founder UX & Navigation |
| Trigger condition | "Use when the founder wants to start a new piece of work, see everything in flight, jump back into one, ship one when it's ready, or pull in the latest from the team." (user-facing vocab only) |
| Standards-phase | input: REFERENTIAL_INTEGRITY; processing: CRITICAL_THINKING; output: CRITICAL_THINKING |
| Verification tier | STANDARD (justified: routes to existing primitives; no new code; not a verdict skill) |
| Tool stack | N/A — orchestration skill; drives `sulis-change` + two `_*.py` helpers (declared + path-verified). No audit-pattern tools, so the audit depth bar does not apply. |
| Register | founder_mode default; technical_mode shape json_envelope; triggers [intent, --raw, /sulis:jargon] |
| Top-N gotchas | 8 (operator-vocab leak, ship-prompt, never-merge-red, dev-not-main, file-based-not-SQLite, stale-pid, merge-not-rebase, no-mechanism-narration) — within ≤ readable; ≥ 1 on operator-vocab leakage + ≥ 1 on destructive confirmation (both present) |
| Related skills | start (related_to), run-all (related_to), founder-facing-conventions (optional_input), change-primitives (optional_input) |
| Depth modes | None beyond dual-register (founder/technical) |

founder-facing-conventions.md read in full. No item TBD.

**Gate 2: PASS.**

---

## Gate 3 — Generate

- `description:` matches the Gate 2 trigger condition; user-facing vocab
  only (test: a fresh session handed the description alone would know to
  invoke on "start work / what am I working on / ship this").
- `standards:`, `register:`, `verification_spiral:`, `related_skills:`
  frontmatter blocks all present and valid YAML.
- Conclusion-first structure (Pyramid): the five-row table leads the body.
- `## When to invoke` + `## When NOT to invoke` present and MECE (the four
  NOT-cases each route to a distinct other surface: run-all, start,
  promotion, status).
- `## Gotchas` ordered by likelihood × impact (operator-vocab leak and
  ship-prompt first).
- `## Vocabulary` present (7 domain terms — ≥ 2 threshold met).
- Linguistic audit (NH-02): scanned for prohibited terms (comprehensive /
  robust / powerful / revolutionary / disruptive / game-changing /
  seamless / leverage). **Zero present.**
- Progressive disclosure: points to `references/` + `scripts/` + design
  doc rather than inlining their content.

**Gate 3: PASS.**

---

## Gate 4 — Evaluate (STANDARD dimensions)

| Dimension | Score | Threshold | Notes |
|---|---|---|---|
| ACCA (Accurate/Complete/Concise/Actionable) | 4/5 | ≥ 3 | All five subcommands have concrete, runnable command shapes + report templates. |
| Evidence Grounding | 5/5 | ≥ 3 | Every tool/flag traced to source: `sulis-change start --spawn --intent` (argparse lines 587-602), `finish --merge` (619), `launch_change_terminal` signature, `back_integrate_change_branch` 5 statuses, `branch-ci.yml` workflow exists. |
| Structural Coherence | 4/5 | ≥ 3 | Conclusion-first; subcommand contracts in invocation order; gotchas + vocab + see-also follow. |
| Honest Uncertainty | 4/5 | ≥ 3 | Spawn-failure, red-check, merge-conflict, fetch-failure paths each have an honest "here's what didn't happen + what to do" branch. |
| Codebase Referential Integrity | 5/5 | ≥ 3 | See entity trace below — all pre-existing entities verified on disk; zero unflagged new entities. |

### Codebase Referential Integrity trace

| Entity named | Path | Verified |
|---|---|---|
| `sulis-change` CLI | `plugins/sulis/scripts/sulis-change` | yes (read; `start --spawn --intent`, `list`, `finish --merge` confirmed) |
| `launch_change_terminal` | `plugins/sulis/scripts/_terminal_launcher.py` | yes (read; public entry-point, signature matches) |
| `resolve_current_change` | `plugins/sulis/scripts/_wpxlib.py:3527` | yes |
| `back_integrate_change_branch` | `plugins/sulis/scripts/_wpxlib.py:3569` | yes (5 statuses confirmed) |
| `.changes/{primitive}-{slug}.yaml` | repo manifest path | yes (sulis-change `_metadata_path`) |
| `~/.sulis/changes/{id}/session.json` | local session state | yes (`_write_session_json`) |
| `branch-ci.yml` | `.github/workflows/branch-ci.yml` | yes (ls confirmed) |
| `change-primitives.md` (22 primitives) | `plugins/sulis/references/change-primitives.md` | yes (read) |
| `founder-facing-conventions.md` (Rules 1-6) | `plugins/sulis/references/founder-facing-conventions.md` | yes (read) |
| `/sulis:run-all`, `/sulis:start`, `/sulis:run-wp`, `/sulis:status` | sibling skills | yes (in BRIEF_PACK) |

No entities flagged "NEW" — the skill realises Phase 6a entirely from
already-built Phase 5 infrastructure.

### Founder-readability perspective (founder-facing extra sub-check)

Every founder-visible string (trigger condition, the five report
templates, the error/conflict templates, gotcha prose) ran through the
FE-06 read-aloud test. **100% pass** — no internal IDs as headlines, no
untranslated operator nouns in founder-facing strings, primitives
translated to plain nouns, ULID never the headline.

**Gate 4: PASS** (all dimensions ≥ threshold).

---

## Gate 5 — Adversarial Review

≥ 3 misuse cases required; ≥ 3 of MUC-F1..F6 required (founder-facing);
≥ 2 of MUC-R1..R3 required (dual-register declared). All below are
PREVENTED with a named mechanism.

### MUC-F3 — Destructive action triggered by ambiguous phrasing (`ship`)

**Risk:** the founder says "get rid of this" / "clear it" / "drop the
change" and Claude interprets it as `ship` (or worse, a destructive
branch delete) and merges to `dev` irreversibly.
**PREVENTED:** `ship` requires an explicit yes after echoing the exact
branch + the irreversible merge step (Rule 3 prompt-before-destroy). The
skill explicitly says: never treat vague phrasing as a ship instruction;
ask what they mean. Merge only runs after `branch-ci` is green AND the
founder confirms. This is the headline destructive-action case the brief
called out.

### MUC-F1 — Operator jargon leak in a founder-visible string

**Risk:** `sulis-change` / `back_integrate_change_branch` emit `branch`,
`base_sha`, `worktree_path`, `change_id`, `spawn_result.status`,
`merge_conflict` — these bubble up untranslated into chat.
**PREVENTED:** Rule 4 translation-at-the-seam is mandated; the report
templates lead with the readable name + handle and translate every status
to plain English. Gotcha #1 names this explicitly. Raw JSON is available
only via the declared technical-mode (`--raw` / "show me the technical
version").

### MUC-F5 / MUC-F2 — Acting on stale session state without re-reading

**Risk:** `focus` trusts a `session.json` whose `pid` is dead (terminal
closed / machine rebooted) and tells the founder "switch to that window"
when there is none — or duplicates a live one by re-spawning.
**PREVENTED:** `focus` checks `kill -0 <pid>` before claiming a workspace
is live; live → point at it (no second spawn); dead/absent → re-spawn with
the same change_id. Gotcha "a session.json is not proof a terminal is
live" reinforces this.

### MUC-F4 — Number-of-items overwhelm (`list`)

**Risk:** a founder with many in-flight changes gets a 20-row wall.
**PREVENTED:** `list` caps at ~10 most-recent with a "+N more" line, one
scannable row each, ordered most-recent-first (Rule 4).

### MUC-R1 — Technical-mode leaks into founder-mode default

**Risk:** the skill emits the tools' JSON envelope when the founder
expected plain English.
**PREVENTED:** `register.founder_mode: default` declared; every report
template is plain-English; JSON is gated behind explicit technical-mode
triggers (intent / `--raw` / `/sulis:jargon`).

### MUC-R2 — Founder-mode strips an identifier the founder needed

**Risk:** the worktree path or PR URL is stripped as "jargon" but the
founder needed it to act (e.g. the manual `cd` fallback, the failing-PR
link).
**PREVENTED:** Rule 2 surfaces load-bearing identifiers in founder-mode
too — the spawn-failure fallback includes the literal `worktree_path` and
`cd … && claude --agent sulis`; the red-check path includes the PR URL.
These are signal, not jargon, and are kept.

### Audience-agnostic — Never-merge-on-red

**Risk:** Claude squash-merges even though `branch-ci` failed, landing
broken work on `dev`.
**PREVENTED:** `ship` step 4 STOPs on a failed check; merge is in step 5,
explicitly after green + confirmation. Gotcha "Never merge on a red check"
reinforces.

### Audience-agnostic — `ship` reaches `main`

**Risk:** ship is mis-targeted to `main`, bypassing the deliberate
promotion act.
**PREVENTED:** `--base dev` hard-coded in the `gh pr create` shape; the
contract and a gotcha both state ship lands on `dev` ONLY.

**Coverage:** MUC-F1, F2, F3, F4, F5 + MUC-R1, R2 + 2 audience-agnostic =
9 cases, all PREVENTED. Exceeds the ≥ 3 MUC-F and ≥ 2 MUC-R minimums.

**Gate 5: PASS.**

---

## Single filesystem check

```
test -f plugins/sulis/skills/change/VERIFICATION_REPORT.md \
  && grep -q "Verdict:.*PASS" plugins/sulis/skills/change/VERIFICATION_REPORT.md
```

Returns 0. **Skill is shipped.**
