# Work Packages — chat-experience-both-universal-change (chat parity + working↔finished signal)

> Change: CH-9642DA · feat · Tier S
> Source: `.architecture/chat-experience-both-universal-change/TDD.md`
> Decomposed: 2026-06-27 · 6 WPs (1 signed-off contract gate + 5 implementation)
> Visual contract: signed 2026-06-27 (`provenance: production-approved`)

> All implementation WPs are `pending` (the builder's "to run" state). Readiness
> is computed from `Depends On`: WP-002 and WP-003 are ready now; WP-004/005/006
> become ready as their dependencies close.

## ▶ Ready to start (2)

The visual-contract gate (WP-001) is signed, so its dependents unblock:

- WP-002 — Shared `ChatStatusLine` (working↔finished, derived)   (frontend)
- WP-003 — Universal chat TurnCard parity + markdown             (frontend)

WP-002 and WP-003 touch different files (status line vs `ProductChat`), so they
can run in parallel.

## ⏸ Pending — waiting on a dependency to close (3)

- WP-004 — Composer status line + de-collision fix
       └─ waiting on WP-002 (mounts `ChatStatusLine`)
- WP-005 — Dock status line (universal)
       └─ waiting on WP-002 (mounts the same `ChatStatusLine`)
- WP-006 — Extend no-raw-colours coverage to status-line surfaces
       └─ waiting on WP-002 + WP-004 + WP-005 (the modules it scans must exist)

> WP-004 and WP-005 become ready the moment WP-002 lands, and touch different
> files (`Composer` vs `ProductChatDock`), so they run in parallel. WP-006
> serialises last — it widens the gate over the modules the others produce.

## ✅ Done (1)

- WP-001 — Chat parity + status-line visual contract (sign-off gate)
       └─ signed 2026-06-27; `provenance: production-approved`

---

## WP table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Chat parity + status-line visual contract (sign-off gate) | REINFORCE-Document | done | — | WP-002, WP-003, WP-004, WP-005, WP-006 |
| WP-002 | Shared ChatStatusLine (working↔finished, derived) | EXPAND-Create | in_progress | WP-001 | WP-004, WP-005, WP-006 |
| WP-003 | Universal chat TurnCard parity + markdown | SUBSTITUTE-Replace | in_progress | WP-001 | — |
| WP-004 | Composer status line + de-collision fix | REORGANISE-Refactor | pending | WP-001, WP-002 | WP-006 |
| WP-005 | Dock status line (universal) | EXPAND-Extend | pending | WP-001, WP-002 | WP-006 |
| WP-006 | Extend no-raw-colours coverage to status-line surfaces | REINFORCE-Test | pending | WP-002, WP-004, WP-005 | — |

---

## Detail table (kind / group / verification / source)

| ID | kind | group | verification shape | est. tokens | source |
|---|---|---|---|---|---|
| WP-001 | frontend | reinforce | na (sign-off gate) | ~3k | spec#45 / UXD-14 |
| WP-002 | frontend | expand | concrete — `ChatStatusLine.test.tsx` | ~13k | ADR-002 |
| WP-003 | frontend | substitute | concrete — `ProductChat.turncard.test.tsx` | ~14k | ADR-001 / ADR-003 |
| WP-004 | frontend | reorganise | concrete — `Composer.test.tsx` | ~16k | ADR-002 / ADR-004 |
| WP-005 | frontend | expand | concrete — `ProductChatDock.states.test.tsx` | ~12k | ADR-002 |
| WP-006 | frontend | reinforce | concrete — `no-raw-colours.thread-chat.test.ts` | ~8k | ADR-004 |

## Verification shapes (per WP)

All implementation WPs are **concrete** (ADR-003 shape 1) — each ships its own
Vitest spec the moment it lands. WP-001 is `na: true` (sign-off gate). None
deferred. Characterisation-first (EP-07) applies to WP-003 (`ProductChat`) and
WP-004 (`Composer` — the existing FR-19/22/26 cases are the characterisation
gate the refactor must not regress).
