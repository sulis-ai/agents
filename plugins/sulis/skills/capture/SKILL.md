---
name: capture
description: "Jots down an idea the moment you have it — why it matters and what it'd take — so nothing good gets lost."
user_invocable: true
standards:
  input: [AUDIENCE_ADAPTED_FRAMING_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD]
  output: [FOUNDER_ENGLISH_STANDARD, AUDIENCE_ADAPTED_FRAMING_STANDARD, TONE_STANDARD]
register:
  founder_mode: default
  technical_mode:
    shape: json_envelope
    triggers: [intent, --raw, /sulis:jargon]
verification_spiral:
  tier: standard
  template_base: STANDARD_TIER_DEFAULT
related_skills:
  - relationship: depends_on
    skill: ../../scripts/sulis-capture
    notes: the CLI this skill drives — roots the idea in the backlog (why-first); returns the ok/error envelope this skill renders in plain English
  - relationship: related_to
    skill: ../../agents/opportunity-analyst.md
    notes: the specialist this skill recommends for the deeper "think the why through properly" path (ADR-004 store hand-off)
  - relationship: related_to
    skill: ../backlog/SKILL.md
    notes: the companion door — capture puts ideas in, backlog reads them back out
  - relationship: optional_input
    skill: ../../references/founder-english.md
    notes: Audience=founder-facing; every line here passes the founder-English check (FE-01..FE-10)
  - relationship: optional_input
    skill: ../../references/audience-adapted-framing-standard.md
    notes: any question to the founder runs the three-step pre-question triage first (AAF-01)
---

# /sulis:capture — jot down an idea before it slips away

## Conclusion (lead with the answer)

`/sulis:capture` is the quick way to write down an idea the moment you
have it. It asks two plain questions — **why does this matter?** and
**what would it take?** — and files the idea in your backlog so you can
come back to it later. That's it. No forms, no jargon, no setup.

The one rule: **an idea needs a why.** A good idea you can't explain the
*point* of isn't ready to be written down yet — so this skill asks for
the why first, every time. If you skip it, nothing gets saved and you'll
get a friendly nudge rather than an error.

There are two depths:

| Depth | When | What happens |
|---|---|---|
| **Quick** (default) | A mid-conversation idea you want to park | You give a one-line why and a one-line what, right here, in one sitting |
| **Deeper** | You want to really think the "why" through | This skill points you to a specialist who'll talk it through with you first, then you come back and finish the capture |

This skill is a **friendly front door**. The actual filing is done by a
small tool under the hood (`sulis-capture`); this skill's job is to ask
the two questions in plain English and tell you how it went. It does not
re-implement the filing logic in these instructions.

This skill speaks plain English throughout. You'll never be asked to type
codes, identifiers, or technical labels — those are the tool's business,
not yours. (Founder-English check applies to every line: see
`../../references/founder-english.md`.)

## Step 0 — resolve the tool path (MUST — first action)

The Sulis tools live in the plugin cache when installed, or in the
marketplace repo in dev. Resolve the script directory once:

```bash
SCRIPTS_DIR=$(
  find ~/.claude/plugins/cache \
    -name sulis-capture -type f \
    -path '*/sulis/*/scripts/*' \
    2>/dev/null \
  | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
)
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/sulis-capture" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
if [ -z "$SCRIPTS_DIR" ]; then
  echo "ERROR: cannot find the sulis tools. Run: claude plugin install sulis@sulis-ai-agents" >&2
  exit 1
fi
echo "SCRIPTS_DIR=$SCRIPTS_DIR"
```

Capture the printed path and substitute the literal at each `$SCRIPTS_DIR`
below — environment variables do NOT persist between Bash tool calls in
Claude Code.

## Step 1 — ask the why (and mean it)

Ask, in plain English:

> *"What's the idea — and why does it matter? One line on each is plenty."*

The **why** is the part that's mandatory. It doesn't have to be polished —
"because support keeps asking for it" is a perfectly good why. But there
has to be one. If the founder gives you an idea with no why, don't file
it. Ask once more, gently:

> *"Got the idea. Before I write it down — what's the point of it? Even a
> half-sentence helps future-you remember why this was worth keeping."*

You don't enforce this rule yourself — the tool under the hood is the real
gate (it refuses to save a why-less idea and hands back a plain message you
relay). Your job is just to ask the question kindly and not push past a
blank answer. (Any follow-up question runs the pre-question triage first —
`../../references/audience-adapted-framing-standard.md`.)

## Step 2 — ask the what (same sitting)

In the **same** conversation — don't make them come back for it — ask what
it'd take:

> *"And what would 'done' look like, roughly? One line is fine — I can
> always flesh it out later."*

The what is optional: an idea can stand on its own as something to revisit,
with just the why. If the founder doesn't have a clear what yet, that's
fine — capture the idea on the strength of its why alone and say so.

## Step 3 — offer to set it aside for later

Some ideas are "do this soon"; others are "good, but not now." Offer the
parking option in plain language:

> *"Want me to set this aside for later, or is it something you're
> actively chewing on?"*

If they say later, mark it accordingly when you file it (the tool takes a
`--roadmap` flag — you set it, the founder never types it).

## Step 4 — the deeper path (only if they want it)

