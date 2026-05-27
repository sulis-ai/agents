---
founder_facing: false
---
# Spec — enrich the pre-spawn recon CONTEXT.md

**Change:** CH-01KSNF · extend
**Closes:** [#26](https://github.com/sulis-ai/agents/issues/26)

## What this should do

Extend `plugins/sulis/scripts/_change_context.py`'s CONTEXT.md writer so the
recon stub it produces under `~/.sulis/changes/{change_id}/CONTEXT.md`
includes three sections it currently omits:

1. **`## Intent`** — the founder's intent text from the change metadata
   (already in `.changes/{primitive}-{slug}.yaml`, just not piped through
   to CONTEXT.md).
2. **`## Linked issue`** — when the intent text contains `#NN`,
   shell out `gh issue view N --json title,body,labels,state` and inline
   the title, labels, and body. Best-effort: silently omit the section on
   any failure (no `gh` available, no remote, network error, issue not
   found). Multiple `#NN` references → list each.
3. **`## Code-area pointers`** — light grep-based scan over the intent for
   backtick-quoted tokens (`cmd_nuke`, `read_change_record`, etc.) and
   path-like tokens (`_change_state.py`). Surface up to 5 candidate files
   under the section header. Section omitted entirely if zero matches.

## How we'll know it's done

- New tests in `plugins/sulis/scripts/tests/unit/test_change_context.py`
  for: intent-section render, linked-issue render (mocked `gh`), code-area
  pointer render (mocked `git grep`), graceful degrade when `gh` /
  `git grep` fail.
- All existing 12 tests still pass (additions don't break the change-
  identity or git-state sections).
- Full unit suite green: `python3 -m pytest plugins/sulis/scripts/tests/unit/ -q`
- Lint: `python3 -m compileall -q plugins/sulis/scripts/` clean.

## What to avoid

- **Do NOT add a new MCP dependency** — reuse the `gh` shell-out via
  `_wpxlib._run`, the established pattern in `sulis-lessons capture`.
- **Do NOT refactor the existing `_PRIMITIVE_NEXT_STEP_HINTS` map** — out
  of scope. (A future change should pair that next-step hint with the
  new context; not this one.)
- **Do NOT make the new sections required.** Recon is best-effort
  (per the writer's existing contract); if `gh` or `git grep` fails, the
  sections are silently omitted, never block the recon write.
- **Do NOT change the CONTEXT.md template's render order** — existing
  callers (the spawned Sulis agent body) reference the section order.
  New sections go AFTER "Git state at spawn" and BEFORE "Suggested next
  step" so the next-step hint stays the last thing the spawned Sulis
  reads.

## Test-first sequence

1. RED — write tests for: intent section present + correct; linked-issue
   section rendered when `gh` returns a body; linked-issue omitted when
   `gh` fails; code-area pointers section listing matched files; pointers
   omitted when zero matches.
2. GREEN — implement `_resolve_linked_issue(intent, repo_root)` and
   `_locate_code_areas(intent, repo_root)` helpers; thread both into
   `_render_context_md` via the existing dict-passing pattern.
3. BLUE — extract a small `_extract_issue_refs(intent) -> list[int]`
   helper if the regex grows; otherwise leave inline.

## References

- The current writer: `plugins/sulis/scripts/_change_context.py` (179 lines,
  stdlib-only, `_run` from `_wpxlib`).
- Existing test pattern: `plugins/sulis/scripts/tests/unit/test_change_context.py`
  (12 tests; `monkeypatch.setenv("HOME", ...)` for isolation; `_run`
  mocked via `monkeypatch.setattr`).
- The `gh` shell-out pattern: `plugins/sulis/scripts/sulis-lessons`'s
  `_existing_lesson_titles` (the working reference).
