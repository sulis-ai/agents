# Methodology — Why the five gates exist

This document explains the rationale for each gate in `add-skill`. Read it
once. The SKILL.md tells you *what* to do; this tells you *why*.

The methodology is grounded in patterns the kinds-and-tools spec validated for
getting consistent outcomes from agent-driven authoring. See
`kinds-and-tools-learnings.md` for the raw source patterns.

## Why a methodology instead of a checklist

The existing `docs/skill-authoring-guide.md` (97 lines) is a checklist of
tactics: write a gotchas section, use progressive disclosure, frame the
description as a trigger condition. Each tactic is correct. The checklist still
produced inconsistent skill quality.

The reason: tactics don't compose into quality unless they are applied in the
right order against the right discovery. A skill author who writes the gotchas
section before scanning what other skills already document will produce gotchas
that overlap, conflict, or speculate. A skill author who locks the trigger
condition after drafting the body will draft the body around the wrong scope.

The methodology fixes this by structuring the *conversation*, not the artifacts.
Discovery comes first (Find). Commitment comes second (Scope Lock). Drafting
comes third (Generate). Verification comes fourth (Evaluate). Adversarial review
comes last (Adversarial Review). Each gate has explicit pass criteria; the
output is a skill plus an audit trail.

This is the same pattern the kinds-and-tools spec used to ship across 28 turns
of work without vocabulary drift: ground first, lock second, write third, verify
fourth, sweep fifth. See `kinds-and-tools-learnings.md` Section D.

## Gate 1 — Find

### What failure mode it prevents

Vocabulary collision and unrecognised prior art. Two concrete failures:

1. A new skill introduces "verify" as one of its modes; another skill already
   uses "verify" to mean something different. Claude context-switches between
   them and produces confused outputs because the terms don't compose.
2. A new skill wraps a standard from one of the marketplace's existing
   `references/*.md` files but restates it inline, drifting from the source
   over time as the source is updated.

### Why deterministic-first (the hybrid pattern)

The Find phase is HYBRID per the user's design choice: a Python script gathers
the raw inventory (skills, references, gotchas, vocabulary), and Claude
interprets the results.

The split exists because:

- A script can exhaustively enumerate every skill, every reference file, every
  gotchas section, with zero recall loss. Claude reading the marketplace
  conversationally would miss things.
- Claude's judgement is needed to decide whether a flagged collision is real
  ("verify" in two skills with different semantics) or coincidental (two
  skills both mentioning "user" in their descriptions).

This mirrors the kinds-and-tools spec's pattern: deterministic stage primitives
(`read_file`, `glob`, `ripgrep`) for gathering, LLM for the
synthesis/judgement layer.

### Why this gate cannot be skipped

The vocabulary cascade in kinds-and-tools (turn 24) was only cheap because turn
23 had already grounded the terminology against actual codebase patterns. If
you skip Find, every subsequent gate operates on assumptions instead of
evidence — and the cost of correcting those assumptions compounds as more files
get written.

## Gate 2 — Scope Lock

### What failure mode it prevents

Scope creep during drafting. Without an explicit lock, the author starts
writing SKILL.md, realises they have an opinion on tangential things, adds
them, and ships a skill that's bigger and less focused than they intended.

### Why six specific items

The six items locked at Gate 2 (name, plugin home, category, trigger
condition, top-N gotchas, depth modes) are the load-bearing decisions that
shape every other file in the skill. If any of these changes mid-draft, the
draft is wrong.

The kinds-and-tools spec's analog is the apiVersion+kind decision at turn 27.
Locking that decision early made all subsequent decisions cheaper, because
they could be made against a known surface.

### Why no item can be TBD

If something is TBD at Gate 2, it will become a default during drafting (Claude
will pick something to make progress). Defaults that get committed without
deliberate choice are how skills drift in quality.

## Gate 3 — Generate

### What failure mode it prevents

