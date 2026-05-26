# VERIFICATION_REPORT — /sulis:specify

**Skill:** `plugins/sulis/skills/specify/SKILL.md`
**Authored via:** add-skill five-gate methodology (greenfield mode)
**Verification tier:** STANDARD
**Date:** 2026-05-26
**Verdict: PASS**

---

## Gate 1 — Find (discovery + primitive discovery)

**BRIEF_PACK:** produced via
`plugins/sulis/skills/add-skill/scripts/inventory.py` (target-plugin sulis,
target-skill specify). 92 skills across 7 plugins enumerated.

**Collision check (BI-01 / SI-01):**

- No existing skill named `specify` or any `depth-mode` variant. CC verdict:
  **VALIDATED** (full marketplace enumerated; 92 skills checked).
- Nearest neighbours and the boundary against each:
  - `requirements-templates` / `requirements-validation` — owned by the
    requirements-analyst; this skill *dispatches* to that agent for deep
    mode rather than re-implementing. No vocabulary collision.
  - `draft-architecture` (design) — consumes the SPEC this skill produces;
    declared `related_to`. Distinct stage.
  - `index-specifications` — indexes deep specs' `.specifications/{name}/`
    folders; declared `related_to`. Distinct concern.
  - `change` (Phase 6a) — opens the workspace; specify is the first stage
    inside it; declared `related_to`. Distinct command.
- Vocabulary introduced (depth mode / lite / standard / deep spec / depth
  classifier / founder-facing flag) does not overlap existing skill
  vocabulary. Collisions: none.

**Primitive discovery (PG / PD):** this skill is a **facilitation +
dispatch** skill, not an analysis/audit skill. The single deterministic
primitive worth extracting is the **depth classifier** — independently
changeable, independently validatable (20 unit tests), falsifiable (a wrong
proposal is observable). It was extracted to `_specify_classifier.py` rather
than inlined, per the "extract the shared primitive" discipline. Provenance:
**extracted** from the design doc's explicit classifier spec (file count +
primitive count + founder-facing → lite/standard/deep, default standard).
Remaining skill logic (the three modes) is content/facilitation, not an
analysable primitive set — primitive decomposition otherwise **N/A**.

**Gate 1 verdict:** PASS.

---

## Gate 2 — Scope Lock

