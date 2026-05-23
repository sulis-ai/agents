---
name: add-skill
description: Use when the user wants to author a new skill in the Claude Code marketplace, formalise an existing repeatable workflow as a published skill, or get methodology-driven quality consistency rather than ad-hoc SKILL.md authoring. Walks a five-gate flow grounded in the kinds-and-tools spec's learnings on getting consistent outcomes from agents.
---

# Add Skill

A five-gate methodology for authoring a new skill in this marketplace.

The methodology exists because skills drift in quality when authored ad-hoc.
The fix is not a longer checklist; it is a **structured authoring conversation**
that front-loads discovery, locks scope before writing, and gates publication on
completeness + adversarial review.

If you have not read `references/methodology.md`, read it once. It explains why
each gate exists and what failure mode it prevents.

## The five gates

Each gate has explicit pass/fail criteria. Do not skip gates. Do not move
backwards from gate N to gate N-1 without a full re-author (this prevents the
silent vocabulary drift documented in `references/kinds-and-tools-learnings.md`).

The output of running this skill is two artifacts:

1. The skill itself (`plugins/<plugin>/skills/<skill-name>/`)
2. A `COMPLETENESS_REPORT.md` co-located with the skill, documenting which gates
   passed and which were deferred

### Gate 1 — Find (discovery, deterministic-first)

**Goal:** the author starts writing with full visibility into existing
vocabulary, references, prior art, and collision risks. Skipping this gate is
where skill quality decays most.

Run the inventory script:

```bash
python3 plugins/sulis/skills/add-skill/scripts/inventory.py \
  --marketplace-root . \
  --target-plugin <plugin-name> \
  --target-skill <skill-name> \
  --proposed-description "<one-line trigger condition>" \
  --proposed-vocabulary "<comma-separated terms the skill will introduce>"
```

The script produces a structured BRIEF_PACK (Markdown to stdout) covering:

- Every existing skill name + description across the marketplace
- Every `references/*.md` file (so the author sees what knowledge already exists)
- Every existing "Gotchas" section in the target plugin's domain (prior art)
- Vocabulary collision check: does the proposed terminology overlap with
  existing skills?

Then **Claude interprets** the BRIEF_PACK: are the flagged collisions real or
coincidental? Is there an existing skill that already does most of what's
proposed? Is there a reference doc that should be wrapped rather than restated?

**Pass criteria for Gate 1:**

- BRIEF_PACK has been produced and the author has reviewed it
- Any flagged collisions are either resolved (rename / merge / clarify) or
  explicitly waived with a one-line reason
- The author has confirmed there is no existing skill that already covers this

### Gate 2 — Scope Lock (decide phase)

**Goal:** the skill's scope, category, trigger condition, and top-N gotchas are
written down BEFORE drafting SKILL.md. This prevents scope creep during drafting.

The author commits to:

- **Skill name** (kebab-case; verified non-colliding via Gate 1)
- **Plugin home** (which plugin will own it; create new plugin only if no existing one fits)
- **Category** from `docs/skill-authoring-guide.md` (Library/API Reference,
  Product Verification, Data Fetching, Business Process, Code Scaffolding, Code
  Quality, Runbook) — pick exactly one
- **Trigger condition** (the one-line `description:` field — a trigger, not a
  summary; see `references/methodology.md` for the convention)