If the founder says something like *"I want to think this through
properly"* or *"this one's a big deal, I don't want to rush the why"* —
that's the deeper path. Don't try to facilitate it yourself in this quick
door. Recommend the specialist, exactly the way Sulis recommends the
requirements specialist for a deep requirements conversation:

> *"This one deserves a proper think. Run `claude --agent
> opportunity-analyst` — it'll talk the 'why' through with you, one
> question at a time, and shape it up. When you're done, come back here and
> I'll finish filing it."*

The specialist does its work, shapes up the idea, and hands back a
reference to it. You resume capture against that matured idea (the
hand-off happens through the shared backlog, not a direct call — that's
the decision recorded in **ADR-004**). When you resume, pass the reference
the specialist returned to the tool via its `--opportunity-id` option (you
relay it; the founder never types it).

## Step 5 — file it (drive the tool, don't re-implement it)

Invoke the `sulis-capture` CLI with the fields you gathered. The skill
generates a stable internal key for the idea so re-running is safe — the
founder never sees it or types it. Quick path:

```bash
"$SCRIPTS_DIR/sulis-capture" \
  --why-intensity quick \
  --why "<the one-line why the founder gave>" \
  --what "<the one-line what, or omit if they had none>" \
  --roadmap   # include only if they asked to set it aside
```

Deeper path (after the specialist has shaped the idea and handed back a
reference):

```bash
"$SCRIPTS_DIR/sulis-capture" \
  --why-intensity full \
  --opportunity-id "<the reference the specialist returned>" \
  --what "<the one-line what>"
```

Do **not** reproduce the filing logic in these instructions — the CLI owns
it (the why-first gate, the backlog wiring, the safe re-run). This skill is
the friendly door; `sulis-capture` is the lock.

## Step 6 — tell them how it went (plain English, always)

The tool answers with a small result. Translate it — never show raw output:

- **It worked** (`"ok": true`) → confirm in one warm line, naming the idea
  back to them:

  > *"Saved — '<the idea>' is in your backlog. I've noted why it matters and
  > what it'd take. You can pull it back up any time with /sulis:backlog."*

- **No why given** (`"ok": false` with the why-first message) → relay the
  nudge kindly, don't dress it as an error:

  > *"I didn't save that one yet — it needs a why first. What's the point of
  > it, in a few words? Then I'll file it."*

- **Couldn't save right now** (`"ok": false`, anything else — e.g. the
  backlog isn't reachable) → say so plainly, never a stack trace
  (NFR-01 — degrade gracefully):

  > *"I couldn't save that just now — the backlog isn't reachable at the
  > moment. Your idea isn't lost; tell me to try again and I will."*

Whatever the tool returns, the founder hears a sentence, not a code.

## When to invoke this skill

- The founder has an idea mid-conversation and wants it written down before
  it slips away.
- The founder says *"capture this"*, *"add this to the backlog"*, *"note
  this idea down"*, or similar.
- The founder wants to park something for later without losing it.

## When NOT to invoke this skill

- The founder wants to **read back** what's already in the backlog — that's
  `/sulis:backlog`.
- The founder wants a full, careful facilitation of the *why* on its own —
  that's the opportunity specialist (`claude --agent opportunity-analyst`),
  which this skill recommends but does not replace.
- There's no actual idea yet — there's nothing to capture. Don't file an
  empty thought.

## Gotchas

- **Never skip the why.** It's the one hard rule. A blank why means nothing
  gets saved — and that's by design. Ask again, gently; don't push past it.
- **Ask both questions in one sitting.** Don't capture the why now and make
  the founder come back for the what later — walk both in the same
  conversation (the what can still be left blank if they genuinely don't
  have one).
- **Plain English only.** The founder never types codes, identifiers, or
  technical labels — you gather plain answers and the tool does the rest.
  If you catch yourself about to ask the founder for anything that looks
  like a code, stop: that's the tool's job, not theirs (NFR-02).
- **A "couldn't save" is not a crash.** If the backlog is unreachable, the
  tool hands back a plain message — relay it as "couldn't save that right
  now", reassure the founder the idea isn't lost, and offer to retry. Never
  surface raw error text (NFR-01).
- **Don't re-implement the filing.** This skill asks the two questions and
  relays the result; `sulis-capture` does the actual work. Keep the logic in
  the tool, the warmth in the door.

## Vocabulary

- **Capture** — writing an idea down the moment you have it, with its why,
  so it lands in your backlog instead of getting lost.
- **The why** — the point of the idea: what problem it solves or what it
  unlocks. Mandatory; an idea without one isn't ready to be saved.
- **The what** — roughly what "done" would look like. Optional; an idea can
  stand on its why alone.
- **Set aside for later** — parking an idea on the roadmap so it's kept but
  not treated as active right now.
- **The deeper path** — handing the *why* to the opportunity specialist for
  a proper, one-question-at-a-time think before the idea is filed.

## See also

- `../../scripts/sulis-capture` — the CLI this skill drives (the why-first
  gate, backlog wiring, and the ok/error result this skill renders).
- `../../agents/opportunity-analyst.md` — the specialist the deeper path
  recommends (ADR-004 store hand-off).
- `../backlog/SKILL.md` — the companion door: read your captured ideas back
  out.
- `../../references/founder-english.md` — the voice every line here follows.
- `../../references/audience-adapted-framing-standard.md` — the pre-question
  triage any question to the founder runs first.
