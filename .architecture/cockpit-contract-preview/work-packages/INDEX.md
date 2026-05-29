# Work Packages — cockpit-contract-preview

> Change: CH-01KSSV · feat · `01KSSV19SFWBJM01BM2XP6CZZ0` · closes #85
> Source: `.architecture/cockpit-contract-preview/TDD.md` (tier M) + ADR-001..006
> Derived index — never hand-edit. Regenerate from the WP files on any change.

5 Work Packages. WP-001 is the keystone (test-first). WP-005 is the visual
contract and is already **done** (founder signed off the rendered mockup,
2026-05-29). Three WPs (WP-001, WP-002, WP-004) are ready to start now and can
run in parallel; WP-003 integrates them last.

## Work Packages

| ID | Title | Primitive | Status | Depends On | Blocks |
|----|-------|-----------|--------|------------|--------|
| WP-001 | wpx-render-contract — data-contract renderer (keystone, test-first) | Create | done | WP-005 | WP-003 |
| WP-002 | UI-contract renderer (reuses design-system VIEWER) | Create | done | — | WP-003 |
| WP-004 | recreate-on-demand for shipped changes (composes `sulis-change recreate`) | Compose | done | — | WP-003 |
| WP-003 | cockpit wiring: per-change links + review-gate + on-demand | Create | done | WP-001, WP-002, WP-004, WP-005 | — |
| WP-005 | visual contract: CONTRACT.html full-picture default view (signed off 2026-05-29) | Create | done | — | WP-001, WP-003 |

> **`kind` is recorded per WP file, not as a table column** (a `kind` column
> aliases to Primitive and silently wins first-match — issue #60). For
> reference: WP-001/002/004 are `backend`, WP-003 is `frontend`, WP-005 is
> `contract` (visual). The Primitive column above carries the SEA change
> primitive from each WP file's `primitive:` frontmatter.

**Ready now (deps satisfied):** WP-001, WP-002, WP-004 — run in parallel.
WP-001's only dependency (WP-005) is done; WP-002 and WP-004 have none.
WP-003 stays dependency-not-ready (stored status `pending`) until WP-001,
WP-002, and WP-004 merge.

---

## Dependency graph

```
WP-005 (visual contract, DONE/signed-off)
   │
   └──► WP-001 (data-contract renderer — KEYSTONE) ─┐
                                                     │
        WP-002 (UI-contract renderer) ──────────────┤
                                                     ├──► WP-003 (cockpit wiring)
        WP-004 (recreate-on-demand) ────────────────┘        + visual_contract: WP-005

   WP-001, WP-002, WP-004 are mutually independent → run in parallel.
   WP-003 integrates last (depends on all three; declares the WP-005 visual contract).
```

## Build order (TDD + blueprint)

1. **WP-005** — visual contract (DONE — founder signed off). Unblocks the
   default-view layout WP-001 must produce and WP-003 declares against.
2. **WP-001 / WP-002 / WP-004** — parallel. WP-001 is the keystone: write the
   two ServiceSpec fixtures + the OpenAPI-fallback fixture and their assertions
   first (the keystone Red), see them fail, then build the renderer.
3. **WP-003** — last. Serves the WP-001/002 artifacts, uses WP-004 recreate,
   renders at the pre-dispatch review gate + on demand.

## Contract-first note (WP-08.5 / CONTRACT_FIRST)

The cross-kind seam is **Python steps (WP-001/002, producer) → Node cockpit
server (WP-003, consumer)**, meeting at the **rendered artifact files + the
manifest** in the worktree. WP-003 consumes the manifest (data_contract +
`ui_contract: present|none`) and serves files — it never parses contracts itself
(read-only cockpit, ADR-001). WP-003 builds against a manifest fixture (the
contract mock) so it can proceed in parallel with the producers (CF-05). The
**visual** contract for the user-facing CONTRACT.html surface is WP-005
(`kind: contract`, `contract_type: visual`, signed off); WP-003 declares
`visual_contract: WP-005` (WPF-11 / WP-08.5).

## Release acceptance — anti-hard-wiring gate (MUST · ADR-003 / TDD §4.4)

Before release: **open the cockpit, walk EVERY in-flight change, and confirm each
surfaces its OWN data + UI contracts.** This is an explicit release-acceptance
step (carried in WP-003), not a single-change smoke test — it is the trust
property of the whole feature and the proof that per-change resolution is generic.

## Out of scope (recorded)

- **Events** — the ServiceSpec contract does not carry domain events; rendering
  them would break the no-drift guarantee. Excluded pending a contract-format
  extension tracked in ADR-005. The contract-native approximation
  ("what each action changes" / `stateEffects`) is in the default view.
