---
founder_facing: false
---
# Spec — fix GitHub-interaction edge cases

**Change:** CH-01KSNQ · fix
**Closes:** [#23](https://github.com/sulis-ai/agents/issues/23), [#34](https://github.com/sulis-ai/agents/issues/34)

## What this should do

Two GitHub-interaction polish fixes, bundled because they touch the
same surface (how Sulis talks to GitHub) and both have bitten the
2026-05-27 session repeatedly:

### Fix 1 — `sulis-lessons` dedup query (closes #23)

`plugins/sulis/scripts/sulis-lessons` line 50 currently lists existing
`lesson`-labelled issues via:
```python
cmd = ["gh", "issue", "list", "--label", "lesson", "--state", "open",
       "--limit", "200", "--json", "title"]
```
This uses GitHub's REST API filter which is **eventually consistent** —
an issue created seconds earlier may not appear in the result. Bit the
session at least four times: dedup misfired the first time #20 was
created, and the bulk `gh issue list` repeatedly contradicted focused
`gh issue view` calls on freshly-merged PRs.

Swap to:
```python
cmd = ["gh", "issue", "list", "--search", "label:lesson is:open",
       "--limit", "200", "--json", "title"]
```
`--search` uses GitHub's GraphQL search backend — the same one `gh issue
view` uses — which is immediate. The search string `label:lesson
is:open` covers both filters in one expression. The `--state open` flag
is dropped (subsumed by `is:open`).

### Fix 2 — `/sulis:change ship` PR-body close trailer (closes #34)

`plugins/sulis/skills/change/SKILL.md` ship subcommand step 3 shows a
PR-body example but does NOT specify how multi-issue close trailers
must be formatted. GitHub's auto-close-on-merge requires the closing
keyword (`closes` / `fixes` / `resolves`) **once per issue reference**;
chaining with "and" (`Closes #27 and #28`) only auto-closes the first.

Bit the session on PR #33 — both #27 and #28 were addressed but only
#27 auto-closed; #28 had to be manually closed.

Amend the ship subcommand step 3 to add an explicit MUST rule: when
composing the PR body and the change addresses multiple issues
(detected by scanning the change's intent for `#NN` tokens), emit one
`Closes #N` line per issue, OR a single `Closes #N, closes #M`
comma-separated form. Forbidden: `Closes #N and #M` (only the first
auto-closes).

## How we'll know it's done

- `sulis-lessons` capture's dedup query uses `--search 'label:lesson
  is:open'` not `--label lesson --state open`. Verified by a new
  integration test that asserts the gh stub receives `--search`
  argv.
- All 4 existing `test_sulis_lessons.py` tests still pass (the swap
  is a strict equivalent + immediate).
- `change/SKILL.md` ship subcommand step 3 has the new PR-body close
  trailer rule with both the correct forms and the forbidden form
  explicitly shown.
- Full suite green + lint clean.
- Shipped through the new step 4.5 review gate (#30).

## What to avoid

- **Do NOT change the partition logic** in `_lessons.py` — the dedup
  pure core is sound; only the input it consumes is affected. Fix is
  in the gh-glue (`sulis-lessons` CLI), not the pure module.
- **Do NOT add `addresses_issues: [N, M]` field to the change manifest**
  — would be cleaner but widens scope (touches `_wpxlib.py`,
  `sulis-change start`, etc.). Path A (parse `#NN` from the intent at
  PR-body-composition time) is smaller and sufficient.
- **Do NOT make the per-issue close trailer auto-emitted by code** —
  this is a SKILL prose change. The agent composing the PR body reads
  the rule and writes the correct form.

## References

- `plugins/sulis/scripts/sulis-lessons` line 50 (the dedup query).
- `plugins/sulis/scripts/tests/integration/test_sulis_lessons.py` (4 tests; mock_gh fixture for argv stubbing).
- `plugins/sulis/skills/change/SKILL.md` ship subcommand step 3 (lines ~278-290; the PR body example).
- GitHub docs on auto-closing keywords:
  <https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue>
