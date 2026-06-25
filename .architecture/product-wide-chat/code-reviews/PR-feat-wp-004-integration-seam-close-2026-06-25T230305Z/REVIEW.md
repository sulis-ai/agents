# Code Review: WP-004 — Integration: close the seam; drive the Scenarios green

> **Timestamp:** 2026-06-25T230305Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/create-product-wide-chat/wp-004-integration-seam-close → change/create-product-wide-chat
> **Files changed:** 17 (563 insertions, 29 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change closes the per-product chat seam: chat turns now persist to each
product's own conversation (through a redaction-on-write path so secrets never
land on disk), the chat session runs in a real working directory for the
product instead of nowhere, and the chat panel is now actually shown in the
app. All five of the founder-facing journeys it was meant to deliver now run
green against the real app. The build is clean, the change is well-scoped to
the seam, and it includes tests at every layer plus an end-to-end check of the
five journeys. One robustness gap was found and fixed during review (a durable-
write hiccup could have taken the whole chat down); after that fix there is
nothing blocking merge.

## What to fix

No issues that need attention. One thing was found and already fixed during
review (see below); nothing else requires action.

### Fixed during review — `apps/cockpit/server/routes/chatScope.ts`

**What was happening:** Saving the founder's message to the durable history
happened *before* the chat replied, and it wasn't wrapped in any protection. If
saving that one message hit a transient problem (for example the small helper
that does the saving was briefly unavailable), the whole chat message would
fail — the founder would see an error instead of a reply.

**Why it mattered:** Being able to *have* the conversation matters more than
saving any single line of it. A momentary save problem shouldn't stop the
founder from chatting.

**What was done:** The save is now fail-soft — if it hiccups, the reply still
streams and only that one turn goes unsaved. This matches how the assistant's
reply was already saved (best-effort). Fixed inline; all tests still pass.

## How this pull request is shaped

**Size — clean.** 563 lines across 17 files, well within a reviewable size.

**Scope — clean.** Every file is part of the chat seam this change closes
(the backend store + route, the Python persistence path, the chat panel, and
their tests). No unrelated changes mixed in.

**Safety — clean.** No database migrations, no schema files, no infrastructure
changes, no secrets in the diff.

**Completeness — clean.** New behaviour is covered by tests at every layer:
Python store tests, the cross-language store contract test, the route tests,
and an end-to-end test driving all five founder journeys. The one new source
file without its own test file (the `sulis-chat-append` command) is exercised
end-to-end through the store contract test against the real on-disk path.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit`
  (server+client) clean; `eslint --ext .ts,.tsx` clean; `ruff check` clean on
  the Python surface.
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..PH-04) — scope, size,
  safety, completeness all clean.
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium — fixed inline).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one finding was fixed inline, not queued as a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (fixed) | 0 | user-turn persist was not fail-soft (fixed) |

### Build Verification (CR-01)

No PR-introduced errors. `tool-outputs/typecheck-head.log` shows the server +
client typecheck exiting 0 at HEAD. ESLint clean. Ruff clean on
`sulis-chat-append`, `chat_scope_store.py`, and the Python test.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern: the seam-close)
  module_fan_out: chat store + route + python + dock + tests (one feature)
  severity: low
Size (PH-02):
  lines_added: 563, lines_removed: 29, total: 592
  files_changed: 17
  severity: low (within reviewable band)
Safety (PH-03):
  migration_count: 0  schema_idl_count: 0  infra_files: 0  secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source_without_test: 1 (sulis-chat-append — covered by the store contract test e2e)
  api_change_without_schema: false (the wire contract is unchanged; CF-07 held)
  severity: low
```

### Findings in the Changes

#### `apps/cockpit/server/routes/chatScope.ts` — medium (quality) — FIXED INLINE

**Quoted text (before fix):**
```ts
await deps.store.groundCwd(scope);
await deps.store.appendTurn(scope, "user", prompt);
```

**Evidence:** the assistant-turn append (lower in the same handler) is wrapped
`try { … } catch {}` (fail-soft), but the user-turn append + groundCwd were
awaited unguarded — a transient failure of the vendored `sulis-chat-append`
CLI (or `mkdir`) would reject the request and 500 the chat message.

**Why it matters:** conversation availability should outrank durability of a
single turn; a momentary durable-write failure should degrade to "reply still
streams, this turn unsaved", not "chat is down".

**Fix:** wrapped `groundCwd` + user `appendTurn` in the same fail-soft
try/catch as the assistant append. Re-ran route + contract + adapter suites
(42/42 green), typecheck + lint clean.

