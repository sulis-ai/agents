---
spec: auto-back-merge-on-release
generated_at: 2026-06-02
tier_computed: M
tier_confirmed: M
tier_basis: |
  Functional complexity (sFPC) lands in the lower-M band; ASR count is at the
  S/M boundary. Take the higher tier (M) per the right-sizing rule because the
  reusable-workflow move + the dual-skill drift gate are architecturally
  significant despite the small surface.
---

# SIZING — auto-back-merge-on-release

## sFPC (simplified Function Point Count)

| Element | Count | Source |
|---|---|---|
| **ILF** (internal logical files / persistent data) | 2 | (a) the `dev-sha-at-open` pin embedded in release PR bodies; (b) the `back-integrate`-labelled PR as a persistent state marker. Neither is a database row — both are git/GitHub-native records. |
| **EIF** (external interface files) | 2 | (a) GitHub Actions runtime; (b) GitHub REST API (commits→pulls lookup, PR list + create). |
| **EI** (external inputs — state-mutating ops) | 4 | (1) write pin into release PR body (release-train), (2) fast-forward push `main:dev`, (3) open back-merge PR, (4) enable auto-merge on the PR. |
| **EO** (external outputs — derivations) | 2 | (1) post-condition check `dev == main OR back-integrate PR open`; (2) drift refusal message (composes "back-merge PR open at #N" vs "manual recovery"). |
| **EQ** (external queries — pure reads) | 4 | (1) `gh api .../commits/{SHA}/pulls`, (2) regex-extract pin from PR body, (3) `git ls-remote origin dev`, (4) `git merge-base --is-ancestor origin/main origin/dev` (drift gate). |
| **sFPC total** | **14** | Lower-M band (11–30). |

## ASR count (architecturally significant requirements)

| Source | Count | Items |
|---|---|---|
| NFRs | 8 | NFR-001 (pin), NFR-002 (no force-push), NFR-003 (back-compat), NFR-004 (visibility), NFR-005 (opt-out), NFR-006 (atomicity), NFR-007 (fast/deterministic drift check), NFR-008 (SemVer pin default). |
| Integrations | 2 | GitHub Actions, GitHub REST API. |
| MUCs | 7 | MUC-001..MUC-007 (each carries a load-bearing system response). |
| Cross-cutting policies | 1 | GIT-12 rule (must compose with GIT-05, GIT-06, GIT-09). |
| **ASR total** | **18** | M band (16–40). |

## Tier resolution

| Axis | Band | Result |
|---|---|---|
| sFPC = 14 | 11–30 → M | M |
| ASR = 18 | 16–40 → M | M |
| Bounded contexts | 1 (release pipeline) | not XL |
| **Resolved tier** | | **M** |

**Confirmed:** M. The TDD target length is ~400–700 lines; ADR count expected
2–6. Pre-write announcement: tier M, sFPC 14, ASR 18, per-pillar coverage
below.

## Per-pillar addressable scope

| Pillar | Existing coverage | This change adds |
|---|---|---|
| **Form** | High. The current `.github/workflows/release-on-merge.yml` is the only release artifact; module boundaries between skills and workflows are already established. | A new module boundary: the **reusable workflow lives in the plugin**, called by a thin shim in the consumer. Net-new structural component, addressed in full in the TDD's Form section. |
| **Armor** | Medium. Existing concurrency group + version-drift guard are present; no-force-push is a current invariant (informally). | Promotes no-force-push to invariant **enforced by post-condition check**. Adds explicit fast-forward fallback to PR. Adds defensive drift gate in two skills. Addressed in full in Armor. |
| **Proof** | Low. There is no test for the existing release-on-merge.yml beyond shipping it and observing. | Adds clean-path + raced-path regression tests + chaos test for race simulation + drift-check unit tests. Addressed in full in Proof. |

No authoritative architecture documentation (`.context/auto-back-merge-on-release/`)
exists for this change, so no "reference don't restate" reductions apply. All
three pillars are addressed top-to-bottom.

## File-count sanity check

The marketplace has ~150 plugin source files and ~80 skills. This change
touches **6 files**: one workflow, one new template, one new shim, two skill
SKILL.md files, one standards doc. The mismatch between sFPC (14) and file
count (6) is expected — sFPC counts logical operations, not files. The diff
is small but architecturally significant.

## Circuit breakers

None tripped at planning time. Tier-M target length is ~400–700; the TDD
sits inside that band.

## Notes

- ILF/EIF assignment is unusual: GitHub PR bodies aren't a database, but
  they store the only piece of state that distinguishes clean-vs-raced.
  Counting them as ILF reflects their role rather than their substrate.
- MUC-001 (force-push race) is the load-bearing MUC; the entire design
  exists to satisfy its System Response (REQUIRED).
