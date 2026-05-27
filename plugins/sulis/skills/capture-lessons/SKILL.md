---
name: capture-lessons
description: "Captures the lessons from a piece of work as durable GitHub issues + a digest."
---

# /sulis:capture-lessons — turn what you learned into durable, trackable issues

## Conclusion (lead with the answer)

After a piece of work ships, this skill **captures the lessons so they don't
evaporate**. A lesson the session noticed (a tooling gap, a process slip, a
"we should really fix X later") lives only in the session's memory until it's
written down — and the in-session to-do list disappears when the session ends.
This skill promotes the **actionable** lessons into **GitHub issues** (durable,
discoverable, closeable, and they auto-close when a future PR says `Closes #N`)
and records the **narrative** in a digest in the repo.

It is an **orchestrator**: the deterministic triage/dedup lives in
`../../scripts/_lessons.py` and the gh issue creation in
`../../scripts/sulis-issues`. The skill gathers the lessons, lets the founder
confirm, and writes the digest.

## What counts as a lesson + where it goes

Each lesson carries a **disposition** that decides its fate:

| Disposition | What it means | Becomes a GitHub issue? |
|---|---|---|
| `SEA` | Substantive — needs design/architecture work | **Yes** (`lesson` + `enhancement`) |
| `TASK` | Real follow-up, not trivial, not blocking | **Yes** (`lesson` + `enhancement`) |
| `FIX-NOW` | Trivial (CW-05) — fixed in this commit | No — the commit is the record |
| `FIXED` | Already fixed this session | No — the commit is the record |
| `note` | An observation worth remembering, no action | No — digest only |

Two stores, two lifetimes (this is the point): **GitHub issues** are the
durable backlog of actionable lessons; the **digest** is the narrative of the
session (patterns, process slips, the story). In-session `TaskCreate` todos are
*not* a lessons store — they vanish at session end, which is the gap this
closes.

## Resolving the tool path (MUST — first action)

```bash
SCRIPTS_DIR=$(
  find ~/.claude/plugins/cache -name sulis-issues -type f \
    -path '*/sulis/*/scripts/*' 2>/dev/null | sort -r | head -1 \
  | xargs -I{} dirname {} 2>/dev/null
)
if [ -z "$SCRIPTS_DIR" ] && [ -f "plugins/sulis/scripts/sulis-issues" ]; then
  SCRIPTS_DIR="$(pwd)/plugins/sulis/scripts"
fi
[ -z "$SCRIPTS_DIR" ] && { echo "ERROR: cannot find sulis-issues" >&2; exit 1; }
```

## When invoked

**1. Gather the lessons.** Assemble what the work surfaced into a structured
JSON array — one object per lesson, `{id, title, body, disposition}`:

```json
[
  {"id": "L-01", "title": "two tools disagree on the INDEX column name",
   "body": "wpx-index keyed on 'depends', parse_index_md on 'depends on' — a correct INDEX was silently rejected. Root cause: duplicate parsers.",
   "disposition": "SEA"},
  {"id": "L-02", "title": "sidecar files weren't gitignored",
   "body": "fixed inline this commit.", "disposition": "FIX-NOW"}
]
```

Write it to a temp file (e.g. `/tmp/lessons-<change>.json`). Keep titles short
and specific — the title is the issue title and the dedup key.

**2. Dry-run to see the partition** (creates nothing):

```bash
python3 "$SCRIPTS_DIR/sulis-issues" capture --descriptor lesson \
  --items-file /tmp/lessons-<change>.json --dry-run [--repo OWNER/REPO]
```

Returns `would_create` / `duplicates` / `skipped`. (`--repo` defaults to the
current remote; pass it explicitly when working outside the repo.)

**3. Confirm with the founder (AAF-06 three-list shape, echo-before-act).** Do
NOT silently create issues:

> *"This piece of work surfaced 5 lessons. I'd raise **2** as issues to track
> (X, Y), **1** is already an open issue (Z — skipping), and **2** were fixed
> in the commit (no issue needed). Raise the 2?"*

**4. Create the issues** (on confirmation):

```bash
python3 "$SCRIPTS_DIR/sulis-issues" capture --descriptor lesson \
  --items-file /tmp/lessons-<change>.json [--repo OWNER/REPO]
```

Returns `created` (title + issue URL), `duplicates`, `skipped`. If `degraded:
true` (no `gh` / not a GitHub remote), no issues were created — say so plainly
and fall through to the digest only.

**5. Write the narrative digest.** Append (or create) a dated digest under
`.architecture/{project}/lessons/` (or `plugins/sulis/docs/lessons/` for the
marketplace's own dev) — the story of the session: what happened, the
process slips, the patterns. Link each actionable lesson to its issue URL.
Because `.architecture/` now travels with the change (#42), the digest is
discoverable on the branch.

**6. Report (founder English).**

> *"Captured the lessons from **{work}**. Raised 2 issues to track (#51, #52),
> skipped 1 already-open, 2 were fixed in the commit. Wrote the story to the
> project's lessons digest."*

## Gotchas

- **Don't auto-create — confirm first.** Issue spam erodes the backlog's
  signal. Dry-run → batch-confirm → create. (AAF-06 / echo-before-act.)
- **Titles are the dedup key.** A lesson whose title matches an open `lesson`
  issue is skipped, not re-raised. Keep titles stable + specific.
- **FIX-NOW / FIXED never get an issue** — the commit is the durable record;
  raising an issue for something already fixed is noise.
- **Degrade is not failure.** No `gh` / non-GitHub remote → digest-only is a
  valid outcome; report it plainly, don't error.
- **This is not the finding-triage policy.** Finding-triage (in the Sulis
  agent body) handles findings *mid-work*; this captures lessons *post-ship*.
  They share the disposition vocabulary on purpose.

## When to invoke this skill

- After a piece of work ships, to capture what it taught us.
- The founder says "capture the lessons" / "what did we learn?" / "log that as
  something to fix later."

## When NOT to invoke this skill

- Mid-work findings that block the current task — that's finding-triage (fix
  now or surface), not post-ship capture.
- A trivial change with nothing learned — there's nothing to capture.

## See also

- `../../scripts/_lessons.py` — the pure triage/dedup core.
- `../../scripts/sulis-issues` — the gh-backed CLI this skill drives.
- `../../references/founder-facing-conventions.md` — AAF-06 batch shape,
  echo-before-act.