| Item | Lock |
|---|---|
| **Skill name** | `specify` (kebab; non-colliding per Gate 1) |
| **Plugin home** | `sulis` |
| **Audience** | **founder-facing** (founder-facing-conventions.md read; Rules 1-6 apply) |
| **Category** | Founder UX & Navigation (a stage entry-point in the change journey) |
| **Trigger condition** | the `description:` field — "Use when the founder is ready to write down what a piece of work should do — Stage 1 (Specify) of a change…" |
| **Standards-phase** | input: REFERENTIAL_INTEGRITY; processing: CRITICAL_THINKING + DECOMPOSITION; output: CRITICAL_THINKING + COACHING + TONE |
| **Verification tier** | STANDARD (founder-facing stage skill; orchestrates + dispatches; not a methodology/authoring skill, so not HEAVY) |
| **Tool stack** | not an audit-pattern skill (no Semgrep/Trivy/etc.). Deterministic logic via `_specify_classifier.py` (TDD'd, 20 unit tests). Justification: this is a facilitation + dispatch skill; the depth bar's "real tools not regex" rule targets analysis skills — N/A here. |
| **Depth modes** | lite / standard / deep — selection strategy: **context-derived proposal (classifier) + user-explicit confirm/override**. |
| **Register** | founder_mode: default; technical_mode via intent / `--raw` / `/sulis:jargon` |
| **Top gotchas** | 7 (classifier-proposes-founder-decides; operator-vocab leak; file_count=0 vs None; deep-is-dispatch; default-standard-out-loud; lite-means-lite; SULIS_CHANGE_ID must resolve) — within PD-02 fan-out ≤ 7 |
| **Related skills** | declared in frontmatter (depends_on classifier + _wpxlib; related_to change / draft-architecture / index-specifications; optional_input conventions + primitives) |

No item TBD. **Gate 2 verdict:** PASS.

---

## Gate 3 — Generate

Files produced:

- `plugins/sulis/skills/specify/SKILL.md`
- `plugins/sulis/scripts/_specify_classifier.py` (the extracted primitive)
- `plugins/sulis/scripts/tests/unit/test_specify_classifier.py` (20 tests)
- `plugins/sulis/skills/specify/VERIFICATION_REPORT.md` (this file)

SKILL.md conformance:

- `description:` matches the Gate 2 trigger condition. ✓
- `standards:`, `register:`, `verification_spiral:`, `related_skills:`
  frontmatter blocks present and valid YAML. ✓
- Leads with `## Conclusion` (Pyramid PP-01..04) — depth table + "proposes,
  never silently picks" up front. ✓
- `## When to invoke this skill` + `## When NOT to invoke this skill` —
  MECE (no overlap: each "NOT" routes to a distinct sibling skill). ✓
- `## Gotchas` — 7, ordered by likelihood × impact. ✓
- `## Vocabulary` — 7 domain terms defined. ✓
- Linguistic audit (NH-02): zero prohibited terms (grep-verified: no
  comprehensive/robust/powerful/seamless/leverage/etc.). ✓
- Progressive disclosure: points to `references/` + the design doc rather
  than inlining. ✓

**Gate 3 verdict:** PASS.

---

## Gate 4 — Evaluate (STANDARD tier dimensions)

| Dimension | Score | Threshold | Notes |
|---|---|---|---|
| **ACCA** (Accurate / Complete / Concise / Actionable) | 4/5 | ≥ 3 | Accurate to the design's classifier spec; complete across all 3 modes + output + dispatch; actionable (runnable Bash + python one-liners). |
| **Evidence Grounding** | 5/5 | ≥ 3 | Every behaviour traces to the design doc §"Depth modes" or to a real helper; classifier behaviour pinned by 20 passing tests. |
| **Structural Coherence** | 5/5 | ≥ 3 | Conclusion-first; steps 1→4 sequential; output + gotchas + vocabulary close it out. |
| **Honest Uncertainty** | 4/5 | ≥ 3 | Default-to-standard-on-uncertainty stated in skill AND classifier; "classifier sometimes wrong → founder confirms" surfaced as the primary safety net. |
| **Codebase Referential Integrity** | 5/5 | ≥ 3 | All 9 named entities verified on disk (see below). No unflagged new entities. |

**Codebase Referential Integrity check (verified `test -f` + `grep`):**

- `plugins/sulis/scripts/_specify_classifier.py` ✓ (NEW — created this change; `classify_depth` / `paths_touch_founder_surface` / `proposal_sentence` all present)
- `plugins/sulis/scripts/_wpxlib.py` ✓ (`resolve_current_change` def present)
- `plugins/sulis/skills/change/SKILL.md` ✓
- `plugins/sulis/skills/draft-architecture/SKILL.md` ✓
- `plugins/sulis/skills/index-specifications/SKILL.md` ✓
- `plugins/sulis/agents/requirements-analyst.md` ✓
- `plugins/sulis/references/founder-facing-conventions.md` ✓
- `plugins/sulis/references/change-primitives.md` ✓
- `plugins/sulis/docs/change-as-primitive-design.md` ✓

Storage convention: `{worktree_path}/.changes/{primitive}-{slug}.SPEC.md`
sits alongside the manifest `{worktree_path}/.changes/{primitive}-{slug}.yaml`
written by `write_change_metadata()` in `_wpxlib.py` (verified) — same
`.changes/` directory + same `{primitive}-{slug}` stem. Convention reused,
not invented.

**Functional completeness (5 scenarios run against the classifier):**

1. `fix`, 1 file, internal → **lite** ✓
2. `create`, 4 files → **deep** ✓
3. `refactor`, 4 files → **standard** ✓
4. `fix`, 1 file, founder-facing surface → **standard** (escalated) ✓
5. unknown primitive / `None` signals → **standard** (default) ✓

All 5 produce the promised proposal; 20/20 unit tests green;
`compileall` clean (3.11-safe — no backslash in f-string expressions).

**Gate 4 verdict:** PASS — all dimensions ≥ threshold.

---

## Gate 5 — Adversarial Review

Posture (AT-01): sought failure modes first. Riskiest assumption tested
first (AT-02): "does the classifier silently impose a depth?" — prevented by
the mandatory confirm step.

| # | Misuse case | Category | Disposition |
|---|---|---|---|
| 1 | **Classifier proposes the wrong depth and it runs anyway** — a one-file change that is actually load-bearing gets a lite spec the founder never wanted. | **MUC-F3** (destructive/wrong action from ambiguous signal) — founder-facing | **PREVENTED.** Step 3 makes the proposal an echo-before-act; no mode runs without explicit founder confirmation. The classifier only proposes. Stated in Conclusion + Gotcha 1. |
| 2 | **Operator vocabulary leaks** — the founder sees `primitive`, `file_count`, `founder_facing`, `change_id`, `worktree_path` in chat. | **MUC-F1** (operator-jargon leak) — founder-facing | **PREVENTED.** `proposal_sentence()` is founder-English by construction (unit test asserts the signal-names + `SPEC-`/`WP-` IDs are absent); skill routes raw signals to the `--raw`/technical version only. Gotcha 2. |
| 3 | **Writes a SPEC.md with no change** — `SULIS_CHANGE_ID` unset, skill writes a spec into cwd as a fallback, orphaning it. | **MUC-F5** (acting on absent/stale state) — founder-facing | **PREVENTED.** Step "Resolve the current change" stops on `null` and routes to `/sulis:change start`; Gotcha 7 forbids the cwd fallback explicitly. |
| 4 | **`file_count=0` skews every empty change to lite** — a brand-new change with no commits looks like "touches nothing" and the classifier leans trivial. | unknown-signal handling | **PREVENTED.** Skill instructs `None` (unknown) not `0` for no-commit changes; classifier treats `None` as uncertain → standard. Gotcha 3 + `test_missing_file_count_does_not_crash`. |
| 5 | **Deep mode re-implemented in-skill** — the skill grows its own SRD interview, drifting from the requirements-analyst owner. | single-owner drift | **PREVENTED.** Deep mode is a dispatch (`claude --agent requirements-analyst` / `subagent_type: sulis:requirements-analyst`); skill lands only a short front-door SPEC.md. Gotcha 4 + When-NOT-to-invoke. |
| 6 | **Trigger matches too broadly** — fires for any "spec" mention outside a change. | trigger over-match (audience-agnostic) | **OPEN_RISK (low).** `description` scopes to "Stage 1 (Specify) of a change" and "run inside a change"; the no-current-change branch routes out. `revisit_by:` if telemetry shows mis-fires outside changes. |

Founder-facing requirement: ≥ 3 of MUC-F1..F6 addressed → **4 addressed**
(MUC-F1, F3, F5, plus F-class signal-handling cases). ✓

AT-03: the Step 3 confirmation is a deliberate, documented user-facing
consequence (depth changes the founder's time cost), not permission-theater
— it is the one AAF-correct surface in the flow.

**Gate 5 verdict:** PASS — 6 misuse cases named; 5 PREVENTED, 1 OPEN_RISK
(low, with revisit trigger).

---

## Tests

```
plugins/sulis/scripts/tests/unit/test_specify_classifier.py — 20 passed
full unit suite — 377 passed (see note)
compileall plugins/sulis/scripts — OK (3.11-safe)
```

**Note (pre-existing flake, not a regression):**
`test_wpx_train_state_machine.py::test_train_lock_second_acquisition_raises`
in the deprecated `sulis-execution` mirror is timing-flaky under full-suite
ordering (flock release race) — it passes in isolation and on the clean tree
without these files; the same full-suite command alternates pass/fail run to
run. The new module is pure (no I/O, no shared filesystem state), so it does
not cause the flake. Flagged for branch-ci awareness.

---

## Overall verdict: PASS

All five gates pass. All STANDARD-tier dimensions meet threshold.
Codebase Referential Integrity 5/5. ≥ 3 founder-facing misuse cases
addressed. Ready to ship.
