# Work Packages — autonomous-delivery-environment (CH-01KT50)

> **Change:** `create-autonomous-delivery-environment` · `change_id: 01KT500K2JTE2EGW6TPPQ4D4VN`
> **Derived — do not hand-edit.** Regenerated from `WP-*.md` frontmatter.
> **Decomposition:** contract-first cross-kind (lightweight internal seam, CF-05/WP-08.5).
> **Order:** contract → backend + frontend in parallel where independent → integration last.

## Shape

16 WPs: **2 contract** · **8 backend** · **5 frontend** · **1 integration**.
The two-way chat is the sensitive write/act path — its WPs (008, 009, 010, 015)
carry the NFR-SEC constraints (act only on the targeted change's session;
read-only preserved elsewhere) and the resume/spawn/incomplete-step behaviour
(FR-24/25/26/N5).

---

## ▶ Ready to start now (no unmet deps) — 2

- **WP-001** — Data contract: extend shared/api-types.ts + lock the OpenAPI seam   (contract, 3h)
- **WP-006** — SessionBridge port + contract test (resolve + relay seam)            (backend, 5h) · dep WP-001 *(see note)*

> **WP-002** (visual contract) is already `done` — it records the **signed-off**
> visual contract (`signed_off_at: 2026-06-03T08:31:03Z`, `provenance:
> production-approved`). It is the #45 gate the frontend WPs depend on; it does
> not need "starting".
>
> Strictly, only **WP-001** has zero unmet deps. WP-006 lists `WP-001` as a dep
> (it imports `ChatStreamEvent`); they are tiny and can be done back-to-back or
> in one sitting. Everything else waits on WP-001 landing.

## 🔒 Done (the signed gate) — 1

- **WP-002** — Visual contract: the one coherent surface (board → thread) — SIGNED OFF (contract) · `signed_off_at` + `production-approved` carried verbatim

## ⏸ Blocked on a dependency — 13

### Backend (reads — parallel once WP-001 lands)
- **WP-003** — GET /api/changes/:id/status (plain-English status)   (backend, 4h) · dep WP-001
- **WP-004** — GET /api/changes/:id/brain (entities grouped by kind) (backend, 4h) · dep WP-001
- **WP-005** — GET /api/search (content + stage + needs-attention)   (backend, 5h) · dep WP-001, WP-003

### Backend (chat path — parallel once WP-006 lands)
- **WP-007** — RecordedSessionBridge fixture (live/resume/spawn/mid-step) (backend, 6h) · dep WP-006
- **WP-008** — Binding guard + one-in-flight lock (pure libs)             (backend, 4h) · dep WP-006
- **WP-010** — StreamJsonSessionBridge production adapter                 (backend, 8h) · dep WP-006
- **WP-009** — POST …/chat (SSE relay) + read-only-gate extension         (backend, 8h) · dep WP-001, WP-006, WP-007, WP-008

### Frontend (surfaces — parallel once their deps land; all dep the SIGNED WP-002)
- **WP-011** — Board stage-column Kanban (refactor Dashboard) + tokens refresh (frontend, 8h) · dep WP-001, WP-002
- **WP-012** — Thread shell: stage track + status header (refactor ThreadView)  (frontend, 7h) · dep WP-001, WP-002, WP-003
- **WP-013** — Brain view (grouped) + rendered previews (reuse renderer)        (frontend, 7h) · dep WP-001, WP-002, WP-004, WP-012
- **WP-014** — Board toolbar: search + stage + needs-attention filters          (frontend, 5h) · dep WP-001, WP-002, WP-005, WP-011
- **WP-015** — Two-way chat: composer + SSE stream client                       (frontend, 9h) · dep WP-001, WP-002, WP-009, WP-012

### Integration (last)
- **WP-016** — Chat bridge end-to-end (mock→real) + a11y/visual sweep + from-graph acceptance (composite, 6h) · dep WP-009, WP-010, WP-011, WP-012, WP-013, WP-014, WP-015

---

## Dependency graph

```
WP-002 (visual contract, SIGNED, done) ───────────────┐ (frontend #45 gate)
                                                       │
WP-001 (data contract) ──┬─ WP-003 (status) ──┬─ WP-005 (search) ──────┐
                         │                     │                        │
                         ├─ WP-004 (brain) ────────────────────┐       │
                         │                                      │       │
                         └─ WP-006 (SessionBridge port+contract)│       │
                                  ├─ WP-007 (recorded fixture) ─┤       │
                                  ├─ WP-008 (binding + lock) ───┤       │
                                  ├─ WP-010 (prod adapter) ─────┤       │
                                  └─ WP-009 (relay + gate) ◀────┘ (001,006,007,008)
                                                                  │
   frontend (all also dep WP-002):                                │
   WP-011 (board) ◀── 001,002                                     │
   WP-012 (thread shell) ◀── 001,002,003                          │
   WP-013 (brain+previews) ◀── 001,002,004,012                    │
   WP-014 (search bar) ◀── 001,002,005,011                        │
   WP-015 (chat composer) ◀── 001,002,009,012                     │
                                                                  │
   WP-016 (integration) ◀── 009,010,011,012,013,014,015 ──────────┘
```

## Suggested execution waves

| Wave | WPs | Why |
|---|---|---|
| 0 | WP-002 (already done) | The signed visual contract; gate already open |
| 1 | **WP-001** | The data seam; unblocks everything |
| 2 | WP-003, WP-004, WP-006 | Reads + the chat keystone — parallel after WP-001 |
| 3 | WP-005, WP-007, WP-008, WP-010, WP-011 | Search + chat-path siblings + board — parallel |
| 4 | WP-009, WP-012 | Relay (needs 006/007/008) + thread shell (needs 003) |
| 5 | WP-013, WP-014, WP-015 | Brain/previews, search bar, chat composer |
| 6 | WP-016 | Integration + from-graph acceptance — last |

## Status legend

`pending` ready · `done` merged/closed · `blocked` waiting on a dep.
Visual-contract WP-002 carries the founder sign-off (#45) so frontend WPs can proceed.