- **Top 5 gotchas** the skill must address (from Gate 1's prior-art harvest plus
  the author's domain knowledge)
- **Depth modes** if the skill needs them (Quick / Full / Audit) — declare the
  selection strategy (auto / user-explicit / context-derived)

**Pass criteria for Gate 2:**

- All six items above are written down in `COMPLETENESS_REPORT.md`'s "Scope
  Lock" section (use `templates/COMPLETENESS_REPORT.md.template`)
- No item is "TBD"; if something cannot be locked, return to Gate 1

### Gate 3 — Generate (authoring, LLM-driven)

**Goal:** produce the skill files using the Gate 2 lock as the contract.

Files to produce:

```
plugins/<plugin>/skills/<skill-name>/
├── SKILL.md                  # use templates/SKILL.md.template as starter
├── references/               # optional but encouraged
│   └── <whatever>.md
├── scripts/                  # optional
└── templates/                # optional
```

The SKILL.md must:

- Have a `description:` frontmatter field matching the Gate 2 trigger condition
  verbatim
- Reference any wrapped standards via `references/` rather than restating them
- Include a `## Gotchas` section with the Gate 2 top-N (≤15 items, ordered by
  likelihood × impact)
- Include a `## Vocabulary` section if the skill introduces ≥2 domain terms (use
  `templates/VOCABULARY.md.template` as the structure)
- Use progressive disclosure: point to `references/` for long-form rationale
  rather than inlining it

**Pass criteria for Gate 3:**

- All files exist and parse (SKILL.md frontmatter is valid YAML)
- The skill matches the Gate 2 lock (scope, category, trigger condition, gotchas)
- No reference file declared in SKILL.md is missing on disk

### Gate 4 — Evaluate (verification, three perspectives)

**Goal:** prove the skill actually works before publishing it. See
`references/completeness-perspectives.md` for full criteria.

Run three perspectives:

1. **Trigger-accuracy perspective.** Hand Claude the `description:` field and
   the skill name only (no body). Ask: in what conversation contexts would
   you invoke this? Measure overlap with the intended trigger set. Threshold:
   ≥85% precision (no more than 15% false-invocations).

2. **Gotchas-coverage perspective.** Reverse the gotchas: for each gotcha, is
   there a concrete prior failure (in the BRIEF_PACK, in the author's
   experience, in another skill's history) that this gotcha would have
   prevented? Gotchas without a concrete failure source are speculation and
   should be removed.

3. **Functional-completeness perspective.** Run the skill against 3–5 real
   scenarios from its target category. For each, does Claude produce the
   promised output? Capture failure modes; surface as "required revisions"
   before Gate 5.

**Pass criteria for Gate 4:**

- All three perspectives have explicit verdicts (PASS / FAIL / DEFERRED with
  reason) recorded in `COMPLETENESS_REPORT.md`
- No perspective is FAIL (must be PASS or explicit DEFERRED with a flagged risk)

### Gate 5 — Adversarial Review (publish gate)

**Goal:** name the top three ways the skill could mislead Claude or produce
bad outcomes. For each, either prevent it in the skill or document it as an
open risk.

Per `references/methodology.md` (the kinds-and-tools turn 28 adversarial sweep
pattern), the categories to consider:

- Trigger-condition jargon leakage (Claude triggers it without context)
- Premature commitment to a reference version
- Unbounded gotchas section (grows past readable)
- Authorization leakage (skill requires a tool but doesn't declare it)
- Vocabulary collision with another skill
- Silent failure of progressive disclosure (declared reference missing)
- Trigger condition matches too broadly
- Depth-mode selection ambiguity

For each of the top 3 risks identified:

- **Name** the misuse case
- **Describe** what Claude might do wrong
- **State** what the skill does to prevent it (or mark as "open risk")

**Pass criteria for Gate 5:**

- 3+ misuse cases named in `COMPLETENESS_REPORT.md`'s "Adversarial Review" section
- All marked as either PREVENTED (with mechanism) or OPEN_RISK (with documented
  impact and rationale for accepting)

## Publishing

After all five gates pass:

1. Bump the owning plugin's version in `plugins/<plugin>/.claude-plugin/plugin.json`
2. Bump marketplace version in `.claude-plugin/marketplace.json` (minor bump if
   the skill changes the plugin's surface; patch if it's purely additive)
3. Update the plugin's `CHANGELOG.md` with a v entry naming the new skill
4. Commit + push following the project's conventional-commits style

## Gotchas

- **Do not skip Gate 1 even if you "already know" the marketplace.** The
  vocabulary cascade in kinds-and-tools (turn 24) only worked because the
  grounding from turn 23 was actually done. Skipping Gate 1 because the skill
  feels obvious is exactly when collisions slip through.
- **The `description:` field is the highest-impact text in the whole skill.**
  Claude scans it to decide whether to trigger. Write it as a trigger condition
  ("Use when …"), not a summary ("Generates …"). See `references/methodology.md`.
- **Gotchas without a concrete prior-failure source are speculation.** Gate 4
  perspective 2 will remove them; do not add them in Gate 3 to look thorough.
- **If Gate 2 cannot be locked, the problem is in Gate 1.** Do not draft SKILL.md
  with unresolved scope; the drafting process will commit you to choices you
  haven't actually made.
- **DEFERRED is a valid Gate 4 verdict; FAIL is not.** A deferred perspective
  must have a documented reason and impact. A failed perspective blocks publish.
- **The COMPLETENESS_REPORT.md is part of the skill, not metadata.** Commit it
  alongside SKILL.md. Future authors (and future-you) will read it to understand
  why the skill is shaped the way it is.
- **Re-running Gate 1 on every authoring session is cheap.** The marketplace
  changes; cached BRIEF_PACKs go stale within weeks. Don't reuse a BRIEF_PACK
  from an old authoring session.

## Vocabulary

- **Gate** — a methodology checkpoint with explicit pass/fail criteria. The
  five gates are sequential; do not skip or reverse.
- **BRIEF_PACK** — the structured output of `inventory.py`; the Find phase's
  deliverable.
- **Scope Lock** — the Gate 2 commitment that prevents scope creep during
  drafting.
- **Perspective** — one of three Gate 4 verification angles (trigger-accuracy,
  gotchas-coverage, functional-completeness). Each gets an explicit verdict.
- **Adversarial sweep** — the Gate 5 process of naming misuse cases before
  publish. Borrowed from kinds-and-tools turn 28.
- **COMPLETENESS_REPORT.md** — the per-skill audit trail documenting which
  gates passed, which deferred, and the reasons. Commits alongside SKILL.md.

## When to invoke this skill

- Author has identified a repeatable workflow and wants to publish it as a skill
- A gap exists in `docs/quality-coverage-matrix.md` and a new skill is the
  proposed fill
- An existing skill has drifted in quality and needs a methodology-driven rewrite
- Multiple skills are being authored in batch (e.g., closing several coverage
  gaps in one rollout)

## When NOT to invoke this skill

- The work is a one-off (write it inline; don't make every workflow a skill)
- The author wants to edit an existing skill (use a lighter touch; full
  five-gate is overkill for a gotchas addition)
- The proposed skill is actually a slash command, an agent, or a plugin (those
  have different shapes; this skill is specifically for skills)
