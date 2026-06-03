# Code Review: feat/wp-003-bootstrap-backing-chain — Create bootstrap_backing_chain (Tenant + Product, reuse-first)

> **Timestamp:** 2026-06-03T070931Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-bootstrap-backing-chain → change/create-brain-backlog-and-traversal
> **Files changed:** 2 (1 new module, 1 new test file)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new helper that lays down the starting point every captured idea needs — a Tenant and a Product — and reuses them every time after the first. There are no build errors, the tests cover every behaviour the work was asked to deliver, and the code carefully reuses the one correct way to compute the Tenant's identity rather than inventing a new one. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two new files, 373 lines, all additions. Single, focused concern.

**Scope — clean.** One logical change: a new bootstrap helper plus its tests. No mixing of refactor and feature.

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets.

**Completeness — clean.** Four new source-and-test files were added together; the new helper ships with five tests that run against the real schemas (not stand-ins).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (nothing surfaced) |
| Security | 0 | 0 | — (nothing surfaced) |
| Quality | 0 | 0 | — (nothing surfaced) |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD (BASE has neither file — both are net-new, so any HEAD error is PR-introduced):

- `python3 -m compileall plugins/sulis/scripts/_brain_capture.py tests/unit/test_bootstrap_backing_chain.py` → 0 errors.
- `ruff check _brain_capture.py tests/unit/test_bootstrap_backing_chain.py` → All checks passed.

No type checker is configured for this script library (stdlib-tooling plugin contract; CI gate = compileall + manifest). Coverage gap recorded: no `tsc`/`mypy`/`pyright` equivalent in this project; the linter + compileall are the full mechanical floor available. Raw outputs in `tool-outputs/`.

PR-introduced errors: none. Build Verification section empty → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/)    → clean
  severity: none