### Findings in the Neighbours

None. The neighbour ring (the SessionBridge port, the change-scoped chat
relay, the WorkspaceShell consumers) was read; the change integrates cleanly
without exposing pre-existing gaps.

### Security lens (CR-07)

Security lens: nothing surfaced. Checks run:
- **Hardcoded secrets** — none in non-test source (the only token-shaped
  strings are test fixtures + the redaction placeholder).
- **Process-start safety** — `execFile` uses `shell: false` with a string[]
  argv (no shell interpolation); turn content travels over **stdin**, never
  argv, so a secret never reaches the process table.
- **Path traversal / SSRF** — every scope is validated by `parseChatScope`
  (wire) → `scopeKey` (TS adapter backstop, throws on a hostile scope before
  any path build or shell-out) → `_scope_key`/`validate_store_id` (Python
  on-disk backstop). Distinct scopes derive distinct keys; histories are
  physically separate directories (blending impossible by construction).
- **Redaction-on-write** — chat content is scrubbed by the single-source
  Python secret catalogue before any byte lands (proven by
  `test_append_turn_redacts_secrets_on_write` + the store contract test).
- **Read-only gate** — the new process-start (the append CLI) is allow-listed
  BY PATH in both the JS inventory gate and the bash `check-read-only.sh`, as a
  sanctioned WRITE seam; every other file stays clean.

### Architecture lens (CR-07)

Architecture lens: nothing surfaced. Checks run:
- **Dependency direction** — the route depends on the `ChatScopeStore` port,
  never an adapter; the adapter binds the Python store; no new
  domain→infrastructure import. `groundCwd` logic is single-source in the
  adapter (reused by both the route and the production bridge wiring).
- **Single-source redaction (EP-03)** — redaction stays in the Python
  catalogue; the cockpit does NOT re-implement it in TS. Script resolution
  reuses the existing `resolvePluginScriptsDir` primitive.
- **Contract conformance (CF-07)** — the wire contract (`/api/chat/:scope/*`)
  is unchanged; the shared `chatScope.contract.test.ts` still pins it; producer
  and consumer agree by the shared types.
- **Resilience** — both turn-persists are now fail-soft; the relay's existing
  one-in-flight lock + outcome mapping are reused unchanged.

### Quality lens (CR-07)

1. **Build Verification follow-up** — none (clean).
2. **JSX/template identifier scan** — the TSX change (`WorkspaceShell.tsx`)
   introduces `productList` (declared from `useProducts()`); all identifiers in
   scope. No PR-168-class bug.
3. **Dead surface** — none; every new port method (`appendTurn`, `groundCwd`)
   has a runtime consumer (route + bridge) and tests.
4. **Contract drift** — none; the wire shapes are unchanged.
5. **Test coverage** — strong: Python (9 store tests incl. redaction + per-
   scope isolation), TS store contract (appendTurn round-trip + groundCwd +
   redaction, both adapter + fake), route (persist user-before / assistant-
   after / not-on-unreachable / cwd), e2e (5 scenarios driven green over the
   real interface, both themes a11y).
6. **Style/readability** — clean; comments explain the folded-concern closure
   + the filename-convention alignment.
7. **Performance (CR-10)** — no anti-pattern matches. The per-turn `execFile`
   is one process per chat send (already a heavy operation); no loop-bound IO,
   no N+1.

### Watch List

- The TS `scopeKey` mirrors the Python `_scope_key` (a cross-language
  derivation that cannot be DRY-shared). Both are guarded + tested; kept in
  sync by the shared contract test. No action — noted for awareness.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client`
  (0 errors HEAD), `eslint --ext .ts,.tsx` (clean), `ruff check` (clean).
  Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 563 lines / 17 files (above carve-out);
  the three lenses were applied as distinct passes over the full diff +
  neighbour ring.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end
  (the route, adapter, store, ports, dock, shell, tests).
- [✓] **CR-04 Evidence discipline.** The one finding cites file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied: 1 medium (fixed inline). No
  critical/high.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read end-to-end; all lenses output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each
  produced explicit output (findings or "nothing surfaced. Checks run: …").
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size low, Safety none,
  Completeness low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-product-wide-chat` + untracked
  (`product-wide-chat.spec.ts`, `sulis-chat-append`).
- **Neighbour expansion:** SessionBridge port, change-scoped chat relay,
  WorkspaceShell consumers, read-only gates (git grep).
- **Scanners run:** typecheck (tsc), lint (eslint), ruff; secret/perf/path
  scans by targeted git-diff greps.
- **Lenses:** three lenses applied over the full diff (no sampling).
