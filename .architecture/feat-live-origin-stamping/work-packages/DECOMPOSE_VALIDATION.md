# Decompose Validation — feat: live-origin-stamping (CH-01KTHP)

## Atomicity (each WP implementable without reading another)

| WP | Self-contained? | Note |
|----|-----------------|------|
| WP-001 | Yes | Type widen + contract scaffolding; references ADR-017 only |
| WP-002 | Yes | Forwards arg pinned by WP-001 (the dep carries the contract) |
| WP-003 | Yes | Pure helper; contract + fixtures in the WP |
| WP-004 | Yes | Joins WP-002 + WP-003 surfaces, both named in deps |
| WP-005 | Yes | Python; reuses #216 constructors; contract in the WP |
| WP-006 | Yes | Conformance test + live evidence checklist self-contained |

## Dependency graph is acyclic and minimal

- WP-001 → {WP-002, WP-003} → WP-004 ; WP-005 independent ; {WP-004, WP-005} → WP-006.
- No bundling: 6 WPs, one coherent unit each (contract / bridge-forward /
  relay-helper / relay-wire / executor-export / verify). Each maps to one file or
  one coherent seam per the TDD §5 inventory.

## Cross-kind (WP-08.5) check

- Contract WP first: **WP-001** pins the producer/consumer signature (ADR-017).
- TS track (WP-002/003/004) and Python track (WP-005) proceed independently after
  the contract — they share only #216's env-var grammar (already merged).
- Final integration/live-verification WP last: **WP-006** (grammar conformance in
  CI + live round-trip on the founder machine).

## kind correctness

- WP-001..005 are `backend` (TS server seam + Python executor); WP-006 is
  `integration` (cross-language conformance + live observation). Verified against the
  per-kind adapter table (TDD §Verification Plan item 5).

## Frontmatter completeness

- Every WP carries `change_id: 01KTHP2NYQ1A3WHPJD75VP31NT`, `kind`, `primitive`,
  `group`, `dependsOn`, `estimated_token_cost`, and a `verification:` block
  (concrete shape for WP-001..005; WP-006 carries the deferred live-round-trip plus a
  concrete conformance artifact).

## Standards alignment

- **CONTRACT_FIRST** — WP-001 pins the signature before consumers (WP-002/003/004).
- **Red-Green-Blue** — every WP has all three sub-checklists; Blue re-asserts the
  read-only gate on every TS WP.
- **Boring code / no magic** — explicit types, no `any` on the origin path; reuse of
  #216 primitives instead of re-implementation.
- **MEA-09** — bridge tests use the stubbed child / recorded streams, not mocks; the
  live round-trip uses the real `claude`.

## Acceptance traceability (SPEC → WP)

| SPEC acceptance | WP |
|---|---|
| Executor commit carries `autonomous; run=…`; cockpit shows exact | WP-005, WP-006 |
| Chat commit carries `assisted; conversation=…; turn=…`; cockpit shows exact | WP-003, WP-004, WP-006 |
| Two conversations → different conversation ids; turn increments | WP-003, WP-006 |
| Stamp failure non-fatal → degrade to inferred | WP-004, WP-005, WP-006 |
| CI green + live round-trip observed | WP-001..005 (CI), WP-006 (live) |
