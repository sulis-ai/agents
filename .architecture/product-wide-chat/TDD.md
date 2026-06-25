# Technical Design — Product-wide (per-product) chat experience

> **Change:** CH-G3Y4RM · **Project:** product-wide-chat · **Tier:** M (see `SIZING.md`)
> **Design artifact for the look:** the SIGNED visual contract
> `.architecture/product-wide-chat/contracts/visual/product-wide-chat.contract.md`
> + mockup `product-wide-chat.html` (signed_off_at 2026-06-25, production-approved).
> The build verifies against the mockup (UX_VISUAL_DESIGN_STANDARD post-build check).
> **This is a composition change.** Almost nothing is built from zero; the TDD maps
> reuse and names four load-bearing decisions (ADR-001..004).

---

## 1. What we're building

A chat scoped **per product**, switched by the existing `ProductSwitcher` so one switch
re-scopes the **board AND the chat together**. Each product keeps its **own conversation
history** (durable, never blended). The **Claude ↔ Antigravity** choice lives at the
composer foot, remembered per product, and drives the real session provider. Asking the
chat to start work surfaces a **confirm**, then a **card on that product's board**. "All
products" is a **cross-product overview chat** that asks which product new work belongs to.

The four decisions that make this real are the four ADRs:

- **ADR-001** — extend the concierge composer family; board central, chat docked right.
- **ADR-002** — key the durable thread by product scope; one thread per product.
- **ADR-003** — the agent picker drives the daemon provider seam (replaces the `pty` hardcode).
- **ADR-004** — chat→card reuses `start-from-intent`; the overview chat collects product first.

---

## 2. Form — structural integrity (the reuse map)

This change adds a thin layer over shipped building blocks. The domain owns the *ports*;
the existing pieces are the *adapters/implementations* behind them.

### 2.1 Frontend (apps/cockpit/client/src)

| New / extended | Built on (reuse) | Role |
|---|---|---|
| `ProductChatDock` (new shell) | layout shell; `ProductControl` tile | The right-docked, collapsible chat region; header echoes the active product tile |
| `ProductChat` (extend) | `ConciergeChat` + `ChatMessage` + chips/slash bubble | The per-scope transcript + composer |
| `AgentPicker` (new) | `ProductControl` menu primitive | Claude/Antigravity choice at the composer foot; `menuitemradio` + `aria-checked` |
| `useProductChat` (new hook) | `useConciergeStream` pattern; `useActiveProduct` | Resolves `chat_scope` from active product; streams the scope's thread |
| chat→card embed | `useStartFromIntent` + `StartFromIntent` confirm UI | propose→confirm→card on the product board |

The dock reads the single source of truth for active scope — `useActiveProduct()` —
which `ProductSwitcher.onSelect` already feeds. **One switch, both surfaces** because the
board and the dock both key off `activeProductId`; no new control, no second vocabulary
(CL-05).

### 2.2 Backend (apps/cockpit/server + session manager)

| New / extended | Built on (reuse) | Role |
|---|---|---|
| `chat_scope` resolver | `LocalThreadStore`, `thread_contract` | Maps product scope → durable thread root `~/.sulis/chat/{chat_scope}/threads/` (ADR-002) |
| provider-on-open | `resolveChange` (`index.ts:275`) → `SessionSpec.provider` → daemon `_adapters.get` | Replaces `{provider:"pty"}` with the scope's resolved provider (ADR-003) |
| chat→card | `start-from-intent` orchestrator (`POST /api/changes/start-from-intent`) | Confirm-gated, product-scoped change-create (ADR-004) |

**Dependency direction holds:** the dock depends on the client API funnel (a port); the
funnel depends on the server routes (a port); the server depends on the daemon/store
through existing adapters. No new domain→infrastructure import is introduced.

### 2.3 The client↔server seam (contract-first)

This change crosses a frontend↔backend producer/consumer seam. The **seam contract**
(decomposed first, per CONTRACT_FIRST_STANDARD CF-07/CF-12) is the per-product chat API:

```
GET    /api/chat/{chatScope}/thread        → { messages: ThreadMessage[], provider: "pty"|"agy", productId|null }
POST   /api/chat/{chatScope}/message        body { prompt } → SSE { state | chunk* | complete }
                                              opens/relays the scope's session on the resolved provider
PUT    /api/chat/{chatScope}/provider       body { provider: "pty"|"agy" } → { provider, applied: "new-work" }   (AI-03 guarded)
POST   /api/changes/start-from-intent        (REUSED verbatim — ADR-004) body { phase, productId, intent, kind }
```

