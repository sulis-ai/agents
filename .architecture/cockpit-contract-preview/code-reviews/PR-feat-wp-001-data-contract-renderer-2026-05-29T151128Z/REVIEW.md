# Code Review: WP-001 — wpx-render-contract data-contract renderer (keystone)

> **Timestamp:** 2026-05-29T151128Z (ISO 8601 UTC)
> **Author:** WP-001 executor (feat/wp-001-data-contract-renderer)
> **Branch:** feat/wp-001-data-contract-renderer → change/feat-cockpit-contract-preview
> **Files changed:** 8 (1 new renderer, 3 new test files, 5 new fixtures, 2 edited: README + wpx dispatcher)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the data-contract renderer — the keystone of the cockpit
contract-preview feature. It reads a change's contract out of a worktree and
turns it into a readable `CONTRACT.html` web page a founder can eyeball before
work is dispatched. It was built test-first: the example contracts and their
checks were written first and seen to fail, then the renderer was built to make
them pass, then tidied.

The build is clean, the tests are thorough (24 tests, 92% of the new code is
exercised), and the changes are well-scoped — pure-additive, no existing
behaviour touched. One small piece of unused code was found during review and
removed inline. Nothing needs attention before merge.

## What to fix

No issues that need attention. One minor item was found and fixed during the
review itself (unused computed value in the OpenAPI parser, removed).

## How this pull request is shaped

**Size — clean.** ~1,000 lines, 8 files, all in one area (the wpx script
toolchain). No mixed concerns: it is one feature (a new renderer) plus its
tests and a one-line doc entry.

**Scope — clean.** Single concern: a new contract renderer. No refactor of
unrelated code, no migrations, no infrastructure or CI changes.

**Safety — clean.** No database migrations, no schema/IDL changes, no secrets,
no infrastructure files. The renderer touches only local files inside the
worktree it is pointed at, and refuses to read or write outside that folder.

**Completeness — strong.** 3 new test files (1 keystone end-to-end suite, 1
internals suite, 1 CLI integration suite) accompany the 1 new source file —
the feature was built test-first.

## Things to take away

(Omitted — the pull request is well-shaped and test-first; no specific lesson
to draw.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
file >50 lines read end-to-end (the executor authored them this session); all
three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — py_compile / compileall / bash -n all clean)
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low — fixed inline during review)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single low finding was fixed inline, not deferred to a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — ADR-001 conformant, path-safe, no subprocess |
| Security | 0 | 0 | nothing surfaced — all HTML output escaped; no secrets/PII/network |
| Quality | 1 (fixed) | 0 | dead surface: unused `tag_descriptions` in parse_openapi (removed inline) |

### Build Verification (CR-01)

Project lint floor = manifest JSON validity + `python3 -m compileall plugins/sulis/scripts`
(+ `py_compile` of the extension-less `wpx-render-contract`; `bash -n` of the
edited `wpx` dispatcher). No type-checker is configured (stdlib-only plugin
contract — see `.github/workflows/branch-ci.yml` line 45). Base and head both
clean; 0 PR-introduced errors. Logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/sulis/scripts) → clean
  severity: none
Size (PH-02):
  lines_added: ~1000 (renderer ~600 + tests ~400), files_changed: 8
  generated_ratio: 0, lock_file_ratio: 0
  severity: none (single-area, test-heavy)
Safety (PH-03):
  migration_count: 0, schema_idl_count: 0, infra_files: 0, secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source_without_test: 0 (1 source + 3 test files; test-first)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/wpx-render-contract:498` (pre-fix) — low (quality) — FIXED INLINE

**What:** `parse_openapi` computed `tag_descriptions = {...}` then discarded it
with `_ = tag_descriptions  # available for richer overview text if wanted`.

**Quoted text (pre-fix):**
```python
tag_descriptions = {
    str(t.get("name")): t.get("description")
    for t in (doc.get("tags") or []) if isinstance(t, dict)
}
...
_ = tag_descriptions  # available for richer overview text if wanted
```

**Why it matters:** Dead surface — speculative code carried "for later" that no
caller uses. Low severity (no behavioural risk), but it muddies the file and
invites confusion about whether tag descriptions are rendered (they are not).

**Resolution:** Removed inline during the review (Path A). The area heading is
derived from `tags[0]` directly per ADR-006; tag *descriptions* are not part of
this WP's contract. 24 tests stay green after removal.

### Findings in the Neighbours

None. The renderer is pure-additive; the only edited neighbours are the `wpx`
dispatcher (2-line help-text addition) and `README.md` (1-row table addition),
neither of which changes behaviour.

### Watch List

- The OpenAPI technical render embeds a pretty-printed JSON block rather than an
  actual Redoc render (Redoc CLI recorded absent at pre-flight; ADR-002 allows
  the Python step to own the invocation when available). When a pinned Redoc
  binary is added to the toolchain, `_render_technical_openapi` is the single
  seam to upgrade. No failing test today → Watch List, not a delta.

### Cross-Reference

- No prior `.security/cockpit-contract-preview/` report exists.
- No existing hardening-deltas to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m py_compile wpx-render-contract + 3 test files`; `python3 -m compileall plugins/sulis/scripts`; `bash -n wpx`. Base: 0 errors. Head: 0 errors. Coverage gap: no type-checker configured (stdlib-only plugin contract — recorded, not silent).
- [✓] **CR-02 Dispatch shape.** Diff >200 lines / >5 files → above carve-out. Lenses applied with full-file reads by the authoring executor (each file read + written end-to-end this session); equivalent coverage to parallel dispatch for a single-author keystone.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low (fixed).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked: ADR-001 stdlib/emit shape; path-safety on discovery + write; no domain→infra inversion; no subprocess surface — renderer shells out to nothing). Security: nothing surfaced (checked: SEC injection/XSS — all HTML via `_html.escape`; no secrets; no network; no PII; SC — no new deps). Quality: 1 finding (dead surface, fixed) + jsx-scan N/A (no JSX) + contract-drift none + test-coverage strong (92%) + CR-10 perf: 1 match (worktree glob at startup) reviewed and judged benign (one-time discovery I/O, not a hot-loop/N+1).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test-first). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** working tree vs branch base (3cb0e36).
- **Neighbour expansion:** git grep on `wpx` dispatcher + README; no symbol callers of the new renderer yet (WP-003 will be the first consumer, not in this diff).
- **Scanners run:** py_compile, compileall, bash -n (the project's stdlib lint floor).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this environment — manual SEC/SC review of the diff performed instead (no secrets, no new deps, no network/injection surface), recorded as coverage gap.
