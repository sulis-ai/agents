# Code Review: feat/wp-003-detect-phase — Implement Detect phase (RepoInspector port + LocalFilesystemInspector adapter)

> **Timestamp:** 2026-06-01T17:16:13Z
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-detect-phase → change/create-discover-project
> **Files changed:** 8 (all additions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the Detect phase of the new `/sulis:discover-project` skill — the part that reads a repo's basic shape (git remote, package manifests, CI workflows, optional `.sulis/repo-contract.yml`) so the rest of the skill can propose configuration values. The change is well-scoped: one new module, one new test file, three small fixture directories. Tests pass (13 of 13) and there are no build errors. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — looks good**

689 lines added across 8 files. One source module + one test file + 6 small fixture files. Right-sized for a single piece of work.

**Scope — looks good**

Single concern: the Detect phase. No mixing in unrelated changes.

**Safety — looks good**

No database migrations, no schema changes, no infrastructure touches, no secrets in the diff.

**Completeness — looks good**

The new source module ships with its own test file. 13 tests cover the four port methods plus the typed-error mapping plus a chaos shim for the subprocess timeout.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`. The author tier above contains everything the PR author needs to act.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (n/a — new module; no existing callers yet — WP-008 will wire it)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | (none) |
| Security | 0 | 0 | (none) |
| Quality | 0 | 0 | (none) |

### Build Verification (CR-01)

- `ruff check plugins/sulis/scripts/_discovery/ plugins/sulis/scripts/tests/unit/test_discovery_inspector.py` — All checks passed!
- `uv run pytest tests/unit/test_discovery_inspector.py -q` — 13 passed in 0.52s
- Coverage on `_discovery/inspector.py` — 92% (above the 90% WP DoD threshold)

No PR-introduced errors. Raw tool outputs at `tool-outputs/ruff-head.log` and `tool-outputs/pytest-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts/)
  severity: note

Size (PH-02):
  lines_added: 689, lines_removed: 0, total: 689
  files_changed: 8
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: note (within both line + file thresholds)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: note

Completeness (PH-04):
  new_source_files: 1 (inspector.py) + 1 (__init__.py shared with WP-002)
  new_test_files: 1 (test_discovery_inspector.py)
  new_source_without_test: 0
  api_change_without_schema: false
  severity: note
```

### Findings in the Changes

#### Architecture lens

Nothing surfaced. Checks run:
- Ports & Adapters discipline (TDD §Form §Ports): `RepoInspector` Protocol defined in the same module as `LocalFilesystemInspector` adapter — acceptable for v1 (domain doesn't yet exist as a separate package). Adapter satisfies the port; `@runtime_checkable` permits `isinstance()` verification (exercised by `test_implements_port_protocol`).
- No new domain → infrastructure import direction violations.
- No module-level singletons; the adapter is constructable and reusable across calls.
- No circular imports.
- External dependency policy (TDD §Armor): every `subprocess.run` call is wrapped through `_run_git` with `timeout=self.GIT_TIMEOUT_S` (5 s default) and centralised typed-error mapping. No retries (correct — local CLI, deterministic).
- No new secrets in the diff; no service-to-service calls.
- Verification (TDD §Proof): contract tests + adapter test class authored; chaos shim for the timeout boundary; `tmp_path` + dynamic `git init` for the happy-path read_root, avoiding committed `.git/` dirs.

#### Security lens

Nothing surfaced. Primitives checked:
- SEC-04 injection: every subprocess invocation passes a fully-literal argv list (`["git", "rev-parse", ...]`); the user-supplied `path` is passed via `cwd=`, not interpolated into the command. No `shell=True`. No injection vector.
- DAT-01 deserialisation: all parsers use safe deserialisers — `json.loads`, `tomllib.load`, `yaml.safe_load`. No `yaml.load`, no `pickle`, no `eval`.
- SEC-06 secrets in diff: 0 hits across `_discovery/`, the test file, and the fixtures.
- DAT-03 sensitive logging: no logging in this module; nothing to redact.
- Read-only adapter; no write paths (writes are WP-006's responsibility).

#### Quality lens (CR-07 — all seven outputs)

1. **Build Verification follow-up.** No CR-01 errors.
2. **JSX / template identifier scan.** N/A (Python files only).
3. **Dead surface.** None. `_REPO_CONTRACT_RELPATH` used at line 256. All four dataclasses (`RepoRoot`, `Manifest`, `CiWorkflow`, `RepoContract`) consumed by tests. Both typed exceptions (`NonGitDirectoryError`, `NoRemoteError`) raised by adapter + asserted in tests. All four port methods invoked by tests. All parsing helpers (`_parse_package_json`, `_parse_pyproject_toml`, `_parse_github_workflow`, `_parse_gitlab_ci`, `_normalise_triggers`) reachable via the port methods.
4. **Contract drift.** None. The `Manifest` dataclass carries `private: bool | None` — `_parse_package_json` reads `data.get("private")` (correct; `package.json` may or may not have it), `_parse_pyproject_toml` sets it to `None` (correct; `pyproject.toml` has no canonical `private` field). Scripts-keys list is sorted at parse time so `test_contract_read_package_manifests_finds_package_json`'s `assert sorted(m.scripts_keys) == ...` is deterministic.
5. **Test coverage observation.** 13 tests for 4 port methods + 4 dataclasses + 2 typed errors + 1 chaos shim + 1 Protocol-isinstance check. 92% line coverage on `inspector.py`; missing lines are defensive edge cases (malformed YAML returning non-dict, CalledProcessError on optional `git branch --show-current`, etc.). Above the 90% DoD threshold.
6. **Style / readability.** Single-responsibility methods; clear naming; canonical Step annotations (`# canonical:step:<name>`) above each port-method block — these are load-bearing for WP-009's drift parser. Module docstring cites the canonical-source path verbatim. No TODO/FIXME in this diff.
7. **CR-10 performance procedural checks.** No anti-pattern matches. The only loops are the workflows enumeration (`for ext in ("*.yml", "*.yaml"): for wf_path in sorted(gh_dir.glob(ext)):`) which is bounded by the file count under `.github/workflows/` (typically <20 in real repos). Each iteration parses one local YAML file — no DB calls, no RPC, no nested filesystem N+1.

