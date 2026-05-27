# SIZING — terminal-launcher-port

> **Generated:** 2026-05-25
> **Source artifacts:** `.specifications/terminal-launcher-port/HANDOFF_TO_SEA.md`
> **Tier:** S (small) — computed; user accepted

## sFPC

| Type | Count | Items |
|---|---|---|
| ILF (Internal Logical File) | 1 | The spawned-terminal session (transient; lifetime = founder's terminal window) |
| EIF (External Interface File) | 0 | (no external systems) |
| EI (External Input) | 1 | `launch_change_terminal(change_id, worktree_path)` call |
| EO (External Output) | 0 | (the spawned terminal is operator UX, not a derived dataset) |
| EQ (External Query) | 0 | (no retrieval — write-only spawn) |
| **Total sFPC** | **2** | |

## ASR

| Type | Count | Items |
|---|---|---|
| NFRs | 4 | NFR-1 cross-platform, NFR-3 spawn-time, NFR-4 failure-honesty, NFR-5 no-new-deps |
| Integrations | 0 | (OS APIs are not counted) |
| MUCs | 2 | MUC-1 shell-injection, MUC-2 env-leak |
| Cross-cutting policies | 0 | |
| Hard data constraints | 0 | |
| **Total ASR** | **6** | |

## Tier

- sFPC-tier: S (2 < 8 threshold)
- ASR-tier: S (6 < 8 threshold)
- Multi-bounded-context: no
- **Tier (max): S** — target TDD ~100–200 lines, target ADRs 1–2

## Pillar coverage

| Pillar | Coverage | Notes |
|---|---|---|
| Form | gap-filled | Need public API + module placement (small surface) |
| Armor | gap-filled | Shell-injection + env-leak guards per MUC-1/MUC-2 |
| Proof | gap-filled | Mock-test cross-platform dispatch; manual smoke-test actual spawn |

## User decision

Accepted tier-S as computed. No override.

## Authoritative sources referenced

(None — no context index for this project; no pre-existing standards or ADRs apply directly. Port draws from `plugins/sulis/references/boring-code.md` + Python stdlib conventions implicitly.)
