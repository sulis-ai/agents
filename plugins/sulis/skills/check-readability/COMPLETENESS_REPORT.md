# Completeness Report — sulis:check-readability

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run #2 of sulis:add-skill v0.4.0)
**Methodology:** `sulis:add-skill` v0.4.0 (five-gate)
**Source of design:** `.architecture/sulis-checkup/TDD.md` (tier 5) +
`.architecture/sulis-checkup/CTS-ANALYSIS.md` (verb naming + primitive grounding)

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 description overlaps all coincidental; 0 vocab collisions; 2 references to wrap (`boring-code.md`, `founder-english.md`) |
| 2 — Scope Lock | PASS | 7 items locked (Audience=both with mode-selection strategy declared) |
| 3 — Generate | PASS | SKILL.md + scripts/audit.py + references/founder-translation.md produced; all references verified present |
| 4 — Evaluate | PASS | All three perspectives PASS; Gate 4 P3 surfaced 4 false-positive clusters which were refined in-loop (238 → 13 findings) |
| 5 — Adversarial Review | PASS | 3 audience-agnostic + 3 of MUC-F1..F5 addressed; 2 OPEN_RISK documented |

**Publication decision:** APPROVED

---

## Gate 1 — Find

**BRIEF_PACK regenerated:** via `inventory.py --marketplace-root . --target-plugin sulis --target-skill check-readability --proposed-description "<see Scope Lock>" --proposed-vocabulary stranger-reader,legibility,jargon-density,kitchen-sink-file,naming-clarity,module-cohesion`

**Findings reviewed:** yes

**Description overlaps (5, all waived as coincidental):**

- sea:suggest-split (4 tokens) — PR-splitting operation; orthogonal scope
- sea:code-review (3 tokens) — per-PR review with multiple lenses; readability is one slice but not the focus
- sulis-context:show (3 tokens) — displays context index; different purpose
- sulis-security:codebase-assess (3 tokens) — security/quality primitives; different category
- sea:codebase-audit (2 tokens) — MECE-3 audit; covers Form pillar (modules expose contracts) — partially adjacent but produces HDs not findings

**Vocabulary collisions:** 0. All proposed terms are net-new.

**Existing references to wrap (not restate):**

- `plugins/sulis/references/boring-code.md` (8K) — Boring Code Standard. Defines simple-over-clever; directly relevant to readability heuristics.
- `plugins/sulis/references/founder-english.md` (36K) — FE-01..FE-11. Required for the founder-vocab translation in audience=both mode.

**Existing skills considered for reuse:**

- **sea:code-review** — covers quality as one of multiple lenses, but per-PR-delta only and lens-multiplexed. Not reusable as the primary audit; we cite as the per-PR-lite alternative in "When NOT to invoke."
- **sea:codebase-audit** — Form pillar overlaps with module-cohesion concept. Not reusable directly (produces HDs, requires MECE-3 framework); we cite as the deeper architectural lens in "When NOT to invoke."

**No existing skill covers this scope** (founder-facing dedicated legibility audit with PR-vs-codebase auto-scope). Gate 1 PASS.

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `check-readability` |
| Plugin home | `sulis` (canonical front-door; everything migrates here per user direction) |
| Audience | **both**. Founder default; `--raw` flag for operator output. Mode-selection strategy: **explicit-flag** — without `--raw`, runs in founder mode (FE-06-translated findings, plain-English remediation, no internal IDs in chrome); with `--raw`, returns operator-grade JSON with file:line + heuristic-name + raw metric values. founder-facing-conventions.md was read. |
| Category | **Founder UX & Navigation** (from the founder-facing categories added in add-skill v0.4.0) |
| Trigger condition | "Use when the founder wants to know if the code is clear, if a new person could read it, or if it's getting messy. Audits naming, module structure, and jargon density across the current PR or the whole codebase." |
| Top-5 gotchas | (below — each with concrete source) |
| Depth modes | None for v1. (Future: `quick` = top-5 findings only; `full` = all findings. Defer until usage shows the need.) |

