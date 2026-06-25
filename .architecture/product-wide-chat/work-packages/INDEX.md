# Work Packages — product-wide-chat (CH-G3Y4RM)

> Contract-first, cross-kind. WP-001 (the seam contract) ships first and blocks the
> parallel pair (WP-002 backend ‖ WP-003 frontend); WP-004 closes the seam and drives the
> founder-facing Scenarios green. Tier M (see `../SIZING.md`). Design artifact for the look:
> the SIGNED visual contract `../contracts/visual/product-wide-chat.html`.

| ID | Title | Primitive | Status | Depends On | Blocks |
|----|-------|-----------|--------|------------|--------|
| WP-001 | Per-product chat-scope seam contract (API + contract test) | Create | done | — | WP-002, WP-003, WP-004 |
| WP-002 | Backend — thread keying, provider-on-open, chat→card | Create | done | WP-001 | WP-004 |
| WP-003 | Frontend — chat dock, agent picker, switcher tie-in, chat→card, three states | Create | done | WP-001 | WP-004 |
| WP-004 | Integration — close the seam; drive the Scenarios green | Create | step-7-complete | WP-002, WP-003 | — |
| WP-005 | Make detect_secrets optional in the shared scrub (degrade to the catalogue) | reinforce-harden | step-7-complete | — | — |

## Detail (kind, verification artifact, source)

| ID | Kind | Verification artifact | Source |
|----|------|-----------------------|--------|
| WP-001 | backend | `apps/cockpit/server/tests/contract/chatScope.contract.test.ts` | TDD §2.3 |
| WP-002 | backend | `plugins/sulis/scripts/_session_manager/tests/test_chat_scope_store.py` | TDD §2.2 / ADR-002,003,004 |
| WP-003 | frontend | `apps/cockpit/client/src/tests/ProductChatDock.axe.test.tsx` (a11y gate) | TDD §2.1 / ADR-001,004 |
| WP-004 | frontend | `apps/cockpit/client/e2e/product-wide-chat.spec.ts` (Scenarios 1–5) | TDD §4–5 |

## Sequence

```
WP-001 (contract)
   ├──> WP-002 (backend)  ─┐
   └──> WP-003 (frontend) ─┴──> WP-004 (integration / Scenarios)
```