`chatScope` ∈ `product:{id}` | `product:__all__` | (reserved) `product:__unassigned__`.
The contract is the wire shape the client sends and the server resolves — frontend and
backend WPs build against it in parallel, then an integration WP closes the seam.

---

## 3. Armor — operational hardening

The shipped seams (daemon, thread store, change-start) already carry their hardening
(append-only invariants, secret-scrub-on-write, single-flight locks, `UNKNOWN_PROVIDER`
guard, fail-closed confirm gate). This change adds:

| Primitive | Where | Detail |
|---|---|---|
| **Provider fallback** | provider-on-open (ADR-003) | Unknown/absent provider → safe default `pty`; client only ever sends a registered key; daemon's `UNKNOWN_PROVIDER` is the backstop |
| **AI-03 guard — mid-run switch** | `PUT /provider` | Switching while a session runs is a confirm gate; choice applies to **new work**, never re-homes a live run |
| **AI-03 gate — chat→card** | chat→card (ADR-004) | Reuses `confirmGate.ts` propose→confirm; no card filed without confirm |
| **AI-07 honest identity** | composer foot | Names the **running** provider (from the live session), not the picked-but-unapplied one; status by glyph+word, not colour |
| **Scope isolation** | `chat_scope` root | Per-scope thread directories — histories are physically separate; blending is impossible by construction |
| **No new third-party touch** | — | The agy adapter already landed its Platform Contract; this change consumes the existing provider seam (spec confirms) |

Observability: the chat message relay and session open already emit through the existing
session-manager event path; this change adds no new external call requiring its own
timeout/retry/CB beyond what the daemon and thread store already enforce.

---

## 4. Proof — verification protocol

| Layer | Test | Real, not mock |
|---|---|---|
| Seam contract | Contract test on the `/api/chat/{chatScope}/*` shape — client funnel ↔ server route agree on wire shape (CF-07 conformance) | Shared contract test exercised by both sides |
| Backend — thread keying | `LocalThreadStore` rooted at a chat scope: two scopes → two thread directories; switching scope returns the right history; histories never blend | Real `LocalThreadStore` on a temp dir (no mock) |
| Backend — provider-on-open | Open scope with `provider:"agy"` spawns the agy adapter; `pty` spawns Claude; unknown → `pty` fallback | Real daemon adapter registry (or the CI fake-child seam `SULIS_DAEMON_PTY_CHILD`) |
| Backend — chat→card | propose→confirm with a `productId` returns a `Change`; the card resolves onto that product's board scope | Real `start-from-intent` orchestrator |
| Frontend — a11y (gate) | jest-axe / Playwright-axe on the dock: switcher + agent picker are real menus (`role=menu`, `menuitemradio`, `aria-checked`), full keyboard parity, visible focus, status legible without colour, reduced-motion fallback | jest-axe + Playwright-axe (WPF-13 a11y gate) |
| Frontend — visual | Post-build visual check of the shipped surface against `product-wide-chat.html`, light + dark | UX_VISUAL_DESIGN_STANDARD check |
| Integration (seam close) | Drive switch product → board+chat swap; talk→card; pick/switch agent; overview chat asks which product | Real app, real interface (the authored Scenarios) |

A11y is a **gate** on the frontend WPs (WPF-13), not an afterthought.

---

## 5. Build sequence (contract-first, cross-kind)

1. **Seam contract WP** (the `/api/chat/{chatScope}/*` shape + `chat_scope` vocabulary + contract test). **First — blocks the parallel pair.**
2. **Backend WP** (thread keying + provider-on-open + chat→card wiring) ‖ **Frontend WP** (dock + ProductChat + AgentPicker + switcher tie-in + chat→card embed + three states). **Parallel against the contract.**
3. **Integration WP** (close the seam: switch swaps both surfaces; provider drives real session; the authored Scenarios go green). **Last.**