### Top-5 gotchas (with concrete source)

1. **Source-discovery brittleness (PR-vs-codebase scope).** If the project uses a non-standard branch naming convention or `main`/`master`/`trunk` is mis-detected, the PR-scope mode silently audits the wrong diff.
   *Source: prior-art* — HD-008 INDEX-drift pattern; wpx-train's `_detect_branch_ci` fix (paths-ignore vs branches collision) showed the same class of source-detection brittleness. Mitigation: explicit `--base-branch` flag override; doctor sub-command to verify detection.

2. **Operator-jargon leakage to founder.** Heuristic findings reference identifiers (`_wpxlib.py`, `flip_index_status_via_cli`) that are operator vocab; founder needs plain-English equivalent.
   *Source: prior-art* — founder-english.md anchor cases 3 + 4; sulis:inbox COMPLETENESS_REPORT gotcha #2. Mitigation: in founder mode, every display string passes the FE-06 read-aloud test; technical identifiers stay parenthetical not headline; translation table in `references/founder-translation.md`.

3. **False positives on legitimate domain vocabulary.** Words like `JOURNEY`, `HARDENING_DELTA`, `WP` look like jargon to a stranger-reader but are correct domain terms in this marketplace.
   *Source: author-experience* — every codebase has its own load-bearing vocabulary; flagging them as "jargon" is a false positive. Mitigation: read `references/boring-code.md` and `references/founder-english.md` if present; treat their listed terms as established vocab; offer founder a one-key dismiss-as-domain-term shortcut.

4. **Kitchen-sink threshold is opinionated.** Calling a 3,000-LOC file a "kitchen sink" is a heuristic; the threshold matters. Too low produces noise; too high misses real cases.
   *Source: author-experience + prior-art* — `_wpxlib.py` (3,429 LOC) is the canonical kitchen-sink example we identified earlier this session; 500 LOC is too low (legitimate single-purpose modules exceed it). Mitigation: default threshold 1,500 LOC with `--kitchen-sink-threshold` override; report the threshold used so the founder can recalibrate.

5. **Destructive action ambiguity (rename suggestion).** When the audit suggests "rename `wpx` to `executor`," the founder might press a shortcut expecting it to perform the rename — when actually the skill is read-only.
   *Source: founder-facing-conventions Rule 3 (echo-before-act + prompt-before-destroy)* — operator-mode skills routinely suggest names; founder-mode is more dangerous because of the shortcut-press affordance. Mitigation: NO rename action is offered as a one-key shortcut; rename suggestions are *advisory text only*; SKILL.md explicitly says "this skill never modifies code — only reports."

### Vocabulary terms introduced

- **stranger-reader** — the lens applied: would someone new to this codebase understand what each module/function/identifier does without external context?
- **legibility** — the umbrella property the audit measures. Distinct from "readability" (which is also a name we considered for the skill but is broader and could mean prose quality). Legibility = code-specific readability.
- **jargon-density** — ratio of unexplained domain-specific terms to total identifiers in a module. Threshold-based metric.
- **kitchen-sink-file** — a single file that handles >N (default 1,500) lines covering >M (default 4) distinct concerns. Naming follows the `_wpxlib.py` archetype.
- **naming-clarity** — heuristic score for identifiers (length, jargon, abbreviation, magic-string). Per-symbol metric.
- **module-cohesion** — the inverse of kitchen-sink: how focused is each module's job? Heuristic based on function-count, concept-count, doc-coverage.

---

## Gate 3 — Generate

**Files produced:**