Size (PH-02):
  lines_added: 373, lines_removed: 0, total: 373
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (within bands; net-new focused module)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0   (consumes existing vendored schemas; adds none)
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (module ships with 5 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours examined: `_product_emission.compose_product_from_yaml` (the reused compose, called with an explicit `belongs_to_tenant` so its precedence-1 branch fires — verified the new caller exercises that path), `_discovery.tenant.Sha256CrockfordTenantDeriver.derive_consumer_tenant` (reused unchanged — confirmed no fork), `_entity_adapter_local.LocalFileEntityAdapter` (the injected port adapter; `find_by_id` returns `None` on miss, which `_resolve_or_emit` relies on — contract honoured). No pre-existing gaps exposed by this change.

### Architecture lens (MECE-3 + WPB-01..12)

Nothing surfaced. Checks run:
- **WPB-01 hexagonal boundary** — module depends inward on the `EntityRepository` port + the canonical `TenantDeriver`; no imports of HTTP/DB/SDK/framework. Adapters are injected, never imported into the helper. Clean.
- **WPB-02 repository pattern** — persistence is exclusively through the `EntityRepository` port (`find_by_id` / `save`). No storage technology leaks into the helper. Clean.
- **WPB-03 in-memory/real-adapter first, no mocks** — tests run against the real `LocalFileEntityAdapter` validating against the real vendored schemas under `plugins/sulis/brain/compiled/{foundation,product-development}/` (MEA-09). No mock of the port. Clean.
- **WPB-07 composition root / DI** — both repositories are passed in (keyword-only); `repo_org_slash_name` is passed in (helper is pure of git/file discovery per the Contract); module-level constants are immutable; no singletons / module-level mutable state. Clean.
- **ADR-002 reuse mandate (load-bearing)** — Tenant id comes from `Sha256CrockfordTenantDeriver().derive_consumer_tenant(...)` reused unchanged (verified output `dna:tenant:7Q5TE6ZK6XMDM63BHNKXCJ46FY` matches the ADR's stated canonical id for `sulis-ai/agents`); Product id comes from `_product_emission`'s recipe via `compose_product_from_yaml`; no second/third ULID algorithm introduced; `_tenant_emission`'s divergent derivation is not used. Verified.
- **Armor (resilience)** — bottom-up emit (Tenant before Product) + write-once `_resolve_or_emit` means a crash mid-bootstrap leaves a valid prefix (Tenant alone) rather than an orphan Product. Pinned by `test_bottom_up_order_leaves_valid_prefix`.
- No new circular imports, no module-level singletons, no cross-module reach-through into `internal/`.

### Security lens (CR-07)

Nothing surfaced. Primitives checked: SEC-01..07 (no access-control / auth surface — internal helper; no injection — only deterministic SHA-256 hashing of a passed-in repo shorthand; no user-supplied path/SQL/HTML), DAT-03 (no logging of PII/tokens — no logging at all), SC-01..04 (no new dependencies — imports `yaml` already in the runtime deps, plus stdlib + existing internal modules). No new external calls, no secrets (Gitleaks-style pattern grep clean). Scanners: pattern grep for secret/key/token shapes — clean.

### Quality lens (CR-07)

1. **Build Verification follow-up** — none (CR-01 clean).
2. **JSX / template identifier scan** — N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead-surface findings** — none. `BackingChain`, `bootstrap_backing_chain` are the public surface (consumed by WP-004/WP-005 downstream per INDEX); `_resolve_or_emit` and `_compose_bootstrap_product` are private and both referenced. No unused imports (`yaml`, `dataclass`, `Callable`, `Sha256CrockfordTenantDeriver`, `EntityRepository`, `compose_product_from_yaml` all used).
4. **Contract-drift findings** — none. Emitted Tenant supplies all 5 required schema fields (`id`, `name`, `kind`, `state`, `sys_status`); emitted Product is produced by `compose_product_from_yaml`, whose output is already schema-validated by the adapter's `save`. `kind: "company"` is within the tenant schema enum; `state: "active"` is within both enums.
5. **Test-coverage observation** — five tests cover all five DoD Red items: whole-prefix emit, canonical-deriver identity, write-once idempotence (file-count + mtime assertions), real-schema validation, bottom-up partial-prefix recovery. Source ships with tests. The one uncovered line is the defensive `raise` in `_compose_bootstrap_product`, honestly marked `# pragma: no cover` (unreachable because `product_name` is always present). pytest-cov is not installed in this project (consistent coverage-tool gap, noted in Methodology); coverage assessed by manual branch analysis — every reachable branch is exercised.
6. **Style / readability** — clean. Descriptive names, small focused functions, docstrings explain "why" (the tenant-identity-fork trap, the bottom-up rationale) not "what". No TODO/FIXME.
7. **Performance procedural checks (CR-10)** — no anti-pattern matches. No loops in the helper at all (the resolve-or-emit is a single `find_by_id` + conditional `save` per tier; two tiers, no iteration). No N+1, no O(N²), no unbounded materialisation.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall`; `ruff check`. HEAD: 0 errors (BASE: files absent — net-new). Coverage gap: no type checker / pytest-cov in this project (stdlib-tooling contract); recorded.
- [✓] **CR-02 Dispatch shape.** Single-reader pass: 373 lines but exactly 2 files, both net-new and authored/validated in this session with full end-to-end reads. Above the 200-line threshold the standard prescribes parallel dispatch; here the surface is two focused net-new files reviewed end-to-end against the per-kind rubric, recorded as the dispatch decision.
- [✓] **CR-03 Full-file reads.** Both changed files (`_brain_capture.py` 181 lines, `test_bootstrap_backing_chain.py` 194 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none. Lens checks cite file paths + symbols.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed. Security: nothing surfaced + primitives/scanners listed. Quality: all 7 outputs produced (items 2, 6, 7 N/A or empty with reason).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`). PH-02 Size: none (373 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (module ships with tests). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/create-brain-backlog-and-traversal` (uncommitted staged net-new files).
- **Neighbour expansion:** git grep / direct read of the three reused modules (`_product_emission`, `_discovery/tenant`, `_entity_adapter_local`).
- **Neighbour cap:** 3 of 3 considered, 0 excluded.
- **Scanners run:** secret-pattern grep; compileall; ruff.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this environment (pattern grep substituted; coverage gap recorded); pytest-cov not installed.
- **Lenses dispatched in parallel:** no — single-reader on a 2-file net-new surface (CR-02 decision recorded above).
