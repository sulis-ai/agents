---
name: backlog
description: "Shows what you're thinking about, what you've committed to, and what's already built — your living backlog."
user_invocable: true
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [AUDIENCE_ADAPTED_FRAMING_STANDARD]
  output: [AUDIENCE_ADAPTED_FRAMING_STANDARD]
register:
  founder_mode: default
  technical_mode:
    shape: json_envelope
    triggers: [intent, --raw, /sulis:jargon]
verification_spiral:
  tier: standard
  template_base: STANDARD_TIER_DEFAULT
related_skills:
  - relationship: distinct_from
    skill: ../dashboard/SKILL.md
    notes: >-
      dashboard reads the CHANGE-STORE (pieces of work in flight, by stage);
      backlog reads the BRAIN GRAPH (ideas, roadmap, what's built). Different
      source, different question. Do not conflate them.
  - relationship: distinct_from
    skill: ../inbox/SKILL.md
    notes: >-
      inbox reads the CHANGE-STORE (what's waiting on you, by item); backlog
      reads the BRAIN GRAPH. Different source, different question.
  - relationship: reads_seam
    skill: ../../scripts/sulis-brain-query
    notes: The brain read seam (WP-008). backlog invokes its --open / --roadmap / --done modes.
  - relationship: optional_input
    skill: ../../references/founder-english.md
    notes: Audience=founder-facing; FE-01..FE-10 apply (no ids, no schema vocabulary).
  - relationship: optional_input
    skill: ../../references/audience-adapted-framing-standard.md
    notes: AAF — plain English, names not ids, never surface raw state vocabulary.
---

# /sulis:backlog — what you're thinking about, committed to, and have built

## Conclusion (lead with the answer)

`/sulis:backlog` is the one view that shows, in plain English:

- **Open ideas** — the things you're thinking about but haven't committed to.
- **On your roadmap** — the things you've decided to build.
- **Done** — the things that are already built.

It answers *"where is everything I want to build?"* — sourced from your
project's **brain** (its long-lived memory of ideas, decisions, and what
shipped). It is **read-only**: it surveys; it never adds, changes, or removes
anything.

### This is NOT `/sulis:dashboard` or `/sulis:inbox`

This distinction is load-bearing — keep the two surfaces apart:

- **`/sulis:backlog` (this skill)** reads the **brain graph**: your ideas,
  your roadmap, what's built. It answers *"what do I want to build, and how
  far along is the thinking?"*
- **`/sulis:dashboard` and `/sulis:inbox`** read the **change-store**: the
  pieces of *work-in-progress* and what's waiting on you right now. They
  answer *"what am I actively working on, and what needs me?"*

They read **different sources** and answer **different questions**. A future
maintainer must not wire `/sulis:backlog` to the change-store, nor route a
"what's on my roadmap?" question to the dashboard. The brain is the backlog's
only source.

## Resolving the tool path (MUST — first action)

The brain query tool lives inside the sulis plugin. Resolve the directory
ONCE and capture it as `$SCRIPTS_DIR` (same resolver the other skills use):

```bash
# Resolve from the ACTIVE plugin version (its bin/ is on PATH) — avoids the
# lexical-sort cache pick that mis-ranks 0.98.0 above 0.126.0 (#49).
SCRIPTS_DIR=""
_sulis_bin=$(printf '%s\n' "$PATH" | tr ':' '\n' | grep -E 'sulis-ai-agents/sulis/[^/]+/bin$' | head -1)
if [ -n "$_sulis_bin" ] && [ -d "$(dirname "$_sulis_bin")/scripts" ]; then
  SCRIPTS_DIR="$(dirname "$_sulis_bin")/scripts"
fi
# Dev fallback: marketplace repo cwd.
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/sulis-brain-query" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
# Last-resort fallback ONLY if PATH anchor + dev both miss: a PORTABLE
# version-aware cache pick (numeric, NOT lexical, NOT `sort -V`).
if [ -z "$SCRIPTS_DIR" ]; then
  SCRIPTS_DIR=$(find ~/.claude/plugins/cache -name sulis-brain-query -type f -path '*/sulis/*/scripts/*' 2>/dev/null \
    | sed -E 's#(.*/sulis/)([^/]+)(/scripts/.*)#\2 &#' \
    | sort -t. -k1,1n -k2,2n -k3,3n \
    | tail -1 | cut -d' ' -f2- | xargs -I{} dirname {} 2>/dev/null)
fi
if [ -z "$SCRIPTS_DIR" ]; then
  echo "ERROR: cannot find the brain tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
  exit 1
fi
echo "SCRIPTS_DIR=$SCRIPTS_DIR"
```

## When invoked

**1. Ask the brain the three questions.** Each view is one call to
`sulis-brain-query` (the brain read seam). The seam owns the open/roadmap/done
mapping — this skill never re-derives "open means draft + hypothesis" in
prose; it just asks for the view by name and renders what comes back.

```bash
"$SCRIPTS_DIR/sulis-brain-query" --open      # things being thought about
"$SCRIPTS_DIR/sulis-brain-query" --roadmap   # things committed to
"$SCRIPTS_DIR/sulis-brain-query" --done       # things already built
```

Each returns the same envelope:
`{"ok": true, "data": {"count": N, "entities": [...]}}`. The `entities` are
brain records; each carries a human `name` / `title`.

**For a narrower ask** (e.g. *"just show me the open opportunities"*, or
*"what requirements are approved?"*), drop to the composable modes the seam
provides — `--by-type <opportunity|requirement>` optionally with
`--by-state <state>` — and render the result through the same formatter
(step 2). Use these only when the founder asks something narrower than the
three named views; the default `/sulis:backlog` answers with all three.

**2. Render each result through one plain-English formatter.** All three
views (and any narrower `--by-type` ask) render the *same way* — there is one
rendering rule, applied three times, not three separate prose recipes:

> **The formatter:** take the `entities` list for a group; for each entity,
> show its human **name** / **title** on its own line. Show **nothing else** —
> no id, no state word, no schema field. If the list is empty, render the
> group's empty line (step 4). The group heading is the plain-English label
> ("Open ideas" / "On your roadmap" / "Done"), never the entity type or the
> raw state.

Because the rule is shared, the three groups stay consistent and there is one
place to change how a backlog line looks.

**3. No jargon reaches the founder (NFR-02 — see
`../../references/founder-english.md` and
`../../references/audience-adapted-framing-standard.md`).** The brain records
carry machine fields the founder must never see:

- **Never show the id.** Records are keyed by an internal id; the founder sees
  the **name** / **title**, never the id.
- **Never show the raw state.** The seam already folded states into the three
  plain-English groups ("open" / "roadmap" / "done"); do not print the
  underlying state word back out.
- **Never show schema vocabulary** — internal field names, link labels, or
  type words. Translate at the seam; present names and titles only.

This skill cites the founder-English / AAF standards rather than restating
them, and cites the brain seam (WP-007/WP-008) for the open/done mapping
rather than re-deriving it here.

**4. An empty backlog is a valid state, not an error (NFR-01).** A brand-new
project — or one whose ideas haven't been captured yet — has an empty brain.
Each group renders its own gentle empty line; never surface a scary
"nothing found" or an error:

- Open ideas, all empty → *"Nothing open yet — capture an idea with
  `/sulis:capture` to get started."*
- Roadmap empty → *"Nothing on your roadmap yet."*
- Done empty → *"Nothing built yet."*

If **all three** are empty, lead with the one line: *"Nothing open yet."* and
point at `/sulis:capture`.

**5. Render the backlog:**

```
🧠  Your backlog

  Open ideas
    • {name}
    • {name}

  On your roadmap
    • {name}

  Done
    • {name}

{If a group is empty, show its gentle empty line instead of the bullets.}

What you can do:
  • Capture a new idea      → /sulis:capture
  • See work in flight      → /sulis:dashboard
```

**6. Technical mode (`--raw` / "show me the raw version").** Pass the
underlying envelopes straight through — the three
`{"ok":…,"data":{"count":N,"entities":[…]}}` objects from the seam, keyed by
view (`open` / `roadmap` / `done`). Same substance, machine shape; the id and
state fields are fine here because the audience is an operator, not the
founder.

## Gotchas

- **Brain, not change-store.** The single most important rule: backlog reads
  the **brain graph** via `sulis-brain-query`. The change-store (the
  `.changes/` manifest and the local change index) is **off-limits** here —
  that source belongs to `/sulis:dashboard` / `/sulis:inbox`. Wiring this
  skill to the change-store answers the wrong question entirely.

- **The seam owns the open/done mapping — don't re-derive it.** "Open means
  draft + hypothesis; done means implemented + verified" lives **once**, in
  the query seam (WP-007/WP-008, ADR-006). This skill asks for `--open` /
  `--done` and renders the answer. If the mapping ever changes, it changes in
  the seam, and this skill needs no edit.

- **Never leak ids or states to the founder (NFR-02).** The records carry an
  internal id and a raw state word. Both are operator vocabulary. The founder
  sees names/titles and the three plain-English groups. Printing an id or a
  state word is the jargon-leak failure this skill exists to prevent.

- **Empty is normal (NFR-01).** A new project's brain is empty. Render the
  gentle per-group empty line and point at `/sulis:capture`; never an error.

- **Compute on read; never cache.** Re-ask the brain on every invocation. A
  cached backlog shows yesterday's thinking.

## Vocabulary

- **backlog** — this skill; the brain-sourced view of open ideas, the
  roadmap, and what's built.
- **brain graph** — the project's long-lived memory of ideas, decisions, and
  shipped work. The source this skill reads (via `sulis-brain-query`).
  Distinct from the change-store that `/sulis:dashboard` / `/sulis:inbox`
  read.
- **open / roadmap / done** — the three plain-English groups. The seam maps
  the underlying states into these; this skill never shows the raw states.

## When to invoke this skill

- Founder asks "what's on my roadmap?", "what ideas do I have?", "what have we
  built?", "where is everything I want to build?"
- Founder wants the lay of the land across their *thinking*, not their
  in-flight *work*.

## When NOT to invoke this skill

- Founder asks "what am I actively working on?" / "what's in flight?" — that's
  `/sulis:dashboard` (the change-store, by-change view).
- Founder asks "what's waiting on me?" — that's `/sulis:inbox` (the
  change-store, by-item view).
- Founder wants to capture a new idea — that's `/sulis:capture`.

## See also

- `../../scripts/sulis-brain-query` — the brain read seam (`--open` /
  `--roadmap` / `--done`, plus `--by-type` / `--by-state`).
- `../dashboard/SKILL.md` — the change-store by-change view (distinct source).
- `../inbox/SKILL.md` — the change-store by-item view (distinct source).
- `../../references/founder-english.md` — FE-01..FE-10 (no ids, no jargon).
- `../../references/audience-adapted-framing-standard.md` — AAF (names not
  ids; never surface raw state vocabulary).