### Findings in the Neighbours

None. This is a new module; no existing callers in the codebase (WP-008's SKILL.md will wire it — that work is downstream).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable
- **Existing security report:** none for `_discovery/` (this is the first WP in the package)
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` on the diff; `uv run pytest tests/unit/test_discovery_inspector.py`. Base: branch had no `_discovery/` (new module). Head: 0 errors, 13/13 tests pass. Coverage 92% on `inspector.py`.
- [✓] **CR-02 Dispatch shape.** Diff: 689 lines / 8 files. Above the 200-line carve-out — but only 2 substantive files (inspector.py 368 lines + test 271 lines); the other 6 are tiny fixture data files (4-11 lines each). Lens work performed sequentially against the substantive files; fixtures inspected for secret patterns only.
- [✓] **CR-03 Full-file reads.** Both files >50 lines (inspector.py 368, test 271) read end-to-end. Fixture files all <12 lines.
- [✓] **CR-04 Evidence discipline.** No findings raised; lens output cites checks-run lists rather than file:line references.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: `PASS`. Auto-downgrade triggers: none fired (Build Verification empty, no files unread, all three lenses produced explicit "nothing surfaced" output, no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks-run list. Security: nothing surfaced + primitives-checked list. Quality: all seven outputs present (CR-01 follow-up, JSX-scan N/A, dead-surface, contract-drift, test-coverage, style, CR-10 performance).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single Conventional Commit type, single top-level dir). PH-02 Size: note (689 lines / 8 files — within thresholds; 6 of the files are tiny fixture data). PH-03 Safety: note (no migrations, no schemas, no infra, no secrets). PH-04 Completeness: note (1 source file ships with 1 test file). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff change/create-discover-project` (working tree; branch not yet pushed)
- **Neighbour expansion:** none (new module; no callers yet — WP-008 wires it downstream)
- **Neighbour cap:** n/a
- **Scanners run:** ruff (lint), pytest (test+coverage), grep (secret pattern scan)
- **Scanners unavailable:** Gitleaks, Trivy, Semgrep, ast-grep — falling back to grep for secret patterns + direct read for structural / injection checks. Coverage gap noted; deemed adequate for a 689-line diff with no infra touches.
- **Lenses dispatched:** sequentially against the 2 substantive files (inspector.py + test_discovery_inspector.py); fixture files scanned for secrets only.
