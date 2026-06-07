# Work Packages — feat: live-origin-stamping (CH-01KTHP)

> Sourced from `.architecture/feat-live-origin-stamping/TDD.md`.
> Doctrine: `WP_BACKEND_STANDARD`. Cross-kind decomposition per WP-08.5
> (contract WP first; TS + Python tracks parallel; live round-trip last).

## Sequence graph

```
WP-001 (contract: widen spawnBridge port)
  ├─> WP-002 (bridge forwards originEnv to spawn)              ─┐
  └─> WP-003 (ConversationIdentity port + local adapter +      ─┤
              relay helper: Thread id + Message ordinal)        │
                                                                └─> WP-004 (relay wires assisted origin
                                                                            + inferred path reconciles, #23)

WP-005 (executor exports autonomous SULIS_ORIGIN)   [independent — Python track]

WP-004 + WP-005 ─> WP-006 (grammar conformance + live likely→exact round-trip)
```

## Ready first (no unmet deps)

- **WP-001** — pin the widened port contract (TS track gate).
- **WP-005** — executor autonomous export (Python track; fully independent).

These two can start in parallel immediately.

## Orchestrator Config
max_parallel: 3

## Order

> Canonical header (`| ID | Title | Primitive | Status | Depends On | Blocks |`).
> `kind:` is carried in each WP file's frontmatter (backend / integration), not
> as an INDEX column. Track grouping: WP-001..004 = TS (chat relay); WP-005 =
> Python (executor); WP-006 = live verification.

| ID | Title | Primitive | Status | Depends On | Blocks |
|----|-------|-----------|--------|------------|--------|
| WP-001 | Pin widened spawnBridge port contract (originEnv) | reinforce-document | step-7-complete | — | WP-002, WP-003 |
| WP-002 | Bridge adapter forwards originEnv to the spawn | expand-create | pending | WP-001 | WP-004 |
| WP-003 | Conversation-identity port + local adapter + relay-origin helper (Thread id + Message ordinal) | expand-create | pending | WP-001 | WP-004 |
| WP-004 | Relay wires assisted Thread/Message origin; inferred path reconciles (closes #23) | expand-create | pending | WP-002, WP-003 | WP-006 |
| WP-005 | Executor exports autonomous SULIS_ORIGIN at commit | expand-create | step-7-complete | — | WP-006 |
| WP-006 | Grammar conformance + live likely→exact round-trip | reinforce-test | pending | WP-004, WP-005 | — |

## Notes

- **Identity modelled on the communication service (ADR-016/018).** WP-003/004
  carry a `thread_`-shaped Thread id as `conversation` and the 1-based Message
  ordinal as `turn`. The **trailer grammar is unchanged** — only the computed
  values change. **No cross-service call this change**: a domain-owned
  `ConversationIdentity` port (WP-003) is the seam; its only adapter derives the
  identity locally/read-only. The live Thread/Message repository adapter is a
  clean later WP (the one founder scope call — see TDD §7).
- **One new domain-owned port + one local adapter (ADR-002 shape), no new spawn
  site, no gate change.** WP-001/002 widen one existing port signature (ADR-017);
  the read-only gate already allow-lists `chat.ts` + the bridge by path; the new
  port + adapter are pure reads under allow-listed cockpit paths. Each TS WP's
  Blue re-asserts `check-read-only.sh`.
- **WP-004 is composite** (EXPAND-Create relay wiring + REORGANISE-Refactor of the
  inferred path). The refactor carries a **characterisation test first**
  (`InferredOriginAttribution.test.ts`) and **closes the #23 multi-session TODO**
  by indexing turns per transcript with a Thread id per transcript. The inferred
  path uses the SAME shared `threadIdentity` helper as the relay (EP-03) so
  recorded and inferred render the same id (likely→exact display parity).
- **Consume #216 unchanged.** No WP re-implements the trailer format, the hook, or
  the read path. WP-003/005 emit the exact grammar #216's `parse_origin_env` accepts;
  WP-006 locks that conformance.
- **WP-001 and WP-005 are shipped (step-7-complete) and unaffected by the remodel:**
  WP-001 widened the generic `originEnv` dict (opaque to the value model); WP-005
  is the autonomous path (run-ulid, no threads/messages).
- **Live round-trip is WP-006 and mandatory** — CI stubs the `claude` child, so
  likely→exact is only provable with a real child on the founder's machine.
