# Work Packages — portable-agent-context (CH-GJ9KQR)

> Contract-first decomposition (CONTRACT_FIRST CF-05): the `contract` WP comes
> first; producers + consumers run in parallel against it; the integration WP
> closes the seam (CF-07 + CF-12). Tier M. Ready-first: **WP-001**.
>
> **Remediation wave (2026-06-24).** A `/sulis:prove` consumer-level reality
> check found the headline capability built as components but NOT wired into the
> live system: WP-007's drive proved the assembler directly, not the live
> `SessionManager` spawn/resume path. **WP-009** wires the live assemble→inject
> resume path with real Working Set + brain readers (the live-path acceptance for
> the headline). **WP-010** closes the OpenAI-key redaction blind spot on the
> store-write surface. Both depend only on done WPs and are mutually parallel.

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Thread/Message/Memory + payload contract | expand-create | done | — | WP-002, WP-003, WP-005, WP-008 |
| WP-002 | ThreadStore local adapter (durable, append-only, redaction) | expand-create | done | WP-001 | WP-004, WP-006, WP-007, WP-010 |
| WP-003 | ContextPayloadAssembler (tiered, vendor-neutral) | expand-create | done | WP-001 | WP-004, WP-007 |
| WP-004 | Session-pump durable sink + resume seed | reinforce-instrument | done | WP-002, WP-003 | WP-006, WP-007 |
| WP-005 | thread_context MCP discovery tool | expand-create | done | WP-001 | WP-007 |
| WP-006 | Cockpit raw-view reads our store (strangle) | substitute-strangle | done | WP-002, WP-004 | — |
| WP-007 | Integration — mock→real + conformance + resume drive (component-level) | expand-create | done | WP-002, WP-003, WP-004, WP-005 | WP-009 |
| WP-008 | Thread mint-candidate record (no mint) | expand-create | done | WP-001 | — |
| WP-009 | Live assemble→inject resume wiring (real Working Set + brain readers) | reinforce-instrument | pending | WP-002, WP-003, WP-004, WP-005, WP-007 | — |
| WP-010 | Scrub modern OpenAI keys on write to the thread store | reinforce-harden | pending | WP-002 | — |

## Dependency shape

```
WP-001 (contract, READY FIRST)
  ├── WP-002 (store) ─┐
  ├── WP-003 (assembler) ─┤
  │                       ├── WP-004 (pump sink + resume seed) ──┐
  ├── WP-005 (MCP tool) ──┼──────────────────────────────────────┤
  └── WP-008 (mint candidate, docs)                              │
                          WP-002, WP-004 ── WP-006 (cockpit, optional)
                          WP-002+003+004+005 ── WP-007 (integration / seam-close, component-level)
                                                   └── WP-009 (LIVE assemble→inject resume wiring)
                          WP-002 ── WP-010 (OpenAI-key scrub on write)
```

- **Ready first:** WP-001 (the contract — nothing else starts until it lands).
- **Parallel after WP-001:** WP-002, WP-003, WP-005, WP-008 run concurrently.
- **Join 1:** WP-004 needs the store (WP-002) + assembler (WP-003).
- **Join 2 (seam-close):** WP-007 needs WP-002/003/004/005; drives the
  load-bearing provider-independent-resume journey at the **component** level
  (CF-12).
- **Optional / deferrable:** WP-006 (cockpit raw-view re-point) — closes the
  UI lock-in; can land in the follow-on per its removal plan.
- **Remediation (ready now — all deps done):** **WP-009** (live assemble→inject
  resume wiring, the live-path acceptance for the headline) and **WP-010**
  (OpenAI-key scrub on write) run **in parallel** — disjoint file scopes
  (WP-009: `manager.py` / `durable_sink.py` / readers; WP-010:
  `_secret_patterns.py`).

## Extra metadata (second table — not parsed by the run-all loop)

| ID | kind | verification artifact | est. tokens (in/out) |
|---|---|---|---|
| WP-001 | contract | test_thread_store_contract.py | 12k / 6k |
| WP-002 | backend | test_thread_store_local.py | 14k / 10k |
| WP-003 | backend | test_context_payload_assembler.py | 13k / 9k |
| WP-004 | backend | test_durable_append_sink.py | 16k / 9k |
| WP-005 | backend | test_thread_context_mcp_contract.py | 11k / 7k |
| WP-006 | frontend | useTranscript.test.ts | 12k / 8k |
| WP-007 | composite | test_provider_independent_resume.py (component-level) | 14k / 8k |
| WP-008 | docs | (na — docs only) | 6k / 3k |
| WP-009 | backend | test_live_resume_injection.py (LIVE manager path) | 16k / 10k |
| WP-010 | backend | test_secret_patterns.py (+ outbound + store-write redaction) | 9k / 5k |
