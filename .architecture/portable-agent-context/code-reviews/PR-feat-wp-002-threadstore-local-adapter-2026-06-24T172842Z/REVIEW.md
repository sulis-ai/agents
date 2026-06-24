# Code Review: WP-002 — ThreadStore local adapter (durable, append-only, redaction-on-write)

> **Timestamp:** 2026-06-24T172842Z (ISO 8601 UTC)
> **Branch:** wp/create-portable-agent-context/wp-002-threadstore-local-adapter → change/create-portable-agent-context
> **Files changed:** 5
>
> **Outcome:** Ready to merge (all findings addressed inline)

---

## At a glance

This change adds the durable, on-disk store behind the thread/message/memory
contract — the place agent conversation history is saved so a thread can be
resumed from our own records. The build is clean (no errors), every behaviour
is tested, and coverage on the new code is complete.

The review found three things worth fixing in how secrets are kept out of
the saved files — all three were fixed and re-checked, and a fourth small
hardening was applied for good measure. Nothing is left outstanding.

## What to fix

No issues remain. All findings below were fixed in this same change and
re-reviewed clean.

The fixes that were made (so the record is complete):

1. **A pasted secret in a conversation's title or summary used to be saved
   in plain text.** The store now cleans those two fields the same way it
   cleans message text, so a token can't slip onto disk through them.

2. **A secret stored in the open-ended "context" bag attached to a memory
   snapshot used to be saved in plain text.** The store now cleans every
   string inside that bag (however deeply nested), including the labels.

3. **The secret-finder reports an approximate position for some kinds of
   secret, which could have left a copy behind if the same secret appeared
   twice.** The store now does a second clean-up pass that removes the secret
   by its exact text, so no copy survives regardless of reported position.

## How this pull request is shaped

Well-scoped and complete. One new file (the adapter), a small tightening of
the shared validation helper to close a known edge case, and three test
files. It includes its own tests, including real on-disk tests proving
secrets never reach the saved files. No database migrations, no
infrastructure changes, no secrets in the diff itself.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, lens IDs) for
> engineers and downstream agents.

### Verdict

`PASS` per CR-06 — after the inline-fix loop. No critical/high/medium remain
in the diff; Build Verification empty; all changed files >50 lines read
end-to-end by all three lenses; all three lenses produced structured output.

### Summary

- **Build Verification (CR-01):** 0 PR-introduced errors. ruff clean,
  py_compile OK, mypy 0 errors in changed source files (`thread_store_local.py`,
  `thread_contract.py`). Pre-existing `manager.py` mypy errors are byte-identical
  to base, out-of-scope, and not run by the CI gate.
- **PR Hygiene (CR-09):** Scope low (single `feat:` concern). Size low (675
  lines / 5 files). Safety low (0 migrations, 0 schema files, 0 secret-pattern
  hits in the diff, 0 infra files). Completeness clean (3 of 5 changed files
  are tests; the new source file has dedicated unit + integration tests).
- **In the changes:** 3 findings at first pass (2 high, 1 medium) — ALL
  ADDRESSED inline; 2 follow-on findings on re-review (1 low, 1 informational)
  — ALSO ADDRESSED inline. 0 remaining.
- **Draft fixes:** 0 (all findings fixed inline rather than deferred).

| Lens | In changes | Top concern | Resolution |
|---|---|---|---|
| Architecture | 0 blocking | Single IO seam + dependency-inward confirmed; per-op observability is a follow-on (ADR-002 scope) | clean |
| Security | 3 → 0 | 2 redaction-bypass (Thread free-text + participant_context); 1 advisory-offset seam-misuse | all fixed inline |
| Quality | 0 blocking | O(N²) append-by-design (benign in single-founder bounded-thread context); corrupt-record edge (low, deferred) | clean |

### Build Verification (CR-01)

None. See `tool-outputs/ruff-head.log` and `tool-outputs/mypy-head.log`.
Mechanical baseline clean on HEAD.

### Findings in the Changes (all ADDRESSED)

#### F-1 — `Thread.topic` / `activity_summary` persisted un-scrubbed — high (security, DAT-03) — ADDRESSED

**Was:** `put_thread` wrote `dataclasses.asdict(thread)` with no scrub; the
free-text `topic`/`activity_summary` reached `{thread_id}.thread.json` verbatim,
contradicting the module's "every string is scrubbed" claim.

**Fix:** Added `_scrub_thread()` (scrubs both fields with `None` guards), wired
into `put_thread` before write. Test: `test_redaction_scrubs_thread_topic_and_summary`
(integration) asserts the secret is absent from raw bytes and non-secret text
preserved.

