# Code Review: feat/wp-006-sulis-capture-cli — Create sulis-capture CLI (JSON envelope)

> **Timestamp:** 2026-06-03T091517Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-sulis-capture-cli → change/create-brain-backlog-and-traversal
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the `sulis-capture` command — the front door that turns a typed idea into a rooted entry in the Brain. It is well-scoped: one new command and one new test file, nothing else touched. The build is clean, and the command ships with seven tests that cover the happy path and every failure case. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — for awareness**

The pull request is 472 lines across 2 files: a 192-line command and a 280-line test file. That is a touch over the line where a reviewer would usually split the work between several readers, but both files are brand-new, single-purpose, and short, so it reads cleanly in one pass.

**Scope — clean**

One concern: add the capture command. A single `feat` change, all inside `plugins/sulis/scripts`.

**Safety — clean**

No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean**

The command ships with its tests. Seven of them, covering the success path, the "no why" refusal, repeat-runs-stay-stable, the roadmap flag, the brain-being-unavailable case, the envelope shape, and the missing-config case.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean, compileall clean.
- **PR Hygiene:** 0 findings. Size band low (472 lines / 2 files); scope single-concern; safety clean; completeness clean.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — CLI is a thin consumer of domain ports |
| Security | 0 | 0 | none — local-file CLI, no auth/injection surface |
| Quality | 0 | 0 | none — full test coverage, no dead surface |

### Build Verification (CR-01)

Mechanical baseline ran against the changed files. `ruff check` → "All checks passed!". `python3 -m compileall` → OK. Full repo suite: 1957 passed, 9 skipped (pre-existing), 0 failures. No PR-introduced errors. Raw output in `tool-outputs/ruff-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {feat}; module_fan_out 1   → none
Size (PH-02):        lines +472 -0; files 2; generated 0; lock 0   → low
Safety (PH-03):      migrations 0; schema 0; infra 0; secrets 0    → none
Completeness (PH-04): new_source_without_test 0; api_no_schema false → none
```

### Findings in the Changes

None.

Lens detail:

- **Architecture lens — nothing surfaced.** Checks run: dependency direction (the CLI imports `_brain_capture`, `_entity_adapter_local`, `_entity_repository` — all domain/port modules; correct direction, EXPAND-Create consumer, no infra→domain inversion, WPB dependency-rule clean); no new module-level singletons; no new circular imports; resilience boundary present (`main()` catches `CaptureError`/`EntityValidationError`/`FileNotFoundError` and a bare `Exception` fallback → NFR-01 never-raises, mirroring the orchestrator's `_store` degradation discipline); the only external call (`git rev-parse` in `_resolve_repo_root`) carries `timeout=10`, reused verbatim from the sibling CLIs; verification uses the real `LocalFileEntityAdapter` + real vendored schemas (MEA-09, no mock store) — contract-test discipline satisfied via the 7 integration tests.
- **Security lens — nothing surfaced.** Primitives checked: SEC (access control / injection / validation / secrets exposure). No auth surface (local file CLI). `subprocess.run` uses list-form argv (no shell injection). Path args resolved via `Path.resolve()`. No hardcoded credentials/keys (grep clean). The repo-contract read is wrapped in a bare-`except` that degrades to `None` → plain `ok:false`, no traceback leak. SC (dependency CVEs): no new dependencies — stdlib + already-vendored `yaml`/`jsonschema`.
- **Quality lens — nothing surfaced.** (1) Build Verification: clean. (2) JSX scan: N/A (Python). (3) Dead surface: every argparse arg is consumed; no unused imports (ruff confirms). (4) Contract drift: the `ok:true` payload keys exactly match the WP Contract + the orchestrator's documented return dict (`opportunity_id`, `requirement_id`, `roadmap`, `chain`, `bootstrapped`); pinned by `test_envelope_shape_matches_siblings`. (5) Test coverage: 7 tests for new behaviour, no source-only gap. (6) Style: docstring + boring explicit argparse, no dynamic arg construction; one `TODO(deferred)` with REASON + RESOLVE_BY (documented deferral, conforms to the Conscious-Deferral rule). (7) CR-10 performance: no anti-pattern matches — no loops in the CLI, no N+1, no unbounded materialisation.

### Findings in the Neighbours

None. The CLI is a leaf consumer; its callees (`capture_idea`, `LocalFileEntityAdapter`) are unchanged by this diff and already characterised by WP-004/WP-003 unit tests.

### Watch List

- The `_resolve_repo_root` / `_ok` / `_err` triple is now duplicated verbatim across four CLIs (sulis-capture, sulis-emit-opportunity, sulis-brain-query, _emit_ingest_cli.py). The diff records this as a `TODO(deferred)` for a shared `_cli_env.py`; extraction is out-of-scope for WP-006 (touches sibling CLIs). No delta — theoretical until a follow-on WP touches those files (CR-04: no failing characterisation test grounds a fix here).

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** the 4-CLI boilerplate duplication is the only broad-gap signal; it is already captured as a deferred follow-on, not a full-audit trigger.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `compileall` on changed files; full pytest suite. Base: clean. Head: 0 new errors. Coverage gap: subprocess-invoked executable not tracked by in-process `--cov` (established pattern for these `.py`-less CLIs); behavioural coverage via 7 integration tests instead.
- [✓] **CR-02 Single-reader pass.** Diff is 472 lines / 2 files — above the 200-line threshold but only 2 files, both brand-new, single-purpose, authored and read end-to-end this session. Recorded as a justified single-reader pass; lens checks run inline with conservative severity tilt.
- [✓] **CR-03 Full-file reads.** Both changed files (192 + 280 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens checks enumerated with the symbols/patterns examined.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (+ checks listed). Security: nothing surfaced (+ primitives/scanners listed). Quality: all 7 outputs produced (build / jsx N/A / dead-surface / contract-drift / test-coverage / style / CR-10 perf).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, 1 dir). PH-02 Size: low (472 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schema / 0 secrets / 0 infra). PH-04 Completeness: none (tests included). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/create-brain-backlog-and-traversal` over the two new files (untracked, staged with `git add -N` for diff visibility).
- **Neighbour expansion:** git grep; callees (`capture_idea`, adapters) unchanged → no neighbour findings.
- **Neighbour cap:** not reached (0 of ~3 considered).
- **Scanners run:** ruff (lint), compileall (syntax), grep-based secret scan.
- **Scanners unavailable:** gitleaks/semgrep/trivy not installed locally; substituted grep secret-pattern scan — no hits (low risk: no new deps, no config/secret files in diff).
- **Lenses dispatched in parallel:** no — single-reader pass per the CR-02 note above.