- `plugins/sulis/skills/check-readability/SKILL.md` — entrypoint (verb-first trigger; five-step invocation flow; two-mode output; gotchas; vocabulary; when-to / when-not-to)
- `plugins/sulis/skills/check-readability/scripts/audit.py` — three heuristic families (naming-clarity per-identifier, kitchen-sink-file per-file, jargon-density per-module); auto-detects PR-vs-codebase scope; `--pr-number` for remote PRs; `--raw` for operator JSON output; configurable thresholds
- `plugins/sulis/skills/check-readability/references/founder-translation.md` — operator → founder vocabulary translation table; verdict-strength wording; what-NOT-to-translate
- `plugins/sulis/skills/check-readability/COMPLETENESS_REPORT.md` — this file

**Scope lock adherence:** verified. Name (`check-readability`), plugin (`sulis`), Audience=both with explicit-flag (`--raw`) mode-selection, Category=Founder UX & Navigation, trigger condition matches SKILL.md frontmatter verbatim, 5 gotchas reflected in SKILL.md with concrete sources, no depth modes for v1.

**Referenced files verified present:** yes. `references/boring-code.md` exists at expected path; `references/founder-english.md` exists; `founder-facing-conventions.md` exists; project GLOSSARY discovery via vocabulary-loading.

---

## Gate 4 — Evaluate

### Perspective 1 — Trigger accuracy

**Verdict:** PASS

**Method:** mental walkthrough of 10 representative invocations.

**Test scenarios:**

