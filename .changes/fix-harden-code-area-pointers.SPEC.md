---
founder_facing: false
---
# Spec — harden code-area pointers

**Change:** CH-01KSNR · fix
**Closes:** [#31](https://github.com/sulis-ai/agents/issues/31)

## What this should do

Fix `_locate_code_areas` in `plugins/sulis/scripts/_change_context.py`
so the pointers it surfaces are biased toward **subjects** (the file or
code a token refers to) rather than **mentioners** (docs / changelogs
that happen to contain the token string).

Two complementary heuristics:

### Heuristic 1 — path-token recognition (high signal)

When a backticked token looks like a path:
- contains `/` or `\`, OR
- ends in a known code/doc/config extension
  (`.py .md .ts .tsx .js .jsx .json .yaml .yml .sh .html .css .toml .rst`)

…check if `Path(repo_root) / token` is a real file. If yes, add the
token's relative path to the pointers list **first** as a direct
reference; **skip** the grep for that token (the path resolution is a
stronger signal than any grep match).

### Heuristic 2 — doc-file exclusion on symbol grep

For tokens that aren't path-like (i.e. symbols like `cmd_finish` or
`mark_change_shipped`), keep the existing `git grep -l -F -- <token>`
behaviour, but **filter out** matches whose paths end in
`.md / .txt / .rst`. Docs that mention a symbol are mentioners, not
subjects; including them in the pointers section is noise.

### Combined behaviour

Pointers section is now: `direct_paths + symbol_grep_results`, capped
at 5 unique entries total. Direct paths come first because they're
strictly higher signal (the founder is most often referencing the file
they intend to edit).

## How we'll know it's done

- New helpers `_looks_like_path(token)` and `_is_doc_file(path)` exist
  as pure functions; both have direct unit tests.
- `_locate_code_areas` returns direct path matches before grep matches;
  tested via existing-file fixtures.
- `.md` / `.txt` / `.rst` files no longer surface as symbol-grep
  results; tested by mocking the grep output.
- The original 25 `test_change_context.py` tests still pass (no
  regression on identity / git-state / intent / linked-issue / order).
- Full unit + integration suite green; lint clean.
- Shipped through the step 4.5 review gate (#30).

## What to avoid

- **Do NOT change the `_extract_code_tokens` regex** (the backtick
  extractor) — out of scope. The bug is downstream, in how the tokens
  are *resolved* to files.
- **Do NOT exclude `.md` from path-token matches** — when the intent
  backticks `SOMETHING.md` and that file exists, it IS the subject
  (the founder intends to edit a doc). Only doc-extension matches on
  the **symbol-grep** path are filtered.
- **Do NOT widen the path-recognition to bare filenames without
  extensions** (e.g. just `cmd_finish`) — too many false matches; the
  symbol grep handles these correctly with the new doc filter.

## Path-recognition extension list

The recognised extensions: `.py .md .ts .tsx .js .jsx .json .yaml .yml
.sh .html .css .toml .rst`. Covers the common file types in this
marketplace and downstream Sulis-built apps. Bare extensions are
caught even without `/` (e.g. `_change_context.py` triggers path
recognition).

## References

- `plugins/sulis/scripts/_change_context.py` — `_locate_code_areas`
  (added in v0.61.0 / #26); `_extract_code_tokens` regex.
- `plugins/sulis/scripts/tests/unit/test_change_context.py` — the
  existing 25 tests (12 original + 13 #26 additions).
- The 3 changes that hit #31's noise pattern: PR #30 (no `change/SKILL.md`
  in pointers), PR #33 (got the right file but buried), PR #35 (no
  `sulis-lessons` or `change/SKILL.md` in pointers).
