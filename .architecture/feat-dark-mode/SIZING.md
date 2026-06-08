# SIZING — feat-dark-mode (Dark mode for the cockpit)

> Computed: 2026-06-07 · Source: spec `.changes/feat-dark-mode.SPEC.md` + codebase recon
> Mode: brownfield feature (new theming layer over existing cockpit client)

## sFPC (simplified Function Point Count)

| Element | Count | Notes |
|---|---|---|
| ILF (internal data stores) | 1 | persisted theme choice in `localStorage` (one key) |
| EIF (external integrations) | 0 | Monaco is a bundled library, not an external service |
| EI (mutating ops) | 2 | toggle theme; persist choice |
| EO (deriving ops) | 1 | resolve effective theme (saved ?? OS) |
| EQ (retrieving ops) | 2 | read OS `prefers-color-scheme`; read persisted choice |
| **sFPC** | **6** | → tier **S** (≤10) |

## ASR count (architecturally-significant requirements)

| ASR | Source |
|---|---|
| Theme-selector mechanism (CSS vars overridden under root selector) | spec Constraints |
| Persistence ordering (saved choice > OS default) | spec Constraints |
| Monaco theme binds to active app theme | spec Scope |
| WCAG AA contrast across all surfaces (dark set) | spec Acceptance ("readable") |
| No-regression: full-height layout + existing tests | spec Constraints |
| Hardcoded-colour remediation (32 non-token colour sites) | **audit finding** — see TDD §Audit |
| **ASR count** | **6** → tier **S** (≤5) / low-**M** (6-15) |

**Tier decision: S.** sFPC=6 (S) and ASR=6 (boundary S/M). Take the lower:
the work is one theming layer plus a bounded remediation list, not multiple
bounded contexts. The single material complexity is the audit finding, which
is a known, enumerated 32-site list — not open-ended.

## Per-pillar addressable scope

No `.context/{project}/INDEX.md` exists for this change worktree → no
authoritative sources to reference. All three pillars get full tier-S
sections (short, because tier S).

| Pillar | Coverage | Treatment |
|---|---|---|
| Form | uncovered | full tier-S section |
| Armor | n/a (no external calls, no secrets, client-only) | 1-paragraph "not applicable, here's why" |
| Proof | uncovered | full tier-S section |

## Targets (tier S)

- TDD length target: ~150-250 lines. Circuit breaker at 1.5× (~375).
- ADR maximum: 3. Producing **2** (theme mechanism; Monaco binding). The
  hardcoded-colour remediation is a finding folded into the TDD + WP stub,
  not an ADR (it's not a rejected-alternative decision).

## Notes

- Audit finding materially changes the spec's premise. Spec says "every
  component reads from tokens"; recon repeated it. Code says otherwise: 32
  raw colour literals across 8 files. Surfaced in TDD §Audit + as a WP stub.
