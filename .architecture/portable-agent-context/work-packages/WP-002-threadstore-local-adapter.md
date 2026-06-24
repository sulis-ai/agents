---
id: CH-GJ9KQR-WP-002
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: expand-create
group: expand
title: ThreadStore local adapter — durable, append-only, redaction-on-write
status: pending
dependsOn: [CH-GJ9KQR-WP-001]
implements:
  - "spec:create-portable-agent-context#every-message-tracking"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_thread_store_local.py
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "TDD.md§3.2, §4, ADR-002"
estimatedTokenCost:
  input: ~14k
  output: ~10k
---

## Context
TDD §3.2 + §4. The durable local adapter behind the `ThreadStore` port (WP-001).
This is the new persistence surface — append-only message log + versioned
ThreadMemory under `~/.sulis/changes/{change_id}/threads/` (the CF-11 pinned
path from WP-001). **EXPAND-Create** — implements the port the cockpit domain
owns; the filesystem/db is *called by* the adapter, not wrapped at the seam.

## Contract
Implements `ThreadStore` (WP-001) over local persistence. Append is write-once;
ordering is the monotonic offset convention. Redaction runs **on write**,
reusing `_secret_patterns` (TDD §4). `platform_id="local"` (ADR-002).

## Definition of Done
**Red** — runs the **shared** `test_thread_store_contract.py` (WP-001) against
this real adapter (no mocks — MEA-09), plus `test_thread_store_local.py`
asserting: durability across process restart; append-only rejects rewrite /
out-of-order (ExpectedError); a token-shaped secret is scrubbed before bytes
land. Failing first.
**Green** — boring local persistence; the contract + integration tests pass.
**Blue** — the adapter touches IO in exactly one place; no provider/web import
(dependency-inward, WPB-01); shares the contract test with the in-memory stub.

## Verification
Shape 1 (concrete): `adapter: backend`,
`artifact: .../test_thread_store_local.py`.

> Note from WP-001 security review (ADVISORY, fold in here): tighten the
> `validate_store_id` guard in `thread_contract.py` — its regex anchors with
> `$` (accepts a trailing newline, e.g. `"abc\n"`). Not a traversal breach, but
> since this durable on-disk adapter builds on that guard, switch `$`→`\Z` (or
> `re.fullmatch`) and add a `"abc\n"` rejection test while you're here.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-002-threadstore-local-adapter (deleted post-merge)
- Completed: `2026-06-24T17:46:16Z` (Step 12 by calling session)