#### F-2 — `participant_context` + journal `metadata` persisted un-scrubbed — high (security, DAT-03) — ADDRESSED

**Was:** `_scrub_memory` scrubbed `messages` + `exploration_journal.content`
but passed `participant_context` (which the contract notes carries "provider
identity") and entry `metadata` through unmodified.

**Fix:** Added recursive `_scrub_value()` (walks dict/list, scrubs str leaves
AND keys, preserves non-string scalars), applied to `participant_context` and
each journal entry's `metadata`. Tests: `test_redaction_scrubs_participant_context_values`
+ `test_redaction_scrubs_journal_metadata` (integration, on-disk byte assertions);
`test_scrub_value_recurses_dicts_and_lists`, `test_scrub_value_scrubs_dict_keys`,
`test_scrub_value_passes_through_scalars` (unit).

#### F-3 — `_scrub` trusted advisory detect-secrets offsets — medium (security, DAT-03) — ADDRESSED

**Was:** `_scrub` was span-driven; the detect-secrets layer of `find_secrets`
reports best-effort ("advisory") offsets via `str.find` on the first
occurrence. A duplicated detect-secrets-only secret (e.g. an AWS key appearing
twice) would have only the first occurrence redacted by the span pass.

**Fix:** Added a second exact-value sweep pass — for each `SecretHit.value`
still present (longest-first), `str.replace` removes every occurrence. Tests:
`test_scrub_redacts_detect_secrets_only_secret`,
`test_scrub_redacts_all_occurrences_when_offset_is_advisory` (unit).

### Findings in the Neighbours

None surfaced. The only modified neighbour is `thread_contract.py`'s
`validate_store_id` (in-scope per the WP's WP-001 security advisory fold-in);
the tightening from `^...$`/`.match` to `re.fullmatch` is verified correct and
covered by `test_store_id_validation_rejects_trailing_newline`.

### Watch List (non-blocking, accepted-in-context)

- **O(N²) append** — `append_message` re-reads the full `.jsonl` log per append
  to enforce the append-only invariant. Benign in a single-founder store with
  bounded thread sizes; re-read is the source of truth (no cache-coherency
  surface). Mitigation if threads ever grow unbounded: cache `last_order` + a
  seen-id set per thread.
- **Corrupt-record resilience** — `_read_json`/`_read_messages` catch only
  `FileNotFoundError`; a malformed/torn on-disk record would surface a raw
  `JSONDecodeError` outside the contract's three categories. Low: files are
  adapter-written under atomic temp-then-rename; the only non-atomic write is
  the message-log append (a crash mid-append could leave a torn final line).
- **Per-op structured observability** — TDD §4 mentions a structured log line
  per op; lands more naturally with the session pump (writer) + discovery seam
  (reader) WPs. Follow-on, not a defect for this WP (ADR-002 single-founder
  loopback scope).
- **File permissions at default umask** — ADR-002 designates OS file perms as
  the trust boundary for a single-founder loopback store (same posture as the
  brief/Working Set). Explicit `0o600`/`0o700` is the hardening if `~/.sulis`
  ever sits on a shared host or the hosted binding lands.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff (configured linter) + py_compile + mypy on HEAD. 0 PR-introduced errors in changed source. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch used.** Three lenses dispatched concurrently as sub-agents. Diff 675 lines / 5 files — above the 200-line / 5-file carve-out, so parallel dispatch required.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end by each lens. Re-review passes re-read the modified adapter + tests end-to-end.
- [✓] **CR-04 Evidence discipline.** All findings cite file + quoted text + fix location.
- [✓] **CR-05 Severity rubric.** Applied: 2 high + 1 medium (first pass), 1 low + 1 informational (re-review). All addressed.
- [✓] **CR-06 Verdict computed.** PASS after inline-fix loop (2 review iterations + 1 confirmation). No auto-downgrade triggers fired post-fix.
- [✓] **CR-07 Lens completion.** Architecture: 0 blocking + checks enumerated. Security: 3→0 + final enumeration of every persisted string surface. Quality: build-verification confirm + dead-surface + contract-drift + test-coverage + CR-10 performance + correctness edges.
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size low, Safety low (0 migrations/schemas/secrets/infra), Completeness clean. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-portable-agent-context -- plugins/sulis/scripts`
- **Lenses dispatched in parallel:** yes (architecture + security + quality)
- **Inline-fix loop:** iteration 1 (3 findings fixed) → re-review (2 follow-on findings fixed) → confirmation re-review (0 findings). Within the 3-iteration budget.
- **Final test state:** 78 tests pass across the contract + scrub-unit + integration suites; 100% statement coverage on `thread_store_local.py`.