Writing the wrong skill. The drafting is constrained by the Gate 2 lock, so the
output cannot drift from the agreed scope. Templates (`templates/*.template`)
provide a starting shape so the author isn't writing from a blank slate.

### Why progressive disclosure is mandatory

A SKILL.md that inlines all rationale becomes unreadable past ~300 lines.
Claude stops consulting the bottom half. The pattern is: SKILL.md is the
instruction surface; `references/` is the rationale + long-form knowledge;
`templates/` is the structural starting point; `scripts/` is the deterministic
primitives.

This is the same find/generate/evaluate/decide split applied to the skill's
own internal layout.

## Gate 4 — Evaluate

### What failure mode it prevents

Shipping a skill that looks correct on paper but doesn't actually work. The
three perspectives target three different failure modes:

- **Trigger accuracy:** Claude won't invoke the skill when it should (or will
  invoke it when it shouldn't).
- **Gotchas coverage:** the skill's gotchas are speculative rather than
  grounded in actual failures.
- **Functional completeness:** the skill produces the wrong output, or no
  output, in real scenarios.

### Why three perspectives, not one

Each perspective targets a different failure axis. A skill can pass trigger
accuracy and still fail functional completeness (Claude invokes it correctly,
but the body doesn't produce useful output). A skill can pass functional
completeness and fail gotchas coverage (the skill works, but the gotchas
section is fluff). All three are needed.

The kinds-and-tools spec's completeness report uses five perspectives; this
skill uses three because the simpler shape (skill, not full spec) needs less
coverage. If the skill grows in complexity, add perspectives.

### Misuse cases sometimes surface during Gate 4

The five gates are sequential, but misuse-case discovery is not strictly
gate-bounded. Real-state functional testing in Gate 4 perspective 3
often reveals failure modes the author didn't anticipate at Gate 5's
abstract-thinking moment.

The methodology allows this: maintain a running misuse-case candidate
list during Gate 4; finalise + categorise (PREVENTED / OPEN_RISK) at
Gate 5. This is not a methodology violation; it's the methodology
working as designed — real evidence beats speculation.

The COMPLETENESS_REPORT.md template has space for "misuse cases
identified during Gate 4 (then formalised at Gate 5)" — use it.

### Why DEFERRED is valid but FAIL is not

DEFERRED means the perspective could not be evaluated (e.g., not enough real
scenarios available to test functional completeness on day one). DEFERRED must
be paired with a documented reason and an explicit acknowledged risk.

FAIL means the perspective was evaluated and the skill did not meet the bar.
Publishing a skill with a FAIL verdict is shipping a known-broken skill.

## Gate 5 — Adversarial Review

### What failure mode it prevents

Shipping a skill without having considered how it might be misused or
misinterpret a request. Most skills fail not because they are wrong but
because they are right under the author's mental model and wrong under
another reader's.

### Why borrowed from kinds-and-tools turn 28

The kinds-and-tools spec achieved its "specified" status only after turn 28's
adversarial sweep produced MISUSE_CASES.md. Before that, the spec passed
completeness checks but had not been stressed against hostile or naive use.
The sweep flipped one perspective from PASS to FAIL and triggered negative-
requirement subsections across nine FRs/NFRs.

For skills, the same pattern applies in miniature: name three ways the skill
could mislead Claude; for each, either prevent it or document the open risk.

### Why open risks must be documented, not silent

Every skill ships with some open risks; pretending otherwise is dishonest.
Documenting them (with name, impact, and rationale for acceptance) means
future authors can find them and decide whether the trade-off still holds.
Silent open risks accumulate into the kind of cumulative drift the quality
coverage matrix is meant to surface.

## Patterns to recognise

Skills cluster into recognisable families. The methodology applies to all of
them, but each family has shared concerns worth knowing about.

### Aggregator-pattern skills

A skill that reads from multiple sources and presents a unified view.
`sulis:inbox` is the prototype; future examples include `sulis:next` (over
inbox + journey state), starter-pack discovery (over template registry),
and any "what's the state of X across these N sources?" tool.

Shared concerns:

- **Source-discovery brittleness.** If a state source moves, the aggregator
  silently misses items. Mitigation: deterministic source-discovery via a
  registry or convention, plus a `--doctor` check.
- **No-cache discipline.** Aggregators must recompute on every invocation;
  caching produces stale-on-read failures.
- **Vocabulary translation at output.** Each source has its own vocabulary
  (operator); the aggregator's audience may want different vocabulary
  (founder). Translate at the seam, not at storage.
- **Filter discipline.** Aggregators include items; equally important is
  what they exclude. Verify both paths in Gate 4 P3.
- **Number-of-items overwhelm.** Real-state can surface more items than
  expected (inbox's first real test surfaced 16 findings). Plan a
  presentation cap from the start.

If the skill being authored is an aggregator, all five concerns should
become gotchas in Gate 2 — they ground in concrete prior failures from
HD-008 (source brittleness, no-cache) and inbox's own Gate 4 (overwhelm,
filter discipline).

### Audit-pattern skills

A skill that walks source code looking for issues per a pattern catalogue,
reports findings, supports baseline-aware regression detection.
`sulis:check-readability` is the prototype; `check-tests`, `check-build`,
`check-security`, `check-reliability` all follow this family.

Shared concerns:

- **False-positive philosophy must be locked.** Different audit domains
  have different FP/FN trade-offs. Security: FPs erode trust; FNs are
  worse. Readability: FPs are noise; FNs are tolerable. State the lock
  in Gate 2 (see SKILL.md Gate 2 "False-positive philosophy" item).
- **Baseline-aware regression.** First-run captures the state; subsequent
  runs report what's NEW since baseline. Use the shared
  `plugins/sulis/_lib/baseline.py` helper (tier-namespaced sub-keys in
  `.checkup/{project}/baseline.json`).
- **Allowlist mechanism.** Some findings are intentional (test fixtures,
  domain vocabulary, conscious accept). Use the shared
  `plugins/sulis/_lib/allowlist.py` helper for per-project + per-skill
  allowlist loading.
- **Pattern-registry extensibility.** Adding a new pattern shouldn't
  require rewriting the scanner. Use a registry list of `Pattern` /
  `Framework` / `Heuristic` entries; document the "adding a new entry"
  contract in the skill's `references/` doc.
- **In-loop Gate 4 P3 refinement is the methodology working.** Real-state
  testing surfaces false positives that pure-thinking misses. Iterate
  the heuristic during Gate 4 P3 (running candidate misuse-case list
  documented in COMPLETENESS_REPORT.md), then formalise at Gate 5.

If the skill being authored is an audit, all five concerns should
become gotchas at Gate 2.

### Wrapper-pattern skills

A skill that orchestrates other skills, presenting a unified view.
`sulis:code-health` is the prototype; future examples include skill
composition pipelines.

Shared concerns:

- **Stubbed-vs-active distinction (MUC-F6).** When wrapping a registry
  of N skills where K < N are wired, the unwired tiers MUST render
  visually distinct from passing ones. `⏳ not yet checked (planned)`
  vs `✅ Clear`.
- **Registry-driven extensibility.** Adding a wired tier is a registry
  update (the `wired:true` + `invoke_script` flag flip) — not an
  orchestrator rewrite. Pattern same as audit-pattern's pattern-registry.
- **Per-tier extra_args.** Different tiers need different invocation
  flags (check-tests needs `--run`; check-readability doesn't). Each
  TierSpec carries `extra_args: list[str]`.
- **Marketplace-root vs target-root resolution.** Tier scripts live in
  the marketplace (where the orchestrator lives); they OPERATE on a
  target repo (where `--repo-root` points). Resolve tier scripts from
  `Path(__file__).parents[N]` (marketplace), not `--repo-root` (target).
- **Output contract.** Each wired tier emits `--raw` JSON with a common
  shape including `findings[]` so the orchestrator can aggregate
  uniformly.

### Registry-driven extensibility (sub-pattern)

Aggregator + audit + wrapper skills all benefit from registry-driven
extensibility: the entry-list lives separately from the engine. Adding
a new entry doesn't touch the engine code. Examples:

- `check-tests` framework-detection registry (`KNOWN_FRAMEWORKS`)
- `check-build` build-system registry (`KNOWN_SYSTEMS`)
- `check-security` pattern catalogue (`CREDENTIAL_PATTERNS` + `DANGEROUS_PATTERNS`)
- `code-health` tier registry (`TIER_REGISTRY`)

The contract: an entry is a dataclass with detection/match criteria +
the action (command / regex / sub-skill invocation). The engine walks
the list generically. Document the "adding a new entry" contract in
the skill's `references/`.

### Founder-facing skills (any family)

Subject to `plugins/sulis/references/founder-facing-conventions.md` —
FE-06 application, no internal IDs in chrome, echo-before-act,
prompt-before-destroy, error-as-resolution-guidance, vocabulary
translation at output.

### Operator-facing skills (any family)

Free to use technical vocabulary directly; audience preference. The
conventions doc explicitly does NOT apply.

### Cross-skill self-test (validation pattern)

When authoring multiple skills in a batch, run each newly-authored
skill against ITS OWN code via sibling skills. Example:

- After authoring `check-tests`, run `check-readability` against
  `regression.py` → expect 0 findings (the new code passes its own
  legibility check).
- After authoring `check-build`, run all sibling skills against
  `builder.py` → expect 0 findings each.

If a self-test produces findings, either:
1. Fix the issue in the new code (preferred), or
2. Refine the sibling skill's heuristic (if the finding is a false
   positive caused by the new code's legitimate pattern)

The cross-skill self-test pattern has accumulated 5 data points so far
(check-readability, check-tests, code-health, check-build,
check-security) — all 5 self-tests passed. Evidence the methodology
produces consistent-quality code, not just consistent-quality skills.

## Shared helpers (sulis v0.6.0+)

The audit-pattern + wrapper-pattern shared concerns are now codified
as importable helpers at `plugins/sulis/_lib/`:

- `baseline.py` — tier-namespaced `.checkup/{project}/baseline.json`
  read/write. Functions: `load_namespace()`, `save_namespace()`,
  `current_sha()`, `now_iso()`.
- `allowlist.py` — per-project + per-skill allowlist loading. Functions:
  `load_allowlist(*paths)`, `project_allowlist_path()`,
  `marketplace_allowlist_path()`.
- `scope.py` — PR-vs-codebase scope auto-detection. Functions:
  `resolve_scope()` (one-call top-level), `detect_base_branch()`,
  `detect_scope()`, `fetch_pr_files()`, `list_codebase_files()`.

New skills should import from these helpers rather than reimplementing.
Existing skills (check-readability / check-tests / check-build /
check-security) authored before v0.6.0 still have inline
implementations; migration to helpers can happen in future patch
releases without behaviour change.

Import pattern from a tier-skill's `scripts/`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import baseline, allowlist, scope
```

## On the COMPLETENESS_REPORT.md

The report is committed alongside SKILL.md. It is not metadata; it is part of
the skill's identity. Three reasons:

1. **Audit trail.** When the skill is later rewritten or deprecated, the
   report tells the next author which decisions were deliberate and which
   were deferred.
2. **Trust calibration.** A skill with PASS verdicts across all five gates is
   different from a skill with three PASSes and two DEFERREDs. Users and
   future authors should be able to see this at a glance.
3. **Process learning.** Patterns across many COMPLETENESS_REPORT.md files
   reveal where the methodology itself has gaps (e.g., if every skill defers
   the same perspective for the same reason, the methodology needs adjustment).