Right-sized: one contract WP + two kind WPs (the frontend WP is itself sizeable but stays one WP because it's one coherent surface against one contract) + one integration WP = **4 WPs**. See `work-packages/INDEX.md`.

---

## 6. Out of scope (spec non-goals — preserved)

The "Unassigned" triage chat (key reserved, not built); per-product memory transparency;
multiple threads per product; an "Auto" agent option; mid-run pause/stop; the auto
Claude→agy failover trigger (agy Phase 2). No change to the board's scoping logic or the
data model.

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This change is `founder_facing: true` → user-facing journeys are verified as living
**Scenarios** at ship (the scenario gate). The authored scenarios live alongside this TDD
(see `work-packages/INDEX.md` → Scenarios) and concretise the spec's Verification Plan.

**1. User-observable behaviour verified.** Pick a product → board AND chat both swap to
that product; each product's history is its own and never blends; talk → confirm → a card
on that product's board, clickable through; pick/switch the agent (guarded mid-run); the
overview chat asks which product before filing; a11y holds in both themes.

**2. Verification environment(s).** Local dev (the cockpit client+server against a real
session-manager daemon + `LocalThreadStore` on a temp root) for the integration scenarios;
CI for the contract test, backend unit/integration tests, and jest-axe; a Playwright run
(Playwright-axe + visual) drives the dock for the a11y + visual scenarios.

**3. Bootstrap-from-zero.** A fresh clone at the merge SHA can: build the cockpit client +
server; run the contract test (`tests/contract/chat-scope.contract.*`); run the backend
thread-keying + provider-on-open integration tests against a temp store root + the daemon
fake-child seam (`SULIS_DAEMON_PTY_CHILD`); run jest-axe on the dock. No external account
is needed — the agy adapter is consumed through the daemon, exercised via the registry, not
a live Antigravity backend.

**4. Per-integration verification strategy.**

| Integration | Strategy | Class | TDD concretion (shape) |
|---|---|---|---|
| client ↔ server chat-scope API | contract test | existing seam (new shape) | **concrete** — `tests/contract/chat-scope.contract.test.ts` asserts request/response shape both sides agree on; test seam = the API funnel boundary |
| server ↔ thread store | in-memory + real-on-temp adapter | existing | **concrete** — `LocalThreadStore` on `mktemp` root; assert two scopes → two dirs, no blend |
| server ↔ daemon provider seam | real registry via fake-child | existing | **concrete** — open with `agy`/`pty`/unknown; assert adapter chosen / fallback; uses `SULIS_DAEMON_PTY_CHILD` CI seam, no live Antigravity |
| chat → start-from-intent | real orchestrator | existing | **concrete** — propose→confirm→`Change`; card resolves to product board scope |
| dock a11y | jest-axe + Playwright-axe | existing | **concrete** — WPF-13 gate; menus, keyboard, focus, colour-independent status, reduced-motion |
| dock visual | post-build check vs mockup | existing | **concrete** — UX_VISUAL_DESIGN_STANDARD against `product-wide-chat.html`, light + dark |

No `deferred` or `out-of-scope` integrations — every seam is exercised at ship.

**5. Per-kind verification adapter.** This change is cross-kind.
- `backend` kind → pytest/vitest nodeids for thread-keying, provider-on-open, chat→card
  (e.g. `apps/cockpit/server/.../chatScope.test.ts::resolves per-product thread`,
  `plugins/sulis/scripts/_session_manager/tests/test_chat_scope_store.py::test_two_scopes_two_threads`).
- `frontend` kind → Vitest specs + jest-axe + Playwright-axe specs for the dock, switcher
  tie-in, agent picker, chat→card, three states, and the visual check.

**6. Infrastructure needs surfaced (deferred).** None new. The agy adapter, thread store,
and start-from-intent orchestrator all ship already; no vendor mock, test OAuth account, or
seed fixture must be built that isn't present. (Canonical-identifier list: empty.)

### Contradictions with the spec's Verification Plan

None. The spec's Verification Plan journeys map 1:1 to the authored Scenarios; the TDD adds
the test-artifact concretions (paths, seams, fallback assertions) without contradicting any
named strategy.

---

## Sizing Report

> Cross-references `SIZING.md`.

- **Tier:** M (computed sFPC ~10, ASR ~10; confirmed M).
- **TDD length:** proportionate to M and deliberately trimmed — this is a composition
  change, so Form is a reuse map, not a re-derivation. Within tier target; no circuit
  breaker triggered.
- **ADRs:** 4 produced vs M maximum — all four are the load-bearing cross-component
  decisions the spec's "Open questions for design" named explicitly (dock layout, thread
  keying, provider-on-open, chat→card). Not a quota; each rejects a viable alternative.
- **Authoritative sources referenced:** the SIGNED visual contract (the look) — referenced,
  not restated. No context index / External ADR Registry present (new ADRs start at 001).
- **Restated authoritative ground:** none — the visual contract and the shipped seams are
  referenced by path, not reproduced.
