---
founder_facing: false
---
# Spec — fix nuke silent-corrupt-record guard

**Change:** CH-01KSNR · fix
**Closes:** [#22](https://github.com/sulis-ai/agents/issues/22)

## What this should do

Close the silent fail-open in `cmd_nuke`'s shipped-protection guard.

### The bug

`plugins/sulis/scripts/_change_state.py:275-284` — `read_change_record`
returns `None` for **both**:
1. The change record file doesn't exist (legitimate "no record" — common
   immediately after `start` before anything writes `change.json`).
2. The file exists but is corrupt/unreadable (silent failure — emits a
   warning, returns None, callers can't distinguish).

`plugins/sulis/scripts/sulis-change:879-888` — `cmd_nuke`'s #38
shipped-protection guard reads:

```python
record = read_change_record(change_id)
if record and str(record.get("stage", "")).strip().lower() == "shipped" and not args.force:
    emit_error(...)  # refuse to nuke a shipped change
```

The `record and ...` short-circuit evaluates to False for both cases. So
a corrupt `change.json` causes the guard to silently pass — the nuke
proceeds and destroys the worktree + branch + manifest, which IS the
audit trail the #38 guard exists to preserve.

### The fix

Distinguish the two cases at the helper module, then refuse loudly at
the call site.

1. **Add `change_record_is_unreadable(change_id) -> bool`** to
   `_change_state.py`. Returns True iff the record file exists on disk
   AND `read_change_record` returns None (parse/OS failure). Returns
   False both when the file is absent (benign) and when it reads cleanly.
   Pure predicate; no side effects beyond the warning `read_change_record`
   already emits on the underlying read.

2. **Wire it into `cmd_nuke` as Safety 1.4** — runs BEFORE the existing
   Safety 1.5 (shipped check). If the record is unreadable and `--force`
   is not set, `emit_error` with a distinct message: *"Refusing to nuke
   {branch}: the change record exists but can't be read (corrupt or
   unreadable). I can't verify this isn't a shipped change, so I won't
   risk destroying its audit trail. Run with --force if you really mean
   to remove it."*

3. `--force` still overrides — same semantics as the shipped guard. The
   guard is a refusal-by-default, not a hard block.

### Why this ordering

- **Safety 1.4 (this fix) before Safety 1.5 (#38 shipped)** — the new
  guard is the strictly broader check. If the record is unreadable, we
  can't evaluate the shipped check at all, so refusing on unreadability
  is the conservative choice. The shipped check then runs only when the
  record IS readable.
- **No other callers need the distinction.** `mark_change_shipped`,
  `list_all_changes`, and `sulis_list_changes.py`'s `--change-id` lookup
  are all best-effort / informational; they correctly degrade on a
  corrupt record. Only the safety check at the nuke call site needs to
  refuse loudly.

## How we'll know it's done

- New pure-predicate tests in `test_change_store.py` cover
  `change_record_is_unreadable` (absent → False; corrupt → True; OK → False).
- New integration tests in `test_sulis_change_nuke.py` cover the call site:
  - corrupt `change.json` + nuke without `--force` → refused with a
    "record" / "unreadable" message; worktree + branch + manifest all
    preserved.
  - corrupt `change.json` + nuke with `--force` → completes (the guard
    is a refusal-by-default, not a hard block).
- Existing #38 shipped-protection tests still pass (no regression on the
  pre-existing Safety 1.5).
- Full `pytest plugins/sulis/scripts/tests/unit/` green.
- Step 4.5 review gate (#30) PASS.

## What to avoid

- **Do NOT change `read_change_record`'s signature.** It returns
  `dict | None` and that's used by 5 other call sites. The fix adds a
  sibling predicate; it doesn't reshape the existing function.
- **Do NOT remove the existing warning emission inside
  `read_change_record`.** The warning is still useful diagnostic output;
  the new predicate is for safety-check call sites that need to act on
  the unreadability, not replace the warning.
- **Do NOT swallow `--force`.** The guard remains a refusal-by-default;
  `--force` is the documented escape hatch (and is also what the
  existing #38 guard uses).

## References

- `plugins/sulis/scripts/_change_state.py` — `read_change_record` (lines
  275-284); the new `change_record_is_unreadable` sits next to it.
- `plugins/sulis/scripts/sulis-change` — `cmd_nuke` (lines 854+); the
  new Safety 1.4 block goes between Safety 1 (line 868) and Safety 1.5
  (line 875).
- `plugins/sulis/scripts/tests/unit/test_change_store.py` — pure-predicate
  tests live here next to the existing `read_change_record` tests
  (lines 180-191).
- `plugins/sulis/scripts/tests/unit/test_sulis_change_nuke.py` —
  integration tests live here next to the existing `#38 shipped-archive`
  tests (lines 467-528).
- The 2026-05-27 lesson (issue #22) is the source.
