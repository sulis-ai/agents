# Code Review: WP-002 — L1 proxy (scrub-before-DNS + content-as-untrusted-data framing)

> **Timestamp:** 2026-06-13T095201Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-002-l1-proxy-scrub-and-data-framing → change/harden-agent-execution-boundary
> **Files changed:** 4 (2 new source, 1 new test, 1 test extended)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the L1 proxy's two safety controls: it refuses to send any outbound web request that carries a recognised secret (and refuses *before* it contacts the network, so the secret never leaves the process), and it wraps every page it fetches in a labelled "this is data, not instructions" envelope. The work is well-scoped, fully tested (every line of the two new files is exercised), and clean. The review found one defence-in-depth gap — the secret check looked at request header *values* but not header *names* — which has already been fixed and tested in this same change. No outstanding issues.

## What to fix

No issues that need attention. One small improvement was found and applied during review (see below), so nothing is left for you to do.

### Applied during review — `_safe_fetch/proxy.py`

**What was happening:** The secret check scanned the web address, the request body, and the *values* of each request header — but not the header *names*. A secret hidden in a header name would have slipped past.

**Why it matters:** This is a safety control whose whole job is to stop secrets leaving. Even an unlikely hiding spot should be covered.

**What was done:** The check now scans header names as well as values. Real-world header names (like `Authorization` or `Content-Type`) never look like secrets, so this added no false alarms. A new test confirms a secret placed in a header name is refused before any network call.

## How this pull request is shaped

Small, single-concern, and well-tested. 457 lines across 4 files, all in one module (`_safe_fetch/`). New behaviour ships with new tests (every line of both new files is covered). Nothing to flag on size, scope, safety, or completeness.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff check clean; no type checker configured (coverage gap, matches repo baseline).
- **PR Hygiene:** 0 high. Size low (457 lines / 4 files). Scope clean (single `feat:` concern, one module). Safety clean (no migrations/schemas/infra/secrets-in-code). Completeness clean (new source ships with tests).
- **In the changes:** 1 finding (1 medium — defence-in-depth, addressed inline).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one finding was fixed inline with a backing test, not queued as a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 1 (addressed) | 0 | header *names* not scanned by scrub — fixed inline |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

ruff check (the project's configured checker): **All checks passed!** on all four files (`tool-outputs/ruff-check.log`). No mypy/pyright/pyrefly configured in `plugins/sulis/scripts/pyproject.toml` — recorded as a coverage gap (Methodology); consistent with the existing WP-001 modules, which are also not type-checked in CI.

### Findings in the Changes

#### `_safe_fetch/proxy.py:_refuse_if_secret` — medium (security) — ADDRESSED INLINE

**Quoted text (before):**
```python
parts: list[str] = [req.method, req.url, *req.headers.values()]
```

**Finding:** The scrub scanned method + URL + header *values* + body, but not header *names*. `FetchRequest.headers` is `dict[str, str]`; a secret-shaped header name would bypass the refuse policy. Defence-in-depth gap in a security-critical control (SC-L1.3).

**Resolution (inline):** Now scans `headers.keys()` and `headers.values()`. Verified false-positive-safe — common header names (`Authorization`, `X-Api-Key`, `Content-Type`, `X-CSRF-Token`, `Cookie`) produce zero `find_secrets` hits. Backed by new test `test_secret_in_header_name_is_refused_before_dns` (parametrized over all 5 catalogued shapes). Re-reviewed post-fix: 42/42 tests pass, 100% coverage, ruff clean.

### Findings in the Neighbours

None. The only neighbours are WP-001's `_secret_patterns` (consumed read-only via `find_secrets`) and `_safe_fetch.ports` (the implemented protocol); the diff touches neither.

### Watch List

- **SSRF / private-host egress is NOT in WP-002.** The proxy does not validate URL scheme/host or block private/loopback destinations beyond the incidental `private-ip` secret-pattern hit. This is correct per ADR-002 (the no-egress wall is L3) and the WP DoD (egress/no-act halves of SC-L1.2/1.4 proven in WP-003 under the confinement harness). Recorded for awareness, not a finding.
- **Catalogue is format-based (honest limit, ADR-002).** A novel secret shape the catalogue doesn't recognise can pass; the Rule-of-Two credential exclusion (WP-003 spawn wiring) is the primary control, this scrub is defence-in-depth. Documented in the module docstring.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check on all 4 files: 0 errors (`tool-outputs/ruff-check.log`). No type checker configured → coverage gap recorded (matches repo baseline). ruff format clean on all 3 authored new files.
- [✓] **CR-02 Single-reader justified.** 457 lines / 4 files; security-critical so read conservatively end-to-end. Diff is one cohesive concern in one module; all files authored this session and held in full context.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites symbol + quoted text + backing test.
- [✓] **CR-05 Severity rubric.** Applied. 1 medium (defence-in-depth in a security control), addressed inline.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no unread files; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (Form: pure framing, inward deps, no singleton/cycle; Armor: timeout passthrough + fail-closed scrub + no hardcoded secrets; Proof: port shares contract test with fake, MEA-09). Security: 1 finding (header-name scrub) addressed inline; probed framing sentinel-escape (robust), refusal-does-not-leak-value (asserted), SSRF scope (out-of-scope per ADR-002). Quality: 0 dead surface, 0 contract drift, tests cover all new behaviour (100% on both new modules), CR-10 perf scan clean (no loops over I/O; scrub is a bounded scan over a small fixed parts list).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat concern, one dir). PH-02 Size: low (457 lines / 4 files). PH-03 Safety: low (0 migrations, 0 schemas, 0 infra, 0 secret-in-code). PH-04 Completeness: low (new source ships with tests). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/harden-agent-execution-boundary`
- **Neighbour expansion:** string scan; only read-only consumers (`_secret_patterns`, `ports`), neither modified.
- **Neighbour cap:** not reached (0 of 0).
- **Scanners run:** ruff (check + format).
- **Scanners unavailable:** mypy/pyright (not configured); gitleaks/semgrep/trivy (not installed in env) — manual secret/SSRF review performed instead.
- **Lenses dispatched in parallel:** no (single-reader path; diff within size sensibility, security-critical so read in full).
