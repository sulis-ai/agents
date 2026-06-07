# Work Packages — Files diffs · Provenance · Change origin

> **Feature set of:** CH-01KT50 · `create-autonomous-delivery-environment`
> **Parent plan:** `../../../work-packages/INDEX.md` (the 11-slice change plan)
> **Decomposition:** CONTRACT-FIRST per seam (contract WP → parallel
> backend+frontend → integrate), on top of the change's vertical-slice shape.
> Each WP is atomic and carries the Red/Green/Blue cycle.
> **TDD:** `../TDD.md` · **ADRs:** `../adrs/ADR-010..015`

## The two slices (defer the third)

- **Slice 1 — Files diffs-in-tree + Provenance view.** Founder-observable:
  see how much changed per file/folder; get the trust digest + run-log +
  coverage-map.
- **Slice 2 — Change origin.** Founder-observable: a worded
  Autonomous/Assisted·likely/Origin-unknown badge that traces to a run or a
  conversation; origin recorded exactly going forward.
- **Slice 3 — Origin mode-timeline (DEFERRED).** The "story" view
  (`origin-mode-timeline.html`), post-stamping. Not decomposed here.

## Shape — 14 WPs (1 gate-green foundation · 7 Slice-1 · 6 Slice-2)

| WP | Title (plain English) | Kind | Slice | dependsOn | Est | Live hop? |
|---|---|---|---|---|---|---|
| **WP-P00** | Make the safety check green again (reconcile the read-only gate) | backend + gate | 0 | — | 4h | none |
| **WP-P01** | Agree the data shapes for diffs + provenance (contract) | contract | 1 | P00 | 3h | none |
| **WP-P02** | Count what changed in each file (backend) | backend | 1 | P01 | 3h | none |
| **WP-P03** | Show "+N −N" on files and folders (frontend) | frontend | 1 | P01 | 3h | none |
| **WP-P04** | Wire up the change-counts end to end | integration | 1 | P02, P03 | 1h | none |
| **WP-P05** | Build the Provenance read: digest, run-log, coverage (backend) | backend | 1 | P01 | 6h | none |
| **WP-P06** | Build the Provenance screens: dashboard → run-log → coverage-map (frontend) | frontend | 1 | P01 | 9h | none |
| **WP-P07** | Wire up Provenance end to end + retire the old Brain view | integration | 1 | P05, P06 | 2h | none |
| **WP-P08** | Agree the change-origin shapes + the origin seam (contract) | contract | 2 | P01 | 3h | none |
| **WP-P09** | Work out each file's likely origin (backend, inferred) | backend | 2 | P08 | 6h | none |
| **WP-P10** | Show the origin badge, panel + "how it came to be" lens (frontend) | frontend | 2 | P08 | 7h | none |
| **WP-P11** | Wire up change origin end to end | integration | 2 | P09, P10 | 2h | none |
| **WP-P12** | Record origin exactly at commit time (executor + chat write paths) | backend (write side) | 2 | P08 | 5h | **founder-machine: real executor/relay commit** |
| **WP-P13** | Read the recorded origin (exact, replaces inferred) | backend | 2 | P12 | 3h | none |

**Total: 14 WPs · ~57h.**

## Why WP-P00 is first (and blocks everything)

The read-only safety check is **currently failing** on this branch — four
flagged spots (the Advanced view's two actions + its stop-a-process signal, and
the chat-summary cache + its summariser). Nothing in this set can ship green on
top of a failing safety check, so the first job is to **reconcile it** (keep the
check, add named + audited exceptions per ADR-015) and fold in the pending
test-harness fix (the chat/skeleton/inventory tests need the shared data
provider). After WP-P00 the safety check is green and the suite passes; every
later WP builds on a clean base.

## Critical path

```
WP-P00  (gate green)
  └─ WP-P01  (contract: diffs + provenance shapes)
       ├─ WP-P02 ─┐                      (files: backend ∥ frontend)
       ├─ WP-P03 ─┴─ WP-P04             → files diffs OBSERVED
       ├─ WP-P05 ─┐                      (provenance: backend ∥ frontend)
       └─ WP-P06 ─┴─ WP-P07             → provenance OBSERVED  ── end of Slice 1
                          │
            WP-P08  (contract: origin seam)  ◀── P01
              ├─ WP-P09 ─┐               (origin: backend ∥ frontend)
              ├─ WP-P10 ─┴─ WP-P11      → origin OBSERVED (inferred)
              ├─ WP-P12  (stamping, write side)
              └─ WP-P13  (recorded adapter) ◀── P12   → inferred flips to exact
```

**Longest path:** P00 → P01 → P05 → P06 → P07 (Slice 1 provenance) ≈ 24h, then
P08 → P12 → P13 (Slice 2 to exact origin) ≈ 11h. **Critical path ≈ 35h**; the
parallel backend/frontend pairs (P02∥P03, P05∥P06, P09∥P10) collapse wall-clock
when two executors run.

## Suggested execution waves

| Wave | WPs | Why |
|---|---|---|
| 0 | **WP-P00** | Green the safety check + suite — unblocks everything |
| 1 | **WP-P01** | The Slice-1 contract; unblocks the parallel pairs |
| 2 | WP-P02 ∥ WP-P03 → **WP-P04** | Files diffs — thinnest observable round-trip; proves the pattern |
| 3 | WP-P05 ∥ WP-P06 → **WP-P07** | Provenance — the trust headline; retire the old Brain view |
| 4 | **WP-P08** | The Slice-2 origin contract |
| 5 | WP-P09 ∥ WP-P10 → **WP-P11** | Origin (inferred) — observable badge + trace |
| 6 | **WP-P12** → **WP-P13** | Stamping (write side) → recorded adapter; inferred flips to exact |

Slice 1 (P00–P07) is fully observable locally with no live hop. Slice 2's
inferred path (P09–P11) is fully local; only **WP-P12** has a founder-machine
hop (a real executor/relay commit to prove the stamp lands).

## Contract-first seams (CF-05)

| Seam | Contract WP | Parallel producer | Parallel consumer | Integrate |
|---|---|---|---|---|
| Files diff counts | WP-P01 | WP-P02 (numstat) | WP-P03 (rows+rollup) | WP-P04 |
| Provenance projection | WP-P01 | WP-P05 (read+edges) | WP-P06 (3 screens) | WP-P07 |
| Change origin | WP-P08 | WP-P09 (inferred) / WP-P12 (stamp) / WP-P13 (recorded) | WP-P10 (badge+panel+lens) | WP-P11 |

## Deferred infrastructure needs (each ships WITH its slice)

| Fixture | Needed by |
|---|---|
| `seed-brain-entities-fixture` (incl. ≥1 real `lifecyclerun` with `_gaps`/`_self_critique`) | WP-P05 (provenance) — deferred upstream by the parent change |
| `recording-origin-correlation-fixture` (commits + runs + turns, known-true origins) | WP-P09 (inferred origin) |
| `fixture-stampable-commit` | WP-P12 (stamping) |
| `fixture-stamped-commits` (commits with `Sulis-Origin:` trailers) | WP-P13 (recorded adapter) |

## Founder calls baked in (confirm at review — see TDD §10)

- **Origin-stamping mechanism** (ADR-013): commit **trailer** recommended;
  sidecar-only is the conservative alternative. Drives WP-P12.
- **Read-only gate stance** (ADR-015): **keep-with-named-exception** recommended;
  remove "stop a process" is the conservative alternative. Drives WP-P00.

## Status legend

`pending` ready · `done` merged · `blocked` waiting on a dep.
