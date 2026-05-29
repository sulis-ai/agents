# Code Review: WP-002 — UI-contract renderer (reuses design-system VIEWER)

> **Timestamp:** 2026-05-29T150501Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-ui-contract-renderer → change/feat-cockpit-contract-preview
> **Files changed:** 5 (4 new + README.md doc line)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small, self-contained step that turns a change's design
tokens into a visual preview page (`UI.html`), reusing the existing
design-system viewer rather than building a new previewer. When a change has
no visual side (a behind-the-scenes change), it cleanly records "no UI
contract for this change" and writes nothing, so the cockpit never shows a
broken link. The build is clean, the change is tightly scoped, and it ships
with sixteen tests covering the present case, the no-contract case, generic
discovery, path safety, and a hardening test for a malformed contract file.

Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One small thing was tightened during review (already applied): a design-token
value is now neutralised before it's placed into the preview page's style
block, so a malformed or hostile token file can't break out of the styling and
inject content. This is belt-and-suspenders — the values come from the
change's own trusted design files — but it costs nothing and is now covered by
a test.

## How this change is shaped

**Size — clean.** ~650 lines across 5 files, single concern (one new step +
its tests + one doc line). Well within a reviewable size.

**Scope — clean.** One Conventional Commit type (`feat`), one module area
(`plugins/sulis/scripts/`). No mixed refactor-plus-feature.

**Safety — clean.** No migrations, no schema/IDL changes, no infra files, no
secrets. No network on the hot path; file I/O only, confined to the change's
own worktree.

**Completeness — clean.** 4 new source/test files; the two new source files
(`_render_ui.py`, `wpx-render-ui`) are both covered by tests (16 tests; 94%
line coverage on the module).

---

## Technical detail

> Internal taxonomy below for engineers + downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low) — resolved inline
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the one low finding was fixed inline, not deferred)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — hexagonal shape clean (pure logic in `_render_ui.py`, CLI thin delegate) |
| Security | 1 (low, fixed) | 0 | `</style>` breakout in inlined token value — defanged inline (`_css_value_safe`) |
| Quality | 0 | 0 | None — 16 tests, 94% coverage, no dead surface, no CR-10 anti-patterns |

### Build Verification (CR-01)

Clean. `ruff check` on all 4 changed files: "All checks passed!". `mypy
--ignore-missing-imports _render_ui.py`: "Success: no issues found". `python3
-m py_compile`: OK. 16/16 tests pass. Tool outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts)
  severity: none

Size (PH-02):
  lines_added: ~650, files_changed: 5
  severity: none (within reviewable band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (both source files covered)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/_render_ui.py` (build_viewer_html) — low (security), RESOLVED INLINE

**What:** token `value` strings were inlined into the VIEWER's `<style>`
block. The token regex `(--[A-Za-z0-9_-]+)\s*:\s*([^;}\n]+)` already stops a
value at `;`, `}`, or newline (so no new-declaration / block-close injection is
possible), but a literal `</style>` substring inside a value could
theoretically escape the style element.

**Why it matters (bounded):** token values originate from the change's own
trusted design-token files, and the output is a local `file://` preview, not a
served page — so real exposure is negligible. Defence-in-depth only.

**Resolution (inline):** added `_css_value_safe(value)` which replaces `<`
with the CSS hex-escape `\3c `, neutralising any `</style>` while leaving
legitimate CSS values (which contain no `<`) byte-identical. Pinned by
`test_inlined_token_values_cannot_break_out_of_style_block`. Re-ran lint +
mypy + tests: all green. No Hardening Delta queued (fixed, not deferred).

### Findings in the Neighbours

None. The change is additive (new files); the only edit to existing code is a
documentation addition to `README.md`. No behavioural neighbour exposure.

### Watch List

- A future shared `manifest.json` read/write helper may be worth extracting
  once WP-001's data-contract renderer lands and a second consumer of the
  manifest exists (2-consumer threshold). Deferred to WP-003 integration; not
  a gap in this WP. No delta.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (4 files), `mypy`
  (`_render_ui.py`), `py_compile` (both modules). Base vs head: no
  PR-introduced errors. Coverage gap: `ruff format` deliberately not gated —
  existing sibling scripts (`_wpxlib.py`, `wpx-worktree`) don't conform to it
  either; the repo's gate is `ruff check` (CP-01 convention-match).
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Justified by diff size +
  cohesion: ~650 lines but a single new module + CLI + its own tests, all
  authored this session and read end-to-end. Executor self-review gate, not a
  multi-author PR.
- [✓] **CR-03 Full-file reads.** All 4 changed source/test files read
  end-to-end (each <300 lines).
- [✓] **CR-04 Evidence discipline.** The one finding cites file + function +
  the exact regex/behaviour.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low
  (resolved inline).
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade triggers fired
  (Build Verification empty; no unread files; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (hexagonal
  boundary clean; reuse per ADR-001/EP-03; generic resolution per ADR-003;
  no network; writes confined to worktree root). Security: 1 low finding
  (style breakout), resolved inline; no secrets, no injection, no shell-out
  (grep-verified), no traversal write. Quality: 16 tests + present/absent/
  generic/path-safety/manifest-merge coverage; no dead surface; CR-10 — no
  N+1 / I/O-in-loop / O(N²) patterns (grep-verified).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none.
  PH-03 Safety: none. PH-04 Completeness: none. No PH-03 high → no CR-06
  auto-downgrade.

#### Run details

- **Diff source:** working tree vs `origin/change/feat-cockpit-contract-preview`
  (new files untracked at review time).
- **Neighbour expansion:** git grep; additive change, no symbol callers
  affected (new module).
- **Scanners run:** ruff, mypy, py_compile, pytest.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked — diff carries
  no secrets, no dependencies, no Dockerfile (grep-verified clean).
- **Lenses dispatched in parallel:** no — single-reader per CR-02 carve-out.
