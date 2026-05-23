# Kinds-and-Tools — Learnings Applied to Skill Authoring

This document transplants the load-bearing patterns from the kinds-and-tools
specification at
`/Users/iain/Documents/repos/platform/.specifications/kinds-and-tools/`
into the context of authoring marketplace skills. It is the source-of-truth
for *why* the five-gate methodology exists in the shape it does.

The original spec is about a YAML-template system for content-generation
pipelines. The patterns it validated for "getting consistent outcomes from
agents" are domain-independent.

## Section A — Architectural patterns borrowed

### A1. Four-stage pipeline as a meta-pattern

**Source pattern:** the spec mandates four execution stages — `find /
generate / evaluate / decide`. The same shape applies to any bounded
agent-driven workflow that produces an artifact.

**Applied here:** the five gates collapse into the four stages: Gate 1 is
*find*; Gates 2+3 are *generate* (lock the scope, then write); Gate 4 is
*evaluate*; Gate 5 is *decide* (publish, defer, or reject).

Authoring a skill is itself an agent-driven workflow producing a bounded
artifact. The same shape that runs Kind execution at runtime is the shape
that runs skill authoring at design time.

### A2. Template + work order split

**Source pattern:** the spec separates *Kind* (methodology-side template
defining a content type's instance schema and four-stage pipeline) from
*ContentBrief* (user-data-side work order that names a Kind via `kind_ref`).
This prevents conflation of "what a Goal is" with "this particular request
to produce a Goal."

**Applied here:** the methodology (`add-skill` SKILL.md + references +
templates + scripts) is the Kind; each invocation of `add-skill` against a
specific new skill (e.g., authoring `/sea:code-hygiene`) is the
ContentBrief. The methodology evolves without re-authoring in-flight skill
authorship work; specific skills can be revisited without changing the
methodology.

### A3. Front-load grounding (turns 23 → 24)

**Source pattern:** the spec's turn 24 vocabulary cascade locked four
terminology decisions and propagated them across ten artifacts in a single
pass. This was cheap only because turn 23 had grounded the terminology
against actual codebase patterns first. Skipping the grounding would have
made every subsequent cascade expensive.

**Applied here:** Gate 1 (Find) is non-negotiable. Without grounding, every
subsequent decision compounds bias. The hybrid script-then-LLM split exists
specifically to make grounding cheap and exhaustive.

### A4. Adversarial sweep (turn 28)

**Source pattern:** the spec achieved "specified" status only after turn 28
produced `MISUSE_CASES.md` — 13 misuse cases across 11 security-sensitive
surfaces. The sweep flipped Perspective 7 from PASS to FAIL and triggered
negative-requirement subsections across nine FRs/NFRs that had previously
looked complete.

**Applied here:** Gate 5 is the equivalent adversarial sweep in miniature.
A skill cannot publish without naming at least three misuse cases and
either preventing them in the skill or documenting them as open risks. The
sweep is what catches the failure modes that all four prior gates miss.

### A5. K8s convention as a tie-breaker (turn 27)

**Source pattern:** when the spec faced a naming-collision question (the
abstract `Kind` colliding with concrete `kind: Content` instances), the
team adopted the Kubernetes convention `(apiVersion, kind)` rather than
inventing new disambiguation. "The boring K8s answer wins."

**Applied here:** when a skill faces a similar design choice, prefer
existing conventions over novel patterns. SKILL.md frontmatter follows the
established `name` + `description` shape. Categories are from the existing
seven-category list in `docs/skill-authoring-guide.md`. New patterns require
explicit justification (the kinds-and-tools spec's `apiVersion: methodology.sulis/v1`
analog would be a new SKILL.md frontmatter field — costly, requires marketplace-wide change).

## Section B — Misuse cases applied to skill authoring

The kinds-and-tools `MISUSE_CASES.md` catalogues 13 misuse cases across 11
security-sensitive surfaces. The eight that apply to skill authoring:

1. **Trigger-condition jargon leakage** — the `description:` field uses
   vocabulary Claude doesn't have context for. Claude triggers the skill
   for the wrong reason. Mitigation: trigger condition uses only
   user-facing vocabulary; verify via test (hand Claude the description
   alone, see if it makes the right decision).

2. **Premature reference commitment** — the skill wraps a standard from
   `references/some-standard.md` but doesn't declare the version. The
   standard is later updated; the skill's behaviour silently changes.
   Mitigation: any wrapped reference declares its version + reconciliation
   strategy.

3. **Unbounded gotchas section** — gotchas grow past 15 items;
   Claude stops consulting the bottom half. Mitigation: ≤15 items in
   SKILL.md, ordered by likelihood × impact; overflow goes to
   `references/advanced-gotchas.md` with a progressive-disclosure pointer.

4. **Authorization leakage** — the skill requires an MCP server or CLI
   tool but doesn't declare it. Claude invokes; the tool isn't available;
   no clear error. Mitigation: SKILL.md frontmatter declares
   `requires: [...]`; the skill's first action fails-fast on missing
   prerequisites with a typed error.

5. **Vocabulary collision** — two active skills use the same term to mean
   different things. Claude context-switches between them and produces
   confused outputs. Mitigation: Gate 1 scans for collisions; flagged
   collisions either resolved or explicitly waived.

6. **Silent failure of progressive disclosure** — SKILL.md says "see
   references/api.md" but the reference file was deleted or never
   committed. Claude never sees it and ships a partial-context output.
   Mitigation: Gate 3 verifies every declared reference exists on disk.

7. **Trigger condition matches too broadly** — description says "use when
   reviewing"; Claude triggers it for design reviews, code reviews, peer
   reviews. Mitigation: Gate 4 perspective 1 measures trigger accuracy
   against intended-invocation set; threshold ≥85% precision.

8. **Depth-mode ambiguity** — skill declares Quick/Full/Audit modes but
   doesn't specify how Claude chooses between them. Mitigation: depth-mode
   selection strategy is declared in SKILL.md frontmatter (auto /
   user-explicit / context-derived).

## Section C — Vocabulary, completeness, and verification discipline

### Vocabulary discipline (kinds-and-tools GLOSSARY.md → SKILL.md vocabulary section)

The spec treats vocabulary drift as a regression. Every load-bearing term has
exactly one definition; artifacts are validated against the glossary.

The skill-authoring equivalent: every skill that introduces ≥2 domain terms
must include a `## Vocabulary` section listing the terms, their definitions,
and any collisions-with-other-skills it disambiguates. The methodology
tracks cross-skill vocabulary at the marketplace level (Gate 1's `inventory.py`
output flags potential collisions).

### Completeness verification (kinds-and-tools five-perspective spiral → three-perspective Gate 4)

The kinds-and-tools spec ran a five-perspective completeness spiral:
requirement traceability, integration completeness, NFR coverage, tree
completeness, acceptance criteria. The spiral ran two passes, fixed residual
drift inline, surfaced three category gaps (Scalability, Availability, Data),
and resolved them via an inheritance clause.

The skill-authoring equivalent is lighter: three perspectives in Gate 4
(trigger accuracy, gotchas coverage, functional completeness). The simpler
artifact (a skill, not a full spec) needs less coverage. If a skill grows in
complexity, add perspectives — the pattern is extensible.

### Why grounding-before-specifying produces consistent outcomes

The spec's most-load-bearing insight: agent-driven authoring succeeds when
you structure the *discovery* conversation, not the *specification*
conversation. The conversation surfaces five separate framing-shifts (turns
15, 17, 19, 21, 23–24). Each shift was cheap because prior turns had
produced structured artifacts (codebase index, primitive tree, requirements
with explicit sources) so reframing only touched specification, not discovery.

For skill authoring: Gate 1 produces a structured BRIEF_PACK. Even if Gate 2
reveals the scope was wrong and Gate 1 needs to rerun, the BRIEF_PACK is the
cost-bound — discovery doesn't restart from scratch.

## Section D — Meta-learnings on consistency

**The single load-bearing claim:** the kinds-and-tools spec achieved consistent
outcomes across 28 turns of agent-driven work not through heavy process but
through **discovery gates with structured outputs**. The user didn't say "go
write a spec"; they said "ground the spec against actual code, then lock the
vocabulary, then apply the cascade." Each gate had a structured artifact
(CODEBASE_INDEX, PRIMITIVE_TREE, GLOSSARY) that became the input to the next
gate. Reframing was cheap because the artifacts were the contract.

**Applied to skill authoring:** the five gates each produce a structured
artifact (BRIEF_PACK, scope lock entries in COMPLETENESS_REPORT.md, the skill
files themselves, perspective verdicts, named misuse cases). Reframing at any
gate is cheap because the artifacts upstream are the contract; the rework is
bounded to downstream artifacts only.

This is the mechanism by which "consistent outcomes from working with agents"
is produced. Not by writing better prompts. By structuring the conversation
into gates whose outputs are auditable artifacts.

## Section E — Recommended structure (the five-gate model)

See `methodology.md` for the per-gate detail. The structure here is the summary:

1. **Gate 1 — Find** (deterministic-first, hybrid). Inventory the marketplace;
   surface collisions; interpret findings with LLM judgement.
2. **Gate 2 — Scope Lock** (decide). Commit to six load-bearing items;
   prevent scope creep during drafting.
3. **Gate 3 — Generate** (LLM-driven). Write SKILL.md + references + scripts
   + templates against the Gate 2 lock.
4. **Gate 4 — Evaluate** (three perspectives). Trigger accuracy, gotchas
   coverage, functional completeness. PASS / FAIL / DEFERRED with reasons.
5. **Gate 5 — Adversarial Review** (publish gate). Name 3+ misuse cases;
   prevent or document each.

Output: skill files + COMPLETENESS_REPORT.md (audit trail).

## Source

`/Users/iain/Documents/repos/platform/.specifications/kinds-and-tools/`

Original research report retained at this skill's `references/` location
(this file) so the methodology's grounding remains auditable even if the
source spec moves or is superseded.
