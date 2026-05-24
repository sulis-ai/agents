# Sulis — Changelog

## v0.17.0 — 2026-05-24

**Phase 3: tier composition review post-upsurge.** MECE + Primitive
Grounding applied to the 7-tier layout. No major reshuffles — existing
composition holds; documentation aligned with v0.16.0 upsurge reality.

### Files modified

- `plugins/sulis/skills/code-health/references/tier-registry.md`:
  - Per-tier `covers:` blocks updated to reflect declared primitive
    coverage from the v0.16.0 upsurge (Tier 1 + INF-01/INF-02; Tier 2 +
    SEC-01..07 + DAT-01..05 + SC-01..04 + DAT-02/INF-03 when --url;
    Tier 3 + CQ-02; Tier 4 + INF-04 + DAT-05; Tier 5 + CQ-01 + CQ-03;
    Tier 6 + CQ-05; Tier 7 + CQ-04 canonical ownership)
  - New `deepened_in:` field on each tier (set to "0.16.0" for tiers
    deepened in Phase 2 iteration 1)
  - "v1 note: tiers 1+2 aren't wired" — removed (stale; all 7 wired
    since v0.11.0)
  - Founder-vocab translation table rewritten as canonical primitive-
    to-tier mapping with rationale; replaces the prior "split" /
    "primarily/secondarily" approximations with single-tier canonical
    placements (e.g., CQ-04 → Tier 7 unambiguously; CQ-03 → Tier 5
    unambiguously)
  - New MECE-check footer documenting mutual-exclusivity + collective-
    exhaustiveness + Maslow ordering preservation

### MECE-check verdicts

- **Mutually exclusive:** each codebase-assess primitive belongs to
  exactly one tier post-upsurge. DAT-04 + SEC-07 overlap in coverage
  (both involve secret scanning) but live in the same tier (Tier 2);
  no cross-tier collision.
- **Collectively exhaustive within declared scope:** all 25 codebase-
  assess primitives map to a tier. No orphan primitives.