| Scenario | Should trigger? | Likely to trigger? |
|---|---|---|
| "is my code getting messy?" | YES | YES (verbatim from description) |
| "can a new person read this?" | YES | YES (verbatim) |
| "are my names clear?" | YES | YES |
| "check this PR for readability" | YES | YES |
| "audit the codebase" | maybe | maybe (audit ≠ check; might route to sea:codebase-audit) |
| "find security issues" | NO (→ check-security tier 2) | NO |
| "run the tests" | NO | NO |
| "what's in my inbox?" | NO (→ sulis:inbox) | NO |
| "rename `wpx` to `executor` across the codebase" | NO (skill is read-only) | maybe (description mentions naming; could trigger; but skill won't act) |
| "are there any kitchen-sink files?" | YES | YES |

**Result:** ~85-90% precision. The "rename across codebase" case is the one false-positive risk; mitigated by the SKILL.md "When NOT to invoke" section + the no-rename-shortcut design (the skill triggers, audits, then explicitly says "I won't act — here's what to rename").

### Perspective 2 — Gotchas coverage

**Verdict:** PASS

**Result:** all 5 gotchas have documented sources:

- Source-discovery brittleness → HD-008 + wpx-train's `_detect_branch_ci` fix (prior art)
- Operator-jargon leakage → founder-english.md anchor cases 3+4 + sulis:inbox COMPLETENESS_REPORT (prior art)
- False positives on domain vocabulary → author-experience (we hit this exact pattern with the `run`/`get` false positives in Gate 4 P3 — see below)
- Kitchen-sink threshold opinionated → `_wpxlib.py` itself + this session's earlier critique (prior art)
- Destructive-action ambiguity (rename) → founder-facing-conventions Rule 3 (prior art)

5 items, ≤15 limit, ordered by likelihood × impact.

### Perspective 3 — Functional completeness

**Verdict:** PASS (with in-loop refinement)

**Scenarios tested:**

1. **Real-state fixture — marketplace itself, codebase scope.** `python3 audit.py --scope codebase` against this marketplace's 145 source files. First pass produced **238 findings**; refinements over 2 iterations brought this to **13 signal-y findings**. Critical true positive: `_wpxlib.py` correctly flagged as kitchen-sink (3,429 LOC / 25 concerns / `concern` severity) — exactly the case Iain originally raised this session.

2. **JSON output mode (`--raw`).** Validated end-to-end via pipe to `json.loads`; structure matches the `InboxEnvelope`-style contract; first finding parses cleanly.

3. **False-positive cluster discovery (emergent — informed Gate 5).** Iteration 1: `def run(self):` flagged across 50+ probe runners (protocol method, false positive). Iteration 2: `test_*` long names flagged (descriptive test names are GOOD practice). Iteration 3: short English verbs (`get`, `add`, `run`, `set`) flagged as "abbreviations" (they're real words). Iteration 4: fixture-file naming flagged. Each false-positive cluster surfaced an emergent misuse case → fed into Gate 5 via the running candidate list (per add-skill v0.4.0 methodology update).

**Failure modes captured + classified:**

- 4 emergent failure modes → all classified as `skill bug` and fixed in-loop. Now PREVENTED, not OPEN_RISK.

### Refinements applied during Gate 4 P3

| Cluster | Refinement | Outcome |
|---|---|---|
| Protocol method names (`run`/`execute`/`handle`/`get`/`set`/`add`/`find`/etc.) on classes | Added `PROTOCOL_METHOD_NAMES` set; magic-name check requires `is_class_method=False` for those | `def run(self):` no longer flagged |
| Real English short verbs flagged as over-abbreviated | Exempted `PROTOCOL_METHOD_NAMES` from over-abbreviated check (`run`/`get`/etc. are real words, not abbreviations) | `def get():` no longer flagged as too-short |
| Descriptive `test_*` names flagged as over-long | `test_file = is_test_file(rel_path); if test_file and name.startswith("test_"): continue` | `test_polyglot_enumeration_finds_pnpm_plus_aux_plus_iac` no longer flagged |
| Fixture files audited for naming + jargon | `if is_fixture_file(rel_path): return findings / skip` | `tests/fixtures/*` paths excluded from name + jargon checks |

Result: 238 → 13 findings (94% noise reduction). Remaining 13 are genuine advisories or one concern.

---

## Gate 5 — Adversarial Review

### Audience-conditional (founder-facing or both): 3+ MUC-F required

### MUC-F1: Operator jargon leak in error string — PREVENTED

- **What Claude might do wrong:** `audit.py` errors out (e.g., `gh CLI not installed`) and the raw error bubbles up to founder-mode output untranslated.
- **Mitigation:** SKILL.md step 4 + founder-translation.md mandate error-time translation. The `errors[]` array in the JSON envelope is intended for Claude to wrap/translate before showing to founder. In `--raw` mode, errors pass through; in founder mode, errors go through the table.
- **OPEN_RISK status:** PREVENTED in design; verification requires running the skill against a project where `gh` is missing (not tested in this dogfood run since gh is available locally). Revisit if any operator-mode string appears unwrapped in a founder-mode invocation.

### MUC-F3: Destructive action triggered by ambiguous founder phrasing — PREVENTED

- **What Claude might do wrong:** founder says "rename `wpx` to `executor` everywhere" — Claude reads the suggestion in the audit output and tries to apply it via Edit/Bash without confirming this is a read-only skill.
- **Mitigation:** SKILL.md explicitly says "this skill never modifies code — only reports" in three places (header description, gotchas section #5, when-NOT-to-invoke section). The audit script itself never writes to source files. Any rename is a separate engineering action requiring explicit founder consent.

### MUC-F4: Number-of-items overwhelm — PARTIALLY PREVENTED

- **What Claude might do wrong:** first iteration produced 238 findings on the marketplace; the founder bounces.
- **Mitigation in v1:** refined heuristics cap noise at ~13 findings on a 145-file codebase (well within readable). Findings ordered by severity within each heuristic group.
- **OPEN_RISK:** if a real founder project produces >50 findings, the report could still overwhelm. No explicit cap in v1.
  - **revisit_by:** trigger — "first real founder use of `/sulis:check-readability` against a 500+ file codebase surfaces >50 findings"
  - **Mitigation in the meantime:** advisory in SKILL.md to prioritise `concern` and `high` severity first.

### MUC-F5: Source-of-truth false-positive — PARTIALLY ADDRESSED

- **What Claude might do wrong:** founder previously decided "`wpx` is fine, it's our domain vocab"; the audit re-flags it on every run.
- **Mitigation in v1:** the audit reads the project's vocabulary sources (`boring-code.md`, `GLOSSARY.md`, etc.); founder can add to a `references/check-readability-vocabulary.md` allow-list. This is documented in `founder-translation.md`.
- **OPEN_RISK:** in-session dismissals (founder says "ignore that one") don't persist across runs. No `--ignore-this` flag in v1.
  - **revisit_by:** event — "founder reports same finding being re-flagged across 3+ runs"
  - **Mitigation in the meantime:** founder can add the term to the allow-list file (manual; not one-key).

### Audience-agnostic categories

### MUC: Trigger-condition jargon leakage — PREVENTED

- **What Claude might do wrong:** description uses "module cohesion" or "jargon density" (internal terms) → Claude triggers wrong contexts.
- **Mitigation:** trigger condition uses ONLY user-facing vocabulary ("if the code is clear", "if a new person could read it", "if it's getting messy", "naming, module structure, jargon density"). The technical terms appear in the body, not the trigger.

### MUC: Unbounded gotchas section — PREVENTED

- **Mitigation:** 5 gotchas in SKILL.md (well under 15 cap); any further heuristic-specific gotchas can go to `references/advanced-gotchas.md` in v1.1.

### MUC: Silent failure of progressive disclosure — PREVENTED

- **Mitigation:** Gate 3 verified all referenced files exist. The only external references are `boring-code.md` (sea plugin — verified) and `founder-english.md` (srd plugin — verified); both stable.

---

## Open risks accepted at publication

1. **>50 findings on a large founder project (MUC-F4 partial).** No explicit cap; founders may bounce. **revisit_by:** trigger — first real use against 500+ file codebase produces >50 findings. **Workaround:** documented in SKILL.md — prioritise concern/high severity first.

2. **In-session dismissals not persisted (MUC-F5 partial).** Founders manually add to `check-readability-vocabulary.md`. **revisit_by:** event — founder reports same finding re-flagging across 3+ runs. **Workaround:** allow-list file documented in founder-translation.md.

3. **PR-scope auto-detection brittleness on non-standard base branches.** Detection tries main/master/trunk then git symbolic-ref. Non-standard names need `--base-branch` override. **revisit_by:** trigger — auto-detection fails on a real project. **Workaround:** echo the detected base branch in every report; founder verifies before trusting.

---

## Vocabulary changes (during authoring)

None — the vocabulary locked at Gate 2 was used unchanged through Gate 3.

---

## Methodology feedback (running notes for add-skill v0.5.0)

Gaps surfaced during this run:

1. **Audit-pattern skills are a sub-family worth recognising** (overlaps with gap #10 from inbox dogfood). Like aggregators, audits share concerns: false-positive management, threshold opinionatedness, vocabulary-aware filtering, multi-mode output (founder/operator). Worth a Pattern entry in methodology.md if a third audit skill confirms.

2. **Gate 4 P3 false-positive iteration is the methodology working** — but the in-loop refinement was non-trivial (4 iterations). For audit-pattern skills specifically, consider a Gate 4 sub-perspective: "false-positive rate against the marketplace baseline." Documents the iteration; pins the expected noise level.

3. **Real-state fixture is the marketplace itself.** For meta-skills (operating ON the marketplace), the marketplace IS the real-state fixture. Document this pattern in completeness-perspectives.md fixtures section.

4. **Operator/founder mode-selection via `--raw` flag worked cleanly.** This is the second skill using audience=both (after sulis:inbox which used auto-detection). The `--raw` pattern is concrete enough to write into the founder-facing-conventions.md as a recommended mode-selection strategy.

5. **`run` and other protocol-method names are universally false-positive in operator skills.** If we build more code-quality skills, the PROTOCOL_METHOD_NAMES set should be shared, not re-derived. Consider extracting into a sea-side helper module that founder skills can use.

(All 5 to be folded into add-skill v0.5.0 alongside the 2 deferred from inbox dogfood — inventory.py domain-aware mode + founder jargon-density check.)
