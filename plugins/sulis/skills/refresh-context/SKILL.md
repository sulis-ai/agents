---
name: refresh
description: >
  Re-validate an existing `.context/{project}/INDEX.md`. Checks that
  every indexed source still exists, flags files modified since the
  last validation, surfaces newly-matched files that didn't exist at
  the last scan, and asks the user only about deltas. Sticky
  classifications — does not re-ask about already-classified sources
  unless they have changed.
user_invocable: true
---

# Context Refresh

When invoked, re-validate an existing context index against the current state
of the project. Update timestamps, classify new findings, and flag drift —
but do not re-run the full discovery conversation.

If arguments are provided, treat them as the project slug. Otherwise infer
from `.context/{project}/INDEX.md` (if exactly one project's index exists) or
ask the user.

If no `.context/{project}/INDEX.md` exists, stop and recommend
`/sulis-context:discover` instead.

---

## When to Run Refresh

- After significant edits to indexed sources (e.g. a new ADR was added)
- Periodically (the protocol recommends every 90 days for active projects)
- After a major refactor or rename
- When SRD/SEA report stale context
- When the index's `Last validated` date is more than 90 days old

---

## Workflow

### Step 1 — Locate the existing index

Read `.context/{project}/INDEX.md`. Parse the frontmatter and all sections.
Capture:
- `Last validated` date
- Classification of every entry across the four buckets
- The external ADR registry's count and highest number (if present)
- Known gaps list

### Step 2 — Re-scan

Run the same scan as `/sulis-context:discover` (per
`references/discovery-protocol.md`). Build a fresh candidate list.

### Step 3 — Diff against the index

Produce three lists:

**Drift — indexed files modified since `Last validated`:**
- For each entry in Authoritative or Informational, check the file's mtime
- If modified after `Last validated`, add to drift list

**Removals — indexed files that no longer exist:**
- For each entry, check the path still resolves
- If missing, add to removal list

**Additions — newly-matched files not in the index:**
- For each scan match, check whether the path appears in any classification table
- If not, add to additions list

If all three lists are empty, the refresh is a no-op. Update only the
`Last validated` date and `Validated by: /sulis-context:refresh`, write the
index, and exit with: *"No changes since {date}. Index timestamp updated."*

### Step 4 — Present deltas

For each non-empty list, surface to the user with the same one-question-per-
purpose pattern as discovery:

**Drift:**

> "These sources have been modified since `{Last validated}`:
>
> 1. `path/to/ADR-022.md` (modified {date}) — currently classified `authoritative`
> 2. `path/to/CONTRIBUTING.md` (modified {date}) — currently classified `authoritative`
>
> Re-confirm classification, or change?"

**Removals:**

> "These previously-indexed files no longer exist:
>
> 1. `path/to/old-ADR.md`
>
> Mark as superseded with the deletion note, or remove from index entirely?"

**Additions:**

> "These newly-matched files are not yet classified:
>
> 1. `architecture/decisions/ADR-023-new-decision.md` — looks like an ADR
>
> Classify each (authoritative / informational / superseded / out-of-scope)."

### Step 5 — External ADR registry recount

If the index has an External ADR Registry section, recount entries in that
directory and update:
- `Count`
- `Highest ADR number`
- `Most recent`
- `SEA new ADRs MUST start from: ADR-{N+1}`

If the highest number has changed, surface to the user:

> "External ADR registry has grown from {old} to {new} entries. New highest:
> ADR-{N}. SEA's next ADRs will start from ADR-{N+1}."

### Step 6 — Re-probe known gaps

Show the user the existing Known Gaps list. Ask:

> "Have any of the known gaps been filled, or are there new gaps to record?"

Add/remove gaps per the answer.

### Step 7 — Write the updated index

Re-generate `.context/{project}/INDEX.md` with:
- `Last validated: {today}`
- `Validated by: /sulis-context:refresh`
- All classification updates applied
- ADR registry updated
- Known gaps updated

Set `Discovery completeness` based on the updated state — promotion or
demotion is allowed if the project's documentation has materially changed
since the last discovery.

### Step 8 — Confirm and report

Show the diff between old and new index. Ask the user to confirm before
writing. After writing:

> "Index refreshed. {N} changes applied: {summary}. Downstream plugins will
> pick up the new state on their next invocation."

---

## Sticky Classifications Rule

The cardinal rule of refresh: **do not re-ask the user about sources whose
classification is still valid**. Specifically:

- A source that exists, hasn't been modified since `Last validated`, and
  is already classified → not re-asked.
- A source that has been modified → ask whether classification still holds.
- A new source → ask for first classification.
- A missing source → ask whether to mark superseded or remove.

This keeps refresh sessions short and the user's attention focused on
genuine deltas.

---

## Adapting Depth

- **Quick** ("just update timestamps") — Steps 1, 2, 3, 5, 7 only. Skip the
  user interaction unless additions or removals exist; for drift on
  authoritative sources, default to "classification holds" without asking.
  Use when you're confident the change set is mechanical (e.g. mass
  reformatting).
- **Full** (default) — all eight steps.
- **Manual overrides only** — if the user has hand-edited the INDEX.md and
  wants the refresh to respect those edits while still validating
  paths/dates, run with `--respect-manual` (skip Step 4's classification
  questions, only update timestamps and path existence).

---

## Gotchas

- **Refresh is not discovery.** Do not re-present the entire catalogue. The
  classification work has already been done; the user is approving deltas.
- **Manual edits to INDEX.md are sacred.** If the user has edited the index
  directly, do not silently overwrite their changes. Diff first, ask
  before overwriting.
- **Mtime can lie.** Some tooling rewrites files without semantic change
  (e.g. mass linting). If the diff against the previous content is trivial,
  ask: *"This file's mtime has changed but content looks identical — keep
  classification?"*
- **ADR renumbering is dangerous.** If the external ADR registry's
  numbering has been compacted (gaps removed) or renumbered, surface this
  loudly — SEA-generated ADRs that referenced specific numbers may now be
  pointing at the wrong decision.

---

## See Also

- `skills/discover/SKILL.md` — first-time discovery
- `skills/show/SKILL.md` — read-only view of the current index
- `references/discovery-protocol.md` — what to scan for and where
- `references/classification-taxonomy.md` — the four buckets explained
- `references/context-index-template.md` — the index file schema