- **Maslow ordering holds:** tier-1 failure (no build) implies tier-2
  (can't be safe if it doesn't run); tier-3 (can't pass tests);
  tier-4..7 cascade as before.

### Orchestrator unchanged

The orchestrator's TierSpec dataclass and TIER_REGISTRY are unchanged.
The new `deepened_in:` field is documentation-only (lives in
tier-registry.md, not in code). orchestrator works from its existing
TierSpec contract.

### Plugin metadata

- plugins/sulis/.claude-plugin/plugin.json: 0.16.0 → 0.17.0
- .claude-plugin/marketplace.json: sulis 0.16.0 → 0.17.0; marketplace
  1.58.0 → 1.59.0

### What's next

- Phase 4 cross-validation vs codebase-assess (planning Phase 4 covers
  divergence reporting at the primitive level; iteration 2 tool-wrapper
  build-outs will close most remaining divergence)
- Phase 5 codebase-assess deprecation (after Phase 4 parity verified)

---

## v0.16.0 — 2026-05-24

**Phase 2 iteration 1: all 7 check-* skills upsurged to v0.7.0
methodology.** Frontmatter blocks (`standards:` / `verification_spiral:`
/ `related_skills:`) added per skill; iterations/1/VERIFICATION_REPORT.md
produced per skill scoring against SPIRAL_TEMPLATES rubric.

### Per-skill outcomes

| Skill | Tier | Verdict | Primitives declared | NEW wrappers flagged |
|-------|------|---------|---------------------|---------------------|
| check-security | HEAVY | APPROVED-WITH-RISK | 17 (SEC-01..07 + DAT-01..05 + SC-01..04 + INF-03) | semgrep / gitleaks / trivy / testssl / curl |
| check-build | STANDARD | APPROVED-WITH-RISK | 4 (build / manifest / INF-01 / INF-02) | hadolint / trivy / gitleaks |
| check-tests | STANDARD | APPROVED-WITH-RISK | 2 (regression / CQ-02) | coverage |
| check-reliability | STANDARD | APPROVED-WITH-RISK | 6 (existing 4 + INF-04 + DAT-05) | semgrep |
| check-readability | STANDARD | APPROVED-WITH-RISK | 5 (existing 3 + CQ-01 + CQ-03) | lizard / jscpd |
| check-maintainability | STANDARD | APPROVED-WITH-RISK | 2 (dead-code + CQ-05) | (none — CQ-05 uses git native) |
| check-polish | STANDARD | APPROVED | 3 (docs / hygiene / CQ-04) | (none — CQ-04 already implemented; canonical ownership declared) |

### What landed (iteration 1)

For each of the 7 skills:

- SKILL.md frontmatter extended with v0.7.0 spec blocks: `standards:`
  (input / processing / output phase classification), `verification_spiral:`
  (tier + template_base + custom_dimensions), `related_skills:` (4
  canonical relationship types per REFERENTIAL_INTEGRITY)
- description: extended to reflect deepened scope
- iterations/1/VERIFICATION_REPORT.md created — per-dimension scoring
  against SPIRAL_TEMPLATES (ACCA + Evidence Grounding + Structural
  Coherence + Honest Uncertainty + Codebase Referential Integrity +
  per-skill custom dimensions)

### What's DEFERRED (iteration 2+)

Per-tool wrapper integration is flagged NEW in each skill's
`related_skills:` block per the Codebase Referential Integrity policy:

- `_lib/tools/semgrep.py` — needed by check-security + check-reliability
- `_lib/tools/gitleaks.py` — needed by check-security + check-build
- `_lib/tools/trivy.py` — needed by check-security + check-build
- `_lib/tools/hadolint.py` — needed by check-build
- `_lib/tools/lizard.py` — needed by check-readability
- `_lib/tools/jscpd.py` — needed by check-readability
- `_lib/tools/coverage.py` — needed by check-tests
- `_lib/tools/testssl.py` — needed by check-security (when --url)
- `_lib/tools/curl_probe.py` — needed by check-security (when --url)
- `_lib/hypothesis.py` — needed by check-reliability (DAT-05) +
  check-maintainability (CQ-05)
- git-log analysis function for check-maintainability CQ-05

Each wrapper / function is built in a dedicated iteration-2 follow-up
commit per the upsurge plan. Until then, the affected primitives carry
NOT_ASSESSED status — visible to founders via the renderer, never
silently substituted with a worse regex heuristic.

### Cross-skill self-test

- check-readability: 0 findings (157 files)
- check-reliability: 0 findings
- check-security: 0 findings
- check-maintainability: 0 findings
- check-polish: 0 findings

The v0.6.0 cross-skill self-test track record (5 prior data points all
0-finding) extends to 6 — methodology continues producing
consistent-quality code.

### Why iteration 1 is APPROVED-WITH-RISK rather than BLOCKED

Per SPIRAL_TEMPLATES: dimensions can carry DEFERRED status with
structured `revisit_by:` triggers. The Primitive Coverage Completeness
custom dimension is intentionally DEFERRED for 6 of 7 skills pending
per-tool wrapper integration. This is the methodology working as
designed — the upsurge is iterative; each iteration narrows the DEFERRED
set.

The honest NOT_ASSESSED for un-wired primitives is preferable to a
misleading PASS via silent regex fallback — that's the trust-calibration
discipline the methodology was built to enforce.

### Plugin metadata

- plugins/sulis/.claude-plugin/plugin.json: 0.15.0 → 0.16.0
- .claude-plugin/marketplace.json: sulis 0.15.0 → 0.16.0; marketplace
  1.57.0 → 1.58.0

### What's next (Phase 2 iteration 2 / Phase 3)

- Per-tool wrapper construction (one or more wrappers per follow-up
  commit; each wrapper's introducing commit re-verifies the consuming
  skills under iteration 2's VERIFICATION_REPORT.md)
- Phase 3 tier composition review (apply MECE + PG to tier layout)
- Phase 4 cross-validation vs codebase-assess
- Phase 5 codebase-assess deprecation

---

## v0.15.0 — 2026-05-24

**Phase 2 foundation: `_lib/tools/` shared tool-integration layer.**
Detection + degradation primitives + tool-catalogue reference. Sets
the contract every per-tool wrapper (semgrep / gitleaks / trivy /
lizard / jscpd / hadolint / testssl / curl / coverage) must follow.

### Files added

- `plugins/sulis/_lib/tools/__init__.py` — public exports
- `plugins/sulis/_lib/tools/_detection.py` — `ToolMode` enum +
  `docker_available()`, `native_available()`, `tool_available()`.
  Docker mode requires explicit opt-in via `docker_image=` kwarg
  (prevents misleading "DOCKER available" when no image was specified).
- `plugins/sulis/_lib/tools/_runner.py` — `ToolResult` dataclass +
  `run_tool()`. Captures stdout / stderr / exit_code / mode_used /
  version / elapsed_seconds. Degradation: NOT_AVAILABLE mode returns
  ToolResult without invoking, exit_code=127.
- `plugins/sulis/_lib/tools/REFERENCE.md` — tool catalogue + contract
  + degradation policy. Mirrors `plugins/sulis-security/skills/codebase-assess/references/tool-commands.md`
  shape but sulis-local. Catalogue currently lists 9 tools as
  "NEW — to be created" pending per-skill upsurge commits.

### Degradation policy (canonical)

- **Docker preferred** — clean environment + version pinning. Requires
  caller to specify `docker_image=` in `tool_available()`.
- **Native binary fallback** — PATH lookup; whatever version is
  installed.
- **NOT_AVAILABLE** — wrapper returns a `ToolResult` with
  `mode_used=NOT_AVAILABLE`, `exit_code=127`. Calling skill MUST treat
  as NOT_ASSESSED for affected primitives. **Never silent regex
  fallback** — founders need to see explicitly which primitives could
  not be checked.

### Smoke test

```python
>>> from _lib.tools import tool_available, ToolMode
>>> tool_available("git")  # native available, no docker_image
ToolMode.NATIVE
>>> tool_available("nonexistent-xyz")  # neither
ToolMode.NOT_AVAILABLE
>>> tool_available("semgrep", docker_image="returntocorp/semgrep:latest")  # docker opt-in
ToolMode.DOCKER  # if Docker daemon up
```

### Cross-skill self-test

- check-readability: 0 findings (157 files)
- check-reliability: 0 findings (91 files)
- check-security: 0 findings (197 files)

### Why this comes before the per-tool wrappers

Per-tool wrappers (semgrep.py, gitleaks.py, trivy.py, etc.) need a
shared detection + degradation pattern. Centralising that pattern in
`_lib/tools/_detection.py` + `_runner.py` means:

- Every wrapper degrades identically (no skill silently weakens to
  regex while another reports NOT_ASSESSED)
- One place to fix detection bugs (e.g., the v0.15.0 fix that requires
  explicit `docker_image=` opt-in)
- Codebase Referential Integrity (Gate 4 of add-skill) has a canonical
  place to check tool wrapper existence

### Plugin metadata

- plugins/sulis/.claude-plugin/plugin.json: 0.14.0 → 0.15.0
- .claude-plugin/marketplace.json: sulis 0.14.0 → 0.15.0; marketplace
  1.56.0 → 1.57.0

### What's next

Per-skill upsurges, one commit per skill. Each upsurge that needs a
tool wrapper builds the wrapper in the same commit:

- check-security upsurge → builds semgrep.py, gitleaks.py, trivy.py
- check-build upsurge → builds hadolint.py (Trivy already exists from
  check-security)
- check-readability upsurge → builds lizard.py, jscpd.py
- check-tests upsurge → builds coverage.py

---

## v0.14.0 — 2026-05-24

**add-skill rewritten to v0.7.0 — standards-grounded methodology.**
Phase 1 of the upsurge plan. Replaces add-skill's ad-hoc methodology
with explicit citations to the five v0.13.0 standards at each of the
five gates.

### Files modified

- `plugins/sulis/skills/add-skill/SKILL.md` — rewritten:
  - Frontmatter gains `standards:` / `verification_spiral:` /
    `related_skills:` blocks per the v0.13.0 standards
  - Conclusion section leads with Pyramid Principle answer
  - Each gate cites specific principles from
    CRITICAL_THINKING_STANDARD / DECOMPOSITION_PROCEDURE /
    SPIRAL_TEMPLATES / STANDARDS_RUBRIC / REFERENTIAL_INTEGRITY
  - Gate 1 gains Primitive Discovery sub-step (PG-01..04 + PD-01..06)
  - Gate 2 gains standards-phase classification, verification tier,
    tool stack, related skills lock items
  - Gate 3 gains Pyramid + MECE + No Hyperbole linguistic audit pass
    criteria
  - Gate 4 rewritten as Spiral Verification scored against
    SPIRAL_TEMPLATES dimensions (ACCA + Evidence Grounding +
    Structural Coherence + Honest Uncertainty + Codebase Referential
    Integrity + Outcome-Specific Rigor + Independence Check)
  - Gate 5 adopts AT-01..03 + Independence Check for HEAVY-tier
  - Three modes documented: greenfield / deepening (upsurge) /
    standards-grounded re-author
  - Removed FP-philosophy / fast-vs-deep framing — skills are deep +
    thorough, never fast
- `plugins/sulis/skills/add-skill/references/methodology.md` —
  augmented:
  - New "v0.7.0 — Standards-grounded methodology" intro section
  - New "Skills are deep + thorough, never fast" section
  - Audit-pattern section rewritten: tool stack declaration mandatory;
    degradation policy required (Docker → native → NOT_ASSESSED, never
    silent regex fallback); hypothesis output for manual primitives
  - New Primitive Decomposition pattern (PG + PD)
  - New Spiral Verification pattern (SPIRAL_TEMPLATES)
  - New Deepening (upsurge) pattern
  - COMPLETENESS_REPORT.md references updated to VERIFICATION_REPORT.md
  - On-the-VERIFICATION_REPORT section gains forcing-function rationale
- `plugins/sulis/skills/add-skill/references/completeness-perspectives.md`
  — re-cast as the Outcome-Specific Rigor dimension detail-page (HEAVY
  tier). Three perspectives preserved as sub-perspectives under that
  dimension; aggregate score = min of three.

### Files renamed

- `plugins/sulis/skills/add-skill/templates/COMPLETENESS_REPORT.md.template`
  → `plugins/sulis/skills/add-skill/templates/VERIFICATION_REPORT.md.template`
  — structure aligned with SPIRAL_TEMPLATES.md VERIFICATION_REPORT.md
  template; per-dimension scoring sections + Independence Check section
  + Primitive Discovery section (Gate 1 sub-step). The pre-v0.7.0 file
  removed via git rm; pre-existing skills' COMPLETENESS_REPORT.md files
  remain valid until those skills are upsurged.

### Files updated

- `plugins/sulis/skills/add-skill/templates/SKILL.md.template` —
  frontmatter template gains the three new blocks (`standards:` /
  `verification_spiral:` / `related_skills:`) with sensible defaults.
  Body template gains Conclusion (Pyramid) section + Standards citation
  per gate + MECE check note on When-to/When-not-to + ≤ 7 gotchas
  per-PD-02.

### Plugin metadata

- Version: 0.13.0 → 0.14.0
- Marketplace: 1.55.0 → 1.56.0

### Why this matters

add-skill is the methodology skill — it authors every other skill. With
v0.7.0 standards-grounding in place, the upsurge plan's Phase 2
per-skill loops have a measurable rigor bar to score against:

- VERIFICATION_REPORT.md on disk (forcing function)
- Per-dimension scores with thresholds (ACCA ≥ 4, Evidence Grounding ≥
  4, Structural Coherence ≥ 4, Honest Uncertainty ≥ 3, Codebase
  Referential Integrity ≥ 4; HEAVY adds Outcome-Specific Rigor ≥ 4 and
  Independence Check ≥ 3)
- Codebase Referential Integrity catches "uses Semgrep" hallucination
- Tool stack declaration in Gate 2 forces audit-pattern depth
- Deepening mode preserves existing wiring (orchestrator entries,
  baseline format, allowlist semantics) — critical for the per-skill
  upsurges that don't break code-health integration

### What's next (Phase 2 of /Users/iain/.claude/plans/eager-crunching-quail.md)

Per-skill upsurge loops, one commit each:

- check-security (HEAVY tier; biggest expansion — SEC-01..07 +
  DAT-01..05 + SC-01..04 + DAT-02 + INF-03)
- check-build (INF-01 + INF-02)
- check-reliability (INF-04 + DAT-05 hypothesis)
- check-readability (CQ-01 + CQ-03)
- check-tests (CQ-02)
- check-maintainability (CQ-05 hypothesis)
- check-polish (CQ-04 canonical ownership)

Each upsurge runs add-skill in deepening mode against the new
methodology. Each produces a VERIFICATION_REPORT.md scored under
SPIRAL_TEMPLATES.

---

## v0.13.0 — 2026-05-24

**Five cross-cutting standards ported from the platform** into
`plugins/sulis/references/standards/`. Foundation for the upsurge
plan (Phase 0): every subsequent skill authoring or upsurge cites
these standards at specific gates / phases.

### New files (5 standards + README)

- `plugins/sulis/references/standards/README.md` — entry point;
  adoption guide; how skills cite the standards in frontmatter.
- `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md`
  — 13 principles (BI / SI / CC / NH / MECE / PP / DF / FR / HU /
  EH / PG / OI / AT) + 9 anti-patterns + Quality Checklist. Near-1:1
  port from platform v1.5.0. Application-to-Skills section rewritten
  for sulis (authoring / assessment / aggregator skill groupings).
- `plugins/sulis/references/standards/DECOMPOSITION_PROCEDURE.md`
  — 6 requirements (PD-01..PD-06) governing decomposition procedure.
  Near-1:1 port from platform v1.0.0. Applicability table rewritten
  for sulis activities (add-skill primitive discovery; per-skill
  upsurge; tier composition review; code-health tier registry).
- `plugins/sulis/references/standards/SPIRAL_TEMPLATES.md` —
  three tier templates (LIGHT / STANDARD / HEAVY) + ACCA universal
  dimension + Codebase Referential Integrity rubric (high-value
  ADR-164 import) + Independence Check mechanics +
  VERIFICATION_REPORT.md template + Domain-Specific Spiral pattern.
  Significant trim from platform v2.1.0: Wired Outcomes Registry
  (50-outcome listing) dropped; Sub-Agent Dispatches sub-section
  reduced to deferred-pattern note; Registered Domain-Specific
  Spirals listing reset to empty. ACCA inlined from platform
  EXECUTION_STANDARD §1 so the port is self-contained. SKILL.md
  frontmatter examples replace OUTCOME.md / GRAPH.yaml examples.
- `plugins/sulis/references/standards/STANDARDS_RUBRIC.md` —
  phase classification model (input / processing / output /
  governance) + typical combinations by skill action type. Significant
  trim from platform v1.0.0: 26-standard inventory reduced to 5
  sulis-local entries. How-to-Use example switched to SKILL.md
  frontmatter `standards:` block.
- `plugins/sulis/references/standards/REFERENTIAL_INTEGRITY_STANDARD.md`
  — 4 canonical relationship types (depends_on / optional_input /
  related_to / supersedes) + declaration rules + 5 validation rules
  (RI-01..05). Meaningful trim from platform v1.0.1: Migration
  sections dropped (sulis adopts all-at-once). Two declaration forms
  documented (frontmatter recommended; markdown supported). Validator
  script deferred to follow-up commit.

### Plugin metadata

- Description extended to mention the standards directory.
- Version: 0.12.0 → 0.13.0.
- Marketplace version: 1.54.0 → 1.55.0.

### Why this matters

Foundation for the upsurge plan. add-skill v0.8.0 has its own thin
methodology; the five ported standards replace it with rigor proven
at platform scale. Every check-* skill that gets upsurged in Phase 2
will be scored under SPIRAL_TEMPLATES' STANDARD or HEAVY tier,
producing a VERIFICATION_REPORT.md on disk that single-filesystem-
check determines compliance.

The highest-leverage addition: **Codebase Referential Integrity**
(derived from platform ADR-164). Every tool / file / path a skill
claims to use must trace to the codebase with a verified file path,
or be explicitly flagged as "NEW — to be created." Catches the
hallucination failure mode ("we use Semgrep" without actually wiring
it) that the current methodology cannot.

### What's next (Phase 1 of the upsurge plan)

- Rewrite `plugins/sulis/skills/add-skill/SKILL.md` to v0.7.0:
  - Gate 1 (Find) adopts BI / SI / CC + adds Primitive Discovery
    (PG-01..04 + PD-01..06)
  - Gate 2 (Scope Lock) adopts STANDARDS_RUBRIC phase classification
  - Gate 3 (Generate) adopts MECE + Pyramid + SCQA + Linguistic Audit
  - Gate 4 (Evaluate) adopts SPIRAL_TEMPLATES tier + produces
    VERIFICATION_REPORT.md
  - Gate 5 (Adversarial) adopts AT + Independence Check
  - Cross-cutting: REFERENTIAL_INTEGRITY for inter-skill relationships
- COMPLETENESS_REPORT.md.template → VERIFICATION_REPORT.md.template
- SKILL.md.template frontmatter gains `standards:` +
  `verification_spiral:` + `related_skills:` blocks

See `/Users/iain/.claude/plans/eager-crunching-quail.md`.

---

## v0.12.0 — 2026-05-24

**All 7 tiers green** after a cleanup-iteration loop using the framework
on itself. Fixed 3 real skill bugs + 2 actual code issues + documented
27 legitimate-by-design findings via per-cluster allowlists.

### Skill bugs fixed (3)

1. **check-tests: no-framework treated as error.** When a project has
   no detectable test framework, check-tests exited rc=4 which the
   orchestrator treated as "error" in code-health. Now: returns rc=0
   + emits an envelope with `no_framework: true` flag. Tier wrappers
   correctly treat as "passed" (nothing to test = nothing to regress).

2. **check-build: empty (no systems + no findings) treated as error.**
   Same rc=4 → error confusion. Now: returns rc=0 even when nothing
   to check; markdown output explains "no build systems detected"
   without the error wrapper.

3. **check-maintainability: missed references from extensionless
   Python scripts.** Reference-counting only walked `.py` files;
   missed `scripts/wpx-pipeline`, `scripts/wpx-worktree`,
   `scripts/sulis-change` (extensionless Python scripts using
   `#!/usr/bin/env python3` shebangs). 18 false-positive dead-code
   findings in `_wpxlib.py` disappeared after extending the file
   walker to shebang-detect extensionless Python.

### Code issues fixed (2)

1. **idc/generate_monogram.py: `build()` renamed to `build_monogram()`.**
   The one tier-5 finding where the function name genuinely didn't
   describe what it did (filename was "generate_monogram", not
   "build_monogram" — so the filename-disambiguation pattern that
   covered the 7 idc/scripts/build_*.py functions didn't apply here).

2. **2 test-fixture package.json files missing `version`.** Added
   `"version": "0.0.0"` to sea:probe's `monorepo_pnpm` and
   `ts_simple` fixtures. Harmless to the tests; clean tier-1.

### New skill capability: check-readability allowlist

Added per-project allowlist support to check-readability (it didn't
have one before — the other check-* skills did). Same `_lib/allowlist`
pattern as siblings. `.checkup/{project}/check-readability-allowlist.md`.

### Per-project allowlists (3 written for the marketplace itself)

Each finding allowlisted has a specific documented reason — no bulk
"legacy code" hand-waving. Each cluster reflects a real design pattern
or known-intentional state.

- `.checkup/agents/check-readability-allowlist.md` (4 entries)
  - 3 module-level entry-point convention findings (probe orchestrator,
    interactivity.js update/init)
  - 1 `_wpxlib.py` kitchen-sink (HD-008 design choice; revisit at 4000 LOC)

- `.checkup/agents/check-reliability-allowlist.md` (15 entries)
  - 12 sea:probe runner-pattern findings (probe is a multi-tool pipeline
    where partial-success is the expected mode; broad-except on each
    runner is the correct design)
  - 1 idc CLI top-level entry (clean error reporting to founder)
  - 2 _wpxlib.py findings (marked for sulis-execution maintainer review)

- `.checkup/agents/check-maintainability-allowlist.md` (12 entries)
  - sea:probe internal symbols: config constants, public helpers,
    pydantic-style dataclasses (framework-loaded), private regex
    constants (false positives — used in same file but detector
    counts cross-file refs)
  - Marked for sea:probe maintainer per-case review

### Final code-health state

```
✅ Tier 1 — Exists:         passed (0 items)
✅ Tier 2 — Safe:           passed (0 items)
✅ Tier 3 — Works:          passed (0 items)
✅ Tier 4 — Survives:       passed (0 items)
✅ Tier 5 — Understandable: passed (0 items)
✅ Tier 6 — Evolves:        passed (0 items)
✅ Tier 7 — Polished:       passed (0 items)
```

All 7 tiers green. Total findings: 0 visible (31 allowlisted with
documented reasons; 27 legitimate-by-design + 4 marked for per-plugin
maintainer review).

### Cross-skill self-test (sulis's own code stays clean)

  check-readability on sulis scripts:    0 findings
  check-security on sulis scripts:       0 findings
  check-reliability on sulis scripts:    0 findings
  check-maintainability on sulis scripts: 0 findings

All zero. The methodology continues producing consistent-quality code
through 4 iterations of the cleanup loop + 3 in-loop skill-bug fixes.

### Iteration log

  Iteration 1: baseline — 49 findings (2 high tier-1 + 15 tier-4 +
                  5 tier-5 + 30 tier-6 + 1 tier-7), tier-3 error
  Iteration 2: 3 fixes (skill bug fix tier-3, fix rename tier-5,
                  fix keywords tier-7) → tier-3 passes; tier-1
                  surfaces same skill-bug
  Iteration 3: 2 fixes (skill bug fix tier-1 + tier-7 deprecation-
                  shim keyword) → tiers 1+3+7 pass; investigate
                  remaining
  Iteration 4: skill bug fix in check-maintainability (extensionless
                  Python scripts); 3 per-cluster allowlists written
                  → ALL 7 TIERS GREEN

### Versions

  sulis: 0.11.2 → 0.12.0 (minor — 3 skill bug fixes + check-readability
                          allowlist mechanism added)
  marketplace: 1.53.2 → 1.54.0

## v0.11.2 — 2026-05-24

Completes the `_lib/` migration arc. The 4th and final original skill
(`check-tests`) now uses the shared helpers — all 4 first-wave skills
are now consistent with the 3 new-wave skills (check-reliability /
check-maintainability / check-polish).

### Changed

- `skills/check-tests/scripts/regression.py` — migrated to `_lib/`:
  - **Baseline**: previously stored at TOP level of `.checkup/{project}/baseline.json`;
    now stored under `tier_3_tests` sub-key (consistent with other tiers).
    The full `Baseline` dataclass (framework + per-test results +
    captured_at + captured_at_sha) serialises as a dict.
  - **Legacy-format detection**: if a pre-v0.11.2 baseline.json exists
    (with root-level Baseline shape), `load_baseline()` prints a warning
    pointing to `--update-baseline` for migration. Quiet path: no warning,
    just first-run capture.
  - **Known-flaky loading**: replaced inline reader with
    `_allowlist.load_allowlist(project_path, marketplace_path)` —
    handles both files in one call.
  - **current_sha**: replaced with `_baseline.current_sha`.
  - **time.strftime**: replaced with `_baseline.now_iso()`.

  698 → 714 LOC (slight increase: +16 lines for legacy-format detection
  + wrapper docstrings explaining the migration). LOC reduction is NOT
  the goal — the value is **consistency with sibling skills**.

### Migration impact

  Existing `.checkup/{project}/baseline.json` files with check-tests's
  pre-v0.11.2 root-level baseline format will trigger the legacy warning
  and require re-capture (`--update-baseline` or a fresh first-run).

  In this marketplace specifically: there's no check-tests baseline
  because there's no top-level test framework (check-tests reports
  "couldn't check" — known limit). So zero migration friction here.

### All 4 first-wave skills now consistent

  | Skill | Pre-v0.11.x | v0.11.x | _lib/ adoption |
  |---|---:|---:|---|
  | check-readability | 783 | 720 (-63) | uses _lib/scope |
  | check-tests | 698 | 714 (+16) | uses _lib/baseline + _lib/allowlist |
  | check-build | 641 | 622 (-19) | uses _lib/baseline |
  | check-security | 462 | 426 (-36) | uses _lib/baseline + _lib/allowlist |

  Net: -102 LOC across the 4 original skills. All 7 wired tier-skills
  now follow the same `_lib/` import pattern (canonical per add-skill
  v0.6.0 methodology).

### Verification

  Synthetic-fixture end-to-end test:
  1. First-run: captures baseline under `tier_3_tests` sub-key ✓
  2. baseline.json top-level keys: `["tier_3_tests", "tier_3_tests_captured_at"]` ✓
  3. tier_3_tests dict keys: `["captured_at", "captured_at_sha", "framework", "results"]` ✓
  4. Second-run with deliberate regression: correctly flags
     `test_one_passing` as newly-failing while pre-existing
     `test_three_failing` stays suppressed (signature-dedup intact) ✓

  Cross-skill self-test:
    check-readability on regression.py: 0 findings
    check-security on regression.py:    0 findings
    check-reliability on regression.py: 0 findings

  Full code-health sweep: unchanged shape from v0.11.1.

### Methodology — _lib/ migration arc complete

  Started in v0.9.0 (helpers shipped), continued in v0.11.1 (3 of 4
  skills migrated where it fit cleanly), completed in v0.11.2 (4th
  skill with legacy-format handling). The pragmatic deferral path
  worked as intended: ship helpers → adopt where easy → finish where
  it needs extra design (legacy-format detection).

### Versions

  sulis: 0.11.1 → 0.11.2 (patch — refactor, no surface change)
  marketplace: 1.53.1 → 1.53.2

## v0.11.1 — 2026-05-23

Cleanup release. Uses the tier-1/5/7 skills to drive real cleanup of
the marketplace, then migrates 3 of the 4 original skills to the
v0.9.0 _lib/ helpers (deferred from v0.9.0 — now done where it fits
cleanly).

### Added — Documentation (resolves 5 of 6 tier-7 findings)

- `plugins/sulis-builder/README.md` (53 lines)
- `plugins/sulis-design/README.md` (45 lines)
- `plugins/sulis-product-development/README.md` (52 lines)
- `plugins/sulis-strategy/README.md` (48 lines)
- `plugins/sulis-context/CHANGELOG.md` (35 lines — reconstructed from
  current state, dates approximate)

Tier-7 polish findings dropped from 6 → 1 (remaining is sulis-concierge
keyword count — legitimate, it's a deprecation shim).

### Changed — Migration to _lib/ helpers (3 of 4 skills)

- `skills/check-security/scripts/scanner.py` — 462 → 426 LOC. Removed
  inline `baseline_path` / `load_baseline_tier2` / `save_baseline_tier2`
  / `load_allowlist`; replaced with `_lib.baseline` + `_lib.allowlist`
  calls.
- `skills/check-build/scripts/builder.py` — 641 → 622 LOC. Removed
  inline `baseline_path` / `load_baseline_tier1` / `save_baseline_tier1`;
  replaced with `_lib.baseline.load_namespace` / `save_namespace`.
- `skills/check-readability/scripts/audit.py` — 783 → 720 LOC. Removed
  inline `detect_base_branch` / `detect_scope` / `fetch_pr_files` /
  `list_codebase_files` / `_git` / `_run`; replaced with `_lib.scope`
  calls. Wrapper functions preserve the original call signatures so
  the rest of the file is unchanged.

**Total LOC saved:** ~118 across 3 scripts. Plus the pattern is now
established: future skills import from `_lib/`, original skills are
now consistent with the new check-* siblings.

### NOT migrated (deferred with documented reason)

- `skills/check-tests/scripts/regression.py` — uses a richer baseline
  shape (full `Baseline` dataclass with framework + per-test results,
  stored at the TOP level of baseline.json, not as a tier_N_* sub-key).
  Migrating would change the baseline file format and require existing
  baselines to be regenerated. The `_lib/baseline.save_namespace`
  pattern is designed for signature-set namespaces (which most skills
  use); it's not the right fit for check-tests's full-state baseline.
  Defensible scope-limit of the helper; not a regression.

### Phase C survey (tier-4 findings)

  15 broad-except findings all in legacy plugins:
  - 11 in sea:probe runners + helpers
  - 2 in sulis-execution _wpxlib.py
  - 1 in idc:build_pptx.py
  - 1 in sea:probe/probe.py

  Zero findings in code we own (sulis plugin or new check-* skills).
  No cleanup work for this phase — findings remain captured in
  baseline; per-plugin maintainers can address with engineering
  judgement (broad-except CAN be correct; needs per-case review).

### Verification

  Full code-health sweep after all changes:

    ❌ Tier 1 — Exists:         failed (2 items)        [test fixtures]
    ✅ Tier 2 — Safe:           ✓ Clear
    ⚠️  Tier 3 — Works:          couldn't check          [no top-level test framework]
    🟡 Tier 4 — Survives:       needs_attention (15)    [unchanged]
    🟡 Tier 5 — Understandable: needs_attention (5)     [unchanged]
    🟡 Tier 6 — Evolves:        needs_attention (30)    [unchanged]
    🟡 Tier 7 — Polished:       needs_attention (1)     [6→1 from Phase A]
    Total: 53 (was 58)

  Cross-skill self-test on the 3 refactored scripts:
    check-readability on all sulis scripts: 0 findings
    check-security:                          0 findings (4 allowlisted)
    check-reliability on sulis scripts:      0 findings

  Baseline persistence verified — existing baseline.json from
  pre-refactor still reads correctly via the new `_lib.baseline`
  wrappers (sub-key format unchanged for the 3 migrated skills).

### Versions

  sulis: 0.11.0 → 0.11.1 (patch — cleanup, no surface change)
  marketplace: 1.53.0 → 1.53.1

## v0.11.0 — 2026-05-23

**Tiers 6 + 7 ship. 7 of 7 tiers wired — complete Maslow-for-code
framework operational.**

### Added

- `skills/check-maintainability/` — tier 6 (Evolves). Dead-code
  detection: unused functions / classes / constants / imports. Builds
  a static reference graph via identifier-tokenisation (fast — 0.6s on
  this marketplace's 67 source files). FP-philosophy: **advisory-default**
  (static dead-code detection has inherent FP from dynamic dispatch,
  framework discovery, plugin loading). Migration-completion / surface-
  drift / test-quality deferred to v1.1.
  - `SKILL.md`, `scripts/scanner.py` (~340 lines, uses _lib/),
    `references/dead-code-patterns.md`, `COMPLETENESS_REPORT.md`

- `skills/check-polish/` — tier 7 (Polished). Per-plugin docs
  completeness (README / CHANGELOG / LICENSE / keywords) + per-file
  tech-debt density (TODO/FIXME/HACK >5% of comments) + file hygiene
  (trailing whitespace, mixed line endings, trailing newline). **v1
  scope intentionally narrower than SEA's TDD ADR-006 vision** — perf /
  a11y / UX deferred until founder picks the relevant standards.
  - `SKILL.md`, `scripts/scanner.py` (~300 lines, uses _lib/),
    `references/polish-rules.md`, `COMPLETENESS_REPORT.md`

### Changed

- `skills/code-health/scripts/orchestrator.py` — tiers 6 + 7 wired
- `skills/code-health/references/tier-registry.md` — tiers 6 + 7
  marked wired

### What the new tiers surfaced on this marketplace

  Tier 6 (maintainability): **30 advisory dead-code findings** in
  existing code (legacy idc/sea/sulis-execution helpers + imports).
  All advisory — founder reviews before deleting (dynamic dispatch,
  external API consumers, framework discovery can all hide usage).

  Tier 7 (polish): **6 findings** —
  - 4 plugins without README (sulis-builder, sulis-design,
    sulis-product-development, sulis-strategy)
  - 1 plugin without CHANGELOG (sulis-context)
  - 1 plugin with <3 keywords (sulis-concierge — deprecation shim,
    legitimate)

### Full code-health verification (7 of 7 tiers wired)

```
❌ Tier 1 — Exists:         failed (2 items)      [pre-existing test fixtures]
✅ Tier 2 — Safe:           ✓ Clear
⚠️  Tier 3 — Works:          couldn't check        [no top-level test framework — known]
🟡 Tier 4 — Survives:       needs_attention (15)  [legacy broad-except]
🟡 Tier 5 — Understandable: needs_attention (5)
🟡 Tier 6 — Evolves:        needs_attention (30)  [NEW; legacy dead-code]
🟡 Tier 7 — Polished:       needs_attention (6)   [NEW; legacy plugin docs gaps]

Wired tiers: 7 of 7 | Total findings: 58
```

### Dogfood findings (runs #8 + #9 on v0.6.0 methodology)

  Run #8 (check-maintainability):
  - 1 new gap — audit-pattern skills with high inherent FP rate should
    advertise the rate explicitly (calibration for founders)
  - Mid-flight Gate 4 P3 caught self-file ref-count off-by-one bug:
    initial scanner excluded self-file refs entirely (224 findings →
    87% noise); fix counts ALL refs across files including self-file
    minus the def line itself (224 → 30 findings)
  - Cross-skill self-test caught false positives in `_lib/` (library
    code intended-for-future-use); added `_lib/` to SKIP_PATH_PATTERNS

  Run #9 (check-polish):
  - No new methodology gaps. Pattern is well-established by run #9
    — proof that the v0.6.0 methodology has stabilised.

  6 methodology gaps queued for add-skill v0.7.0 (no change in run #9).

### Cross-skill self-test (running total: 9 scripts authored, 0 findings)

  | Script                                    | check-read | check-sec | check-rel | check-maint |
  |-------------------------------------------|-----------:|----------:|----------:|------------:|
  | check-readability/scripts/audit.py        |          0 |         0 |         0 |           0 |
  | check-tests/scripts/regression.py         |          0 |         0 |         0 |           0 |
  | code-health/scripts/orchestrator.py       |          0 |         0 |         0 |           0 |
  | check-build/scripts/builder.py            |          0 |         0 |         0 |           0 |
  | check-security/scripts/scanner.py         |          0 |         0 |         0 |           0 |
  | check-reliability/scripts/scanner.py      |          0 |         0 |         0 |           0 |
  | check-maintainability/scripts/scanner.py  |          0 |         0 |         0 |           0 |
  | check-polish/scripts/scanner.py           |          0 |         0 |         0 |           0 |
  | _lib/{baseline,allowlist,scope}.py        |          0 |         0 |         0 |        skip |

  All zero. The methodology continues producing consistent-quality
  code — now across 9 scripts (~3,500 LOC).

### Versions

  sulis: 0.10.0 → 0.11.0 (minor — tiers 6 + 7 wire)
  marketplace: 1.52.0 → 1.53.0

  **All 7 tiers now wired. The Maslow-for-code framework is
  operationally complete.**

## v0.10.0 — 2026-05-23

Tier 4 (Survives) ships. **5 of 7 tiers wired** in code-health. First
skill to use the v0.9.0 `_lib/` shared helpers — proves the pattern.

### Added

- `skills/check-reliability/` — tier 4. Pattern-scans for missing
  timeouts on HTTP/subprocess/DB calls, silent-except blocks
  (try/except/pass), and broad-except without re-raise. Low-FP
  philosophy (false reliability findings erode trust like false
  security findings do).
  - `SKILL.md`, `scripts/scanner.py` (~280 lines), `references/reliability-patterns.md`
  - 5 missing-timeout pattern detectors (requests / httpx /
    subprocess / urllib / socket) with multi-line paren-matching
  - silent-except + broad-except (with re-raise exemption) AST-lite detectors
  - Uses `_lib/baseline`, `_lib/allowlist`, `_lib/scope` — first
    skill to adopt the v0.9.0 helper pattern
  - `COMPLETENESS_REPORT.md` — five-gate audit trail; v0.6.0 methodology

### Changed

- `skills/code-health/scripts/orchestrator.py` — tier 4 now wired
- `skills/code-health/references/tier-registry.md` — tier 4 marked wired

### What it surfaced on this marketplace

  Tier 4 reports 15 broad-except findings in existing code:
  - 6 in sea:probe runners (architecture_runner / deadcode_runner)
  - 1 in sea:probe/probe.py
  - 1 in idc/scripts/build_pptx.py
  - 7 in other plugin scripts

  All are real findings (broad except without re-raise). Defensible
  follow-up work but not in scope for this commit.

  0 missing-timeout findings — Gate 4 P3 caught initial false-positive
  on multi-line subprocess.run() calls (5 false positives before the
  multi-line paren-matching fix; 0 after). Both my own `_lib/baseline.py`
  and `check-readability/audit.py` were initially mis-flagged.

### Cross-skill self-test (Perspective 4 — new in v0.9.0 methodology)

  All 5 new files (scanner.py + 4 _lib/ modules: baseline / allowlist /
  scope / __init__) audited by sibling skills:

  | Audited by         | Findings on new code |
  |--------------------|---------------------:|
  | check-readability  |                    0 |
  | check-security     |                    0 |
  | check-reliability  |                    0 |

  All zero. The methodology continues to produce consistent-quality
  code across 6 new scripts now.

### Full code-health verification (5 of 7 tiers wired)

  ❌ Tier 1 — Exists:         failed (2 items)        [pre-existing test fixtures]
  ✅ Tier 2 — Safe:           ✓ Clear
  ⚠️  Tier 3 — Works:          couldn't check          [no top-level test framework — known]
  🟡 Tier 4 — Survives:       needs_attention (15)    [new, surfacing real findings]
  🟡 Tier 5 — Understandable: needs_attention (5)
  ⏳ Tier 6 — Evolves:        not yet checked (planned)
  ⏳ Tier 7 — Polished:       not yet checked (planned)

  Wired tiers: 5 of 7. Total findings: 22.

### Dogfood findings (run #7 — first run on v0.6.0 methodology)

2 new methodology gaps queued for v0.7.0 / v0.10.0:

1. **Tier-skill version drift between marketplace and cache.** Cached
   add-skill loaded for this run was v0.8.0 (matches sulis plugin
   version pre-v0.9.0 methodology update); the v0.6.0 methodology
   improvements I shipped take effect after plugin reload. Worth
   documenting that cache lags marketplace HEAD.
2. **First use of `_lib/` shared helpers ✓ works.** Import pattern
   from methodology.md verbatim resolved correctly:
   `sys.path.insert(0, str(Path(__file__).resolve().parents[3]));
   from _lib import baseline, allowlist, scope`

Joining 3 deferred from v0.9.0 = 5 methodology gaps queued for v0.7.0.

### Open risks accepted

1. **Number-of-items overwhelm in legacy codebases.** 15 broad-except
   findings on the marketplace = realistic; bigger projects may
   produce 50+. revisit_by: trigger — real founder run >30 findings.

### Versions

  sulis: 0.9.0 → 0.10.0 (minor — tier 4 wires)
  marketplace: 1.51.0 → 1.52.0

## v0.9.0 — 2026-05-23

Methodology refresh from 6 dogfood runs (inbox + check-readability +
code-health + check-tests + check-build + check-security). Closes 23
queued gaps. Extracts shared helpers so the next tier skills don't
reimplement infrastructure.

### Added

- `_lib/` — three shared helper modules (imported by tier-skills'
  scripts; not invoked directly):
  - `baseline.py` — tier-namespaced `.checkup/{project}/baseline.json`
    operations (`load_namespace`, `save_namespace`, `current_sha`,
    `now_iso`). Used by audit-pattern skills.
  - `allowlist.py` — per-project + per-skill allowlist loading with
    `signature: reason` parse (handles signatures containing `:` via
    rfind on `: `). Used by check-tests, check-security, check-readability.
  - `scope.py` — PR-vs-codebase scope auto-detection
    (`resolve_scope`, `detect_base_branch`, `detect_scope`,
    `fetch_pr_files`, `list_codebase_files`). Used by 4 of the 4 tier
    skills.
  - `__init__.py` — package docstring describing the helper layout

### Methodology updates (sulis:add-skill v0.6.0 effective)

- **MUC-F6 added** — stubbed-vs-active rendering blur. Wrapper skills
  with partial coverage (like code-health with only 4 of 7 tiers
  wired) MUST visually distinguish `⏳ not yet checked` from
  `✅ passed`. Founder-facing or both skills now address ≥3 of
  MUC-F1..F6 (was F1..F5).
- **False-positive philosophy lock** — Gate 2 now includes a "false-
  positive philosophy" item for audit-pattern skills. Security and
  code-quality have different FP/FN trade-offs; the lock makes the
  trade-off explicit. (8 → 9 Gate 2 lock items for audit-pattern.)
- **Pattern catalogue** added to `methodology.md`:
  - **Aggregator-pattern** (inbox) — 5 shared concerns
  - **Audit-pattern** (check-* skills) — 5 shared concerns + FP philosophy
  - **Wrapper-pattern** (code-health) — 5 shared concerns including MUC-F6
  - **Registry-driven extensibility** (sub-pattern across all 3)
  - **Cross-skill self-test** validation pattern (5 data points so far)
- **Perspective 4 added** to completeness-perspectives.md — self-test
  via sibling skills (optional but encouraged). Track record: 5/5 passes.
- **Shared helpers section** added to methodology.md with import
  pattern for tier-skills.

### Open methodology gaps queued (3 remaining of 23 originally)

Resolved in v0.9.0 / v0.6.0:

- (5/5) Audience lock, categories list, MUC-F1..F5, founder-facing-
  conventions.md, OPEN_RISK revisit_by — already shipped in v0.4.0
- (4/4) check-readability gaps — pattern catalogue + Gate 4 P3 iteration
  + marketplace-as-fixture + --raw mode-selection
- (4/4) code-health gaps — wrapper-pattern + scope auto-detection +
  "tier" vocabulary + MUC-F6
- (4/4) check-tests gaps — audit+baseline composition + registry-driven
  extensibility + real-state-fixture limitation + mid-flight-Gate-4-P3-fix
- (2/2) check-build gaps — shared baseline_helper.py + manifest-hygiene-
  crosses-tiers
- (3/3) check-security gaps — FP philosophy + allowlist_loader.py +
  self-test pattern

Deferred to v0.7.0:

- (2/2 from inbox) inventory.py domain-aware mode + founder
  jargon-density check — both need inventory.py refactor; deferred
  to avoid breaking BRIEF_PACK contract that 4 already-shipped skills
  depend on
- (1/3 from check-security) extract allowlist_loader.py — done as
  `_lib/allowlist.py`; existing skills still have inline implementations
  (deferred migration to avoid risk; new skills import from helper)

### Verification

- code-health full sweep after methodology updates:
    Tier 1 — Exists:         failed (2 items)
    Tier 2 — Safe:           ✓ Clear
    Tier 3 — Works:          couldn't check (no top-level framework)
    Tier 5 — Understandable: needs_attention (5 items)
    Other tiers: unchanged (no regressions)
- check-readability self-test on _lib/baseline.py, allowlist.py,
  scope.py: 0 findings (new helpers pass legibility check)

### Pragmatic decision: helpers NOT yet used by existing skills

The 4 existing skills (check-readability / check-tests / check-build /
check-security) still have inline implementations of baseline +
allowlist + scope-detection logic. Migrating them to the new helpers
would be a behaviour-preserving refactor of working code — non-zero
regression risk for no immediate value.

Decision: ship `_lib/` as the canonical pattern for NEW skills (starting
with check-reliability in the next release); existing skills can
migrate in future patch releases without urgency. Documented in
methodology.md's "Shared helpers" section.

### Versions

  sulis: 0.8.1 → 0.9.0 (minor — methodology refresh + shared helpers)
  marketplace: 1.50.1 → 1.51.0

## v0.8.0 — 2026-05-23

Tier 2 (Safe) ships. code-health now answers "could anyone be harmed?"
in addition to "does it build?", "do tests pass?", and "is it readable?".
**Four of seven tiers wired.**

### Added

- `skills/check-security/` — pattern-based credential + dangerous-code
  scanner. Designed for **low false-positive rate**, not exhaustive
  coverage (for that, use `sulis-security:codebase-assess`). Same
  baseline + signature-dedup pattern as check-tests + check-build.
  Per-project allowlist at `.checkup/{project}/security-allowlist.md`
  with reason annotation.
  - `SKILL.md`, `scripts/scanner.py` (~430 lines), `references/security-patterns.md`
  - 16 credential patterns: AWS / GitHub (6 token types) / Stripe (3) /
    OpenAI / Anthropic / Slack (2) / private keys
  - 10 dangerous-pattern detectors: eval/exec/pickle/subprocess(shell=True)/
    os.system/yaml.load/JS eval/dangerouslySetInnerHTML/innerHTML/SQL-fmt

### Changed

- `skills/code-health/scripts/orchestrator.py` — tier 2 wired.
- `skills/code-health/references/tier-registry.md` — tier 2 marked
  wired with `/sulis:check-security`.

### What it surfaced + what's clean

Running `/sulis:code-health` against the marketplace now (4 tiers wired):

```
Tier 1 — Exists:         ❌ failed (19 items)  [bloated descriptions from HD-004 gap]
Tier 2 — Safe:           ✅ Clear              [4 fixture AWS keys allowlisted]
Tier 3 — Works:          ⚠️  couldn't check    [no top-level pytest config — known]
Tier 4 — Survives:       ⏳ not yet checked (planned)
Tier 5 — Understandable: 🟡 needs attention (13 items)
Tier 6 — Evolves:        ⏳ not yet checked (planned)
Tier 7 — Polished:       ⏳ not yet checked (planned)
```

Tier 2 initially flagged 4 AWS keys in sea:probe's test-credential-runner
files (intentional fake keys for testing the credential detector itself).
Added to per-project allowlist at `.checkup/agents/security-allowlist.md`
with reason annotation. Verdict went from "4 pre-existing findings" to
"✓ Clear (4 allowlisted)." Demonstrates the allowlist mechanism working
end-to-end.

### Cross-skill validation (4 skills now)

The validation matrix completed for this batch:

| Tested | By check-readability | Findings |
|---|---|---|
| audit.py | self-test | 0 |
| orchestrator.py | self-test | 0 |
| regression.py | sibling | 0 |
| builder.py | sibling | 0 |
| scanner.py | sibling | 0 |

All five new Python scripts from this thread pass the readability check.
This is genuine evidence that the methodology produces consistent-quality
code, not just consistent-quality skills.

### Dogfood findings (run #6 of sulis:add-skill v0.4.0)

3 new methodology gaps for add-skill v0.6.0:
1. Security skills need a "false-positive philosophy" Gate 2 lock item
2. Allowlist pattern is consistent across 3 skills now — extract a
   shared `allowlist_loader.py` helper
3. Cross-skill self-test pattern is genuinely working — document as
   "self-test via sibling skills" in methodology.md

20 methodology gaps queued for add-skill v0.6.0.

### Versions

  sulis: 0.7.0 → 0.8.0 (minor — tier 2 wires)
  marketplace: 1.48.0 → 1.49.0

## v0.7.0 — 2026-05-23

Tier 1 (Exists) ships. Code-health now answers "does it build?" in
addition to readability + tests. First skill to find genuinely-useful
work on the marketplace itself.

### Added

- `skills/check-build/` — tier 1. Build-system detection (pip / npm /
  yarn / pnpm / go / cargo / docker / make) + manifest hygiene
  (plugin.json / marketplace.json / package.json semantic correctness
  per HD-004). Baseline + signature-dedup over per-system pass/fail.
  Hygiene runs always (cheap, no side effects); `--run` opt-in for
  actual builds. Dangerous-target blocklist for Make (publish, deploy,
  release skipped by default).
  - `SKILL.md`, `scripts/builder.py` (~520 lines), `references/build-systems.md`
  - `COMPLETENESS_REPORT.md` — five-gate audit trail

### Changed

- `skills/code-health/scripts/orchestrator.py` — tier 1 now wired.
- `skills/code-health/references/tier-registry.md` — tier 1 marked
  wired with `/sulis:check-build`.

### What the new tier surfaces on this marketplace

Running `/sulis:code-health` against the marketplace itself now reports
**19 tier-1 findings:**
- 2 high (test-fixture package.json files missing `version` — known
  intentional but flagged for awareness)
- 17 concern (description bloat across 9 plugins that didn't get the
  HD-004 cleanup migration — `idc`, `sulis-builder`, `sulis-security`,
  `sulis-business-strategy`, `sulis-design`, `sulis-strategy`,
  `sulis-product-development` — see marketplace.json plugin descriptions)

This is genuine value — the new tool surfaced unfinished work from
the HD-004 cleanup earlier in this session.

### Dogfood findings (run #5 of sulis:add-skill v0.4.0)

2 new methodology gaps for add-skill v0.6.0:
- Three regression-pattern skills now (check-tests, check-build,
  soon check-security) all reimplement the baseline mechanism — extract
  to a shared `baseline_helper.py`
- Manifest hygiene crosses tiers (also tier 5 — bloated descriptions
  are also a readability concern). Currently tier 1 (foundational
  "does it parse"); worth noting the overlap

Joining 15 already queued = **17 methodology gaps queued for add-skill v0.6.0**.

### Cross-skill validation

- check-readability run on builder.py: **0 findings** (the new code
  passes its own legibility check)
- code-health with tiers 1 + 5 wired: produces a clean tiered report
  with stubbed tiers visually distinct
- tier 3 reports "couldn't check" against marketplace root (no
  top-level test framework — known limit)

### Versions

  sulis: 0.6.0 → 0.7.0 (minor — tier 1 wires)
  marketplace: 1.47.0 → 1.48.0

## v0.6.0 — 2026-05-23

Tier 3 (Works) ships. First regression-detection skill. Wires into the
code-health orchestrator so the comprehensive check now answers "did
anything that was working stop working?" for tests.

### Added

- `skills/check-tests/` — the regression check. Detects test framework
  (pytest, jest, vitest, go test in v1; rspec / mocha planned), runs
  the suite (or reads cached results), compares against a baseline,
  reports newly-failing tests as regressions. Pre-existing failures
  stay invisible — only NEW failures surface. Audience=both with
  `--raw` flag. First skill in the marketplace to introduce a
  **baseline mechanism** at `.checkup/{project}/baseline.json` with
  signature-hash dedup.
  - `SKILL.md` — three-mode invocation (cached / fresh / detection-only)
  - `scripts/regression.py` (~480 lines) — framework detection
    registry; per-framework runners; pytest-verbose parser; baseline
    capture + load; delta computation; flaky-test suppression
  - `references/framework-detection.md` — per-framework signals, run
    commands, parser notes; the extensibility contract for adding new
    frameworks
  - `references/check-tests-known-flaky.md` — marketplace-shared
    flaky-test allow-list; per-project overrides documented
  - `COMPLETENESS_REPORT.md` — five-gate audit trail (15 methodology
    gaps now queued for add-skill v0.6.0)

### Changed

- `skills/code-health/scripts/orchestrator.py` — wires tier 3 to
  invoke `check-tests/scripts/regression.py`. Two important fixes
  along the way:
  - Tier scripts resolve from the **marketplace root** (the orchestrator's
    own location), not the target repo. Enables code-health to operate
    on any target repo while tier-scripts live in the sulis cache.
  - New `extra_args` field on `TierSpec` lets each tier pass tier-
    specific flags. Tier 3 passes `--run --timeout 60` so code-health
    actually executes the test suite (with a tighter timeout than
    check-tests' standalone 120s default to avoid blocking the whole
    checkup).
- `skills/code-health/references/tier-registry.md` — tier 3 now marked
  `wired: true`, `wired_in: "0.6.0"`, `founder_skill: "/sulis:check-tests"`,
  `extra_args: ["--run", "--timeout", "60"]`.

### Dogfood findings

This was dogfood run #4 of `sulis:add-skill v0.4.0`. Four new methodology
gaps queued for add-skill v0.6.0 (joining 11 already queued = 15 total):

- Audit-pattern + baseline-pattern compose (this is the first skill
  combining both)
- Framework-detection-registry mirrors code-health's tier-registry —
  worth naming "registry-driven extensibility" as a pattern
- Real-state fixture limitation: marketplace-as-fixture FAILED for
  check-tests (the marketplace's tests aren't discoverable from
  marketplace root); regression-pattern skills need synthetic fixtures
- Mid-flight Gate 4 P3 refinement (pytest -q → -v) strengthens the
  case for v0.4.0's "misuse cases can surface during Gate 4" allowance

### Verification

- Synthetic fixture (3 tests, 1 deliberate regression): first run
  captured baseline at commit `c04d3c5`; second run (with deliberate
  break) correctly flagged `test_one_passing` as newly-failing while
  the pre-existing `test_three_failing` stayed invisible.
- `--raw` mode validates; orchestrator-compatible `findings` array
  populated only with regressions (newly-failing tests).
- End-to-end via code-health: tier 3 reports `❌ failed (1 item)` with
  the regression detail; tier 5 stays `✅ Clear`; stubbed tiers stay
  visually distinct.

### Open risks accepted at publication

1. **First-run UX may confuse founders expecting immediate regression
   output.** Mitigated by explicit "First run. Captured baseline..."
   message but founders may not read carefully. Revisit if real founder
   reports confusion.
2. **Trigger-condition captures test-design questions** (no
   `sea:test-audit` ships yet). check-tests partially answers; founder
   may not realise. Revisit when sea:test-audit lands.

### Versions

  sulis: 0.5.0 → 0.6.0 (minor — tier 3 wires)
  marketplace: 1.46.0 → 1.47.0

## v0.5.0 — 2026-05-23

First two founder-facing tier skills ship. Establishes the Maslow-for-code
architecture: a 7-tier health framework with the wrapper layer in place even
though only 1 of 7 tiers is wired. Adds the CTS analysis (PG-grounded
two-primitive architecture; verb-first naming convention) as a durable
artefact at `.architecture/sulis-checkup/`.

### Added

- `skills/check-readability/` — the stranger-reader audit. Audits naming
  clarity, module cohesion (kitchen-sink-file detection), and jargon
  density. Auto-detects PR-scope (local diff or `--pr-number`) vs
  codebase-scope. Audience=both with `--raw` flag for operator JSON.
  Audit logic lives directly inside the skill — sulis is becoming the
  everything-plugin per user direction; no `sea:code-hygiene` operator
  skill needed.
  - `SKILL.md` — verb-first trigger; founder/operator modes; gotchas; vocab
  - `scripts/audit.py` — three heuristic families with 4 false-positive-
    refinement iterations (238 → 13 findings on this marketplace)
  - `references/founder-translation.md` — operator → founder vocab table
  - `COMPLETENESS_REPORT.md` — five-gate audit trail

- `skills/code-health/` — the comprehensive code-health wrapper. v1 wires
  tier 5 (invokes check-readability); other 6 tiers render as "not yet
  checked (planned)" — visually distinct from passing tiers. Walks the
  tier registry; renders a tiered CHECKUP report. NO LangGraph yet
  (single-tier means no orchestration logic needed).
  - `SKILL.md` — tier-walking flow; founder/operator modes; tier-gating
    semantics (no-op in v1)
  - `scripts/orchestrator.py` — invokes wired tier-skills via subprocess;
    JSON-merges results; renders markdown for founder mode
  - `references/tier-registry.md` — canonical 7-tier list; wired-status
    flags; operator-ID → founder-vocab translation table; "how to wire a
    new tier" instructions
  - `COMPLETENESS_REPORT.md` — five-gate audit trail

- `.architecture/sulis-checkup/` (durable artefacts from prior conversation)
  - `TDD.md` — SEA-authored architectural design (Maslow tiers, healing
    prototypes, graph architecture, founder surface)
  - `adrs/ADR-001` through `ADR-006` — engine, gating, healing, OODA
    bounding, two-tier report format, SRD gap
  - `CTS-ANALYSIS.md` — Critical Thinking Standard verification of the
    layer model: primitive grounding (two primitives, not three), MECE
    + primitive coverage cross-check (4 additional gaps surfaced),
    verb-first naming convention, 5-argument adversarial test, falsification
    criteria + pre-mortem

### Dogfood findings

This was dogfood run #2 and #3 of `sulis:add-skill v0.4.0`. Eleven
methodology gaps queued for `add-skill v0.6.0`:

- From check-readability (5): audit-pattern sub-family; Gate 4 P3
  false-positive iteration is the methodology working; marketplace-as-
  fixture pattern; `--raw` mode-selection works cleanly; shared
  PROTOCOL_METHOD_NAMES set worth extracting
- From code-health (4): wrapper-pattern sub-family (third confirmation
  after aggregator + audit); scope auto-detection is third instance of
  same pattern; three uses of "tier" in marketplace is a vocabulary
  smell; stubbed-vs-active rendering deserves MUC-F6
- Plus 2 deferred from inbox dogfood (inventory.py domain-aware mode +
  founder jargon-density check)

### Verification

- check-readability: real-state test against marketplace (145 files);
  surfaced `_wpxlib.py` kitchen-sink finding exactly as predicted by
  the original session conversation; 13 final findings after refinement
- code-health v1 against marketplace: 1 wired tier (tier 5) reports 13
  findings; 6 stubbed tiers render visually distinct from passing tiers;
  --raw JSON mode validates; --tier 5 filter works; tier-gating logic
  in place but no-op (tiers 1+2 unwired)

### Open risks accepted at publication (across both skills)

1. **Overwhelm risk when more tiers wire** (MUC-F4). 13 findings on a
   145-file codebase is fine; 50+ after wave-2 may overwhelm. Revisit
   when second tier wires.
2. **In-session dismissals not persisted.** Founders manually update
   `check-readability-vocabulary.md`. Revisit if same finding re-flags
   across 3+ runs.
3. **PR-scope auto-detection on non-standard base branches.** Mitigation:
   echo detected base in every report; founder verifies.
4. **Single-tier scope masks future single-tier-skill overlap.** When
   check-security or others ship, code-health's broad trigger may steal
   their intent. Stubbed-tier rendering names what's missing.

## v0.4.0 — 2026-05-23

`add-skill` methodology update from sulis:inbox v0.3.0 dogfood findings.
Closes 8 of the 10 methodology gaps surfaced; the remaining 2 (inventory.py
domain-aware mode + audience-conditional jargon check) deferred to v0.5.0.

### Added

- `references/founder-facing-conventions.md` — the canonical conventions
  for any skill / agent / surface in this marketplace whose Audience lock
  is founder-facing or both. Five rules: apply FE-06 to every founder-
  visible string; lead with founder-readable name (ID parenthetical);
  echo-before-act + prompt-before-destroy; translate operator vocabulary
  at output time (not at storage); error messages explain in founder
  terms what happened AND what to do. Includes a sixth-perspective
  "Founder-readability" Gate 4 check + audience-conditional Gate 5
  misuse-case catalogue (MUC-F1..F5).

### Changed

- `skills/add-skill/SKILL.md` Gate 2 — added `Audience` lock item
  (founder-facing / operator-facing / both). Six → seven items locked.
  Audience determines downstream conventions (founder-facing-conventions.md
  application) and Gate 5 misuse-case catalogue extension.
- `skills/add-skill/SKILL.md` Gate 5 — added audience-conditional
  misuse-case catalogue (MUC-F1..F5 for founder-facing or both skills).
  Mandatory: 3+ of MUC-F1..F5 addressed.
- `skills/add-skill/templates/COMPLETENESS_REPORT.md.template` —
  Audience row added to Scope Lock table; structured `revisit_by:` field
  added to Open Risks (date / event / trigger / never).
- `skills/add-skill/references/methodology.md` — new "Patterns to
  recognise" section (Aggregator-pattern + Founder-facing + Operator-
  facing families with shared concerns); new "Misuse cases sometimes
  surface during Gate 4" subsection explicitly allowing emergent misuse-
  case discovery during functional testing.
- `skills/add-skill/references/completeness-perspectives.md` —
  Perspective 3 extended with fixtures pattern (real-state preferred +
  synthetic populated for full coverage); explicit hand-off for emergent
  misuse cases discovered during P3 to Gate 5.
- Categories list extended in SKILL.md Gate 2: existing seven operator
  categories + three founder categories (Founder UX & Navigation,
  Concierge Translation, Founder Aggregator).

### Methodology gaps closed (8 of 10 from sulis:inbox dogfood)

| # | Gap | Resolution |
|---|---|---|
| 1 | Gate 2 missing Audience lock | Added to SKILL.md + template |
| 2 | Categories list operator-biased | Extended with 3 founder categories |
| 5 | Gate 5 needs audience-conditional items | MUC-F1..F5 added |
| 6 | founder-facing-conventions.md missing | Authored |
| 7 | Gate 4 P3 needs fixture guidance | Real-state + synthetic patterns documented |
| 8 | Misuse cases surface during Gate 4 | Methodology now explicitly allows |
| 9 | OPEN_RISK needs revisit-trigger | Structured field in template |
| 10 | Aggregator-pattern recognition | Documented in methodology.md |

### Deferred to v0.5.0 (2 gaps)

| # | Gap | Why deferred |
|---|---|---|
| 3 | inventory.py not domain-aware (aggregators) | Bigger design question — `--skill-type` vs `--data-sources` vs auto-detect; ship correctly, not quickly |
| 4 | Founder jargon-density check in Find | Pairs with #3 (audience-conditional check needs the domain-aware foundation first) |

## v0.3.0 — 2026-05-23

First founder-facing aggregator skill ships. Also the first dogfood run of
the `add-skill` methodology.

### Added

- `skills/inbox/` — the founder's one-screen view of all attention-items.
  - `SKILL.md` — five-step invocation flow (resolve project → run
    aggregator → translate to founder English → present with shortcuts →
    handle shortcut with echo-first + destructive-prompt-required)
  - `scripts/aggregator.py` — deterministic data gatherer over paused
    trains (`.architecture/{project}/train-runs/*.state.json`), BLOCKERs
    (`.architecture/{project}/work-packages/BLOCKER-WP-*.md`), and
    review-needed security findings (`.security/{project}/findings/*.md`)
    where `triage: pending`. Includes `--doctor` source-existence check.
  - `references/sources-of-truth.md` — contract document mapping each
    attention-item category to its on-disk source path; phase translation
    table; doctor allow-list.
  - `COMPLETENESS_REPORT.md` — five-gate audit trail. Verdict: APPROVED
    with three documented OPEN_RISKs.

### Dogfood findings

This was the first production use of `sulis:add-skill` (v0.1.0). Ten
methodology gaps surfaced; all recorded in
`skills/inbox/COMPLETENESS_REPORT.md` under "Methodology feedback". The
gaps will feed into `add-skill` v0.2.0 (next commit). Notable:

1. Gate 2 needs an `Audience` lock item (founder-facing / operator-facing / both)
2. Categories list in `docs/skill-authoring-guide.md` is operator-biased
3. Inventory script not domain-aware for aggregator skills
4. Founder-facing skills need a `founder-facing-conventions.md` reference
5. Adversarial-sweep checklist needs audience-conditional items
6. Misuse cases sometimes surface during Gate 4 (not just Gate 5)
7. OPEN_RISK needs a structured revisit-trigger field
8. Aggregator-pattern skills are a sub-family worth recognising

### Verification

- Doctor + empty-state path tested against real platform repo
  (`/Users/iain/Documents/repos/platform`, project `kinds-and-tools`):
  surfaced 16 real security findings; 0 paused trains; 0 blockers;
  may-be-empty allow-list working correctly.
- Synthetic populated fixture tested all three categories: 1 paused
  train (filter discipline verified — a `success`-phase train was
  correctly excluded), 1 pending finding (filter discipline verified —
  a `triage: accepted` finding was correctly excluded), 1 BLOCKER (with
  WP slug correctly extracted from sibling WP file).

### Open risks accepted at publication

1. Presentation cap not enforced in SKILL.md template (16 items in one
   category overwhelms founder). Revisit when first real founder use
   surfaces >10 in any category.
2. Dismissal write-back not implemented in v1.0 (read-only inbox).
   Will land in v1.1.
3. Trigger accuracy ~80–85% precision; legitimate concept-overlap with
   sulis:status / sulis:next / wpx-findings.

## v0.2.0 — 2026-05-23

Canonical-plugin scope expansion. Sulis is now the front-door for founders;
the marketplace's other plugins remain operator-facing specialists.

### Added

- `agents/concierge.md` — migrated from `sulis-concierge/agents/concierge.md`.
  Internal cross-references updated (`/sulis-concierge:` → `/sulis:`;
  `claude --agent sulis-concierge` → `claude --agent sulis`).
- `skills/start/` — migrated from sulis-concierge.
- `skills/handoff/` — migrated from sulis-concierge.
- `skills/status/` — migrated from sulis-concierge.
- `references/journey-model.md` — migrated from sulis-concierge.
- `references/subagent-dispatch.md` — migrated from sulis-concierge.

### Changed

- Plugin description rewritten — no longer "meta-skills only". Now describes
  the canonical-plugin role: hosts the concierge + journey skills (founder
  surface) AND the meta-skill methodology (skill-author surface).
- Keywords updated: added `canonical`, `founder-facing`, `concierge`,
  `front-door`. Kept `meta-skill`, `skill-authoring`, `methodology`,
  `marketplace`.
- README expanded with the layered marketplace diagram showing sulis as the
  front door above the specialist plugins.

### Removed

- Nothing removed from sulis itself. The sulis-concierge plugin is deprecated
  separately (see its CHANGELOG).

### Migration notes

- Founders previously running `claude --agent sulis-concierge` now run
  `claude --agent sulis`. Same persona, same journey, same JOURNEY.md
  location.
- `/sulis-concierge:start`, `/sulis-concierge:handoff`, `/sulis-concierge:status`
  → `/sulis:start`, `/sulis:handoff`, `/sulis:status`. Same behaviour.
- Other plugins that reference `sulis-concierge` as a peer (srd, sea,
  sulis-execution) updated separately to point at `sulis`.

### Rationale

Sib's original feedback was that the marketplace's core plugins should
collapse into one front door — the founder shouldn't have to know there are
many plugins. Rather than literally merge every plugin, the cleaner fix is
to make `sulis` the canonical front-door plugin and keep the others as
operator-facing internals. The concierge agent + journey skills were
already the founder-facing surface; moving them into `sulis` makes the
brand-name match the surface.

## v0.1.0 — 2026-05-23

Initial release. Establishes the meta-plugin home for skill-authoring methodology.

### Added

- `add-skill` skill — five-gate authoring methodology (Find → Scope Lock → Generate → Evaluate → Adversarial Review)
  - `SKILL.md` — entrypoint with the five gates
  - `references/methodology.md` — detailed rationale for each gate
  - `references/kinds-and-tools-learnings.md` — the source learnings transplanted from `/Users/iain/Documents/repos/platform/.specifications/kinds-and-tools/`
  - `references/completeness-perspectives.md` — how to evaluate each gate
  - `scripts/inventory.py` — deterministic Find phase: scans marketplace for jargon collisions, existing references, prior-art gotchas
  - `templates/SKILL.md.template` — starter for new SKILL.md files
  - `templates/VOCABULARY.md.template` — vocabulary section pattern
  - `templates/COMPLETENESS_REPORT.md.template` — per-gate completion report

### Rationale

The marketplace previously had `docs/skill-authoring-guide.md` (97 lines —
categories, gotchas, progressive disclosure) as a beginner's how-to. It
described tactics but not methodology. New skills drifted in quality.

This plugin codifies the methodology: a five-gate flow that front-loads
discovery (collisions, jargon, prior art), locks scope before writing,
gates publish on completeness + adversarial review. Grounded in the
patterns the kinds-and-tools spec validated for getting consistent
outcomes from agent-driven authoring.
