<!-- canonical:step:gather-ambiguous-fields -->
<!-- (annotated under gather-ambiguous-fields because diff approvals are the human gate
     during re-discovery; per the re-discovery decision, the diff is presented one field at a time) -->

# Re-discovery with `--update` — the per-field diff

When the founder runs the skill with `--update` and a Project entity
already exists on disk, the skill doesn't overwrite anything in bulk.
Re-running Detect and Infer produces a *proposed* entity; the skill
diffs it against the *existing* entity field by field and asks the
founder to keep or apply each change.

Fields whose value didn't change are silent — they're not surfaced
at all. The diff loop only shows fields where existing and proposed
disagree.

## Metadata fields are excluded from the diff

Some fields change every run by design and would create noise:

- `valid_from` — the timestamp the entity was last written
- any derived timestamp the schema computes at write-time

The diff loop hides these. The mint phase rewrites them when the
final entity is written; they're never a decision the founder has
to make.

## Prompt template

For each field where existing and proposed differ, render:

```
<friendly-name> has changed since last discovery.
  Existing:  <stored-value>
  Proposed:  <new-value>
Keep existing, or apply proposed?
[k] keep existing · [p] apply proposed
> _
```

Friendly names follow the dictionary in `confirm-or-override.md` —
the founder reads "where you publish releases" not the schema field.

## Binary choice — no third option

Keep existing or apply proposed. Editing the value inline during the
diff is not offered. If the founder wants something other than
either of the two values shown, they keep existing for now, finish
the diff loop, and re-run discovery without `--update` once they've
hand-edited the file. This keeps the diff loop short and the
decisions reversible.

## After the loop

The final entity is composed from:

- approved-proposed values (the founder chose `[p]`)
- kept-existing values (the founder chose `[k]`)
- existing values for any field that didn't change (silent — no
  prompt)

The composed entity is written atomically — same write-to-tmp-then-
rename as a first-time mint. The diff itself is a useful artifact:
"what changed about this project since the last discovery."

## Cancel semantics

Ctrl-C during the diff loop drops every keep/apply decision the
founder made so far and exits cleanly. The existing entity on disk
is untouched. No partial entity is written. Next re-discovery run
starts the diff loop fresh.
