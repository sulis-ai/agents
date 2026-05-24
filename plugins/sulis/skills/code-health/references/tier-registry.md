# Tier Registry — Maslow for Code

The canonical list of seven code-health tiers. Source-of-truth for the
orchestrator's tier walk. Adding or wiring a tier is a registry update,
not a SKILL.md or orchestrator rewrite.

## The seven tiers

Each tier has: a number (1-7), a name (founder-vocab), a founder description
(short, plain English), a wired-status flag, the founder-facing skill that
implements it (when wired), and the operator-side concerns it covers.

```yaml
tiers:
  - number: 1
    name: Exists
    founder_question: "Does it build? Do the basics work?"
    wired: true
    wired_in: "0.7.0"
    deepened_in: "0.16.0"
    founder_skill: "/sulis:check-build"
    operator_skills: null  # build logic + manifest hygiene + container/deploy checks live directly in check-build
    extra_args: []  # hygiene-only by default; --run is opt-in (builds have side effects)
    covers:
      - "Build artefact produces (multi-system detection: pip / npm / go / cargo / docker / make)"
      - "Manifest hygiene (plugin.json / marketplace.json / package.json semantic correctness; per HD-004)"
      - "INF-01 container security (hadolint Dockerfile lint + Trivy base-image CVE scan; wrappers NEW)"
      - "INF-02 deploy-config secrets (Gitleaks yaml/k8s/CI scope; wrapper NEW)"
      - "Tests are runnable — actual test-pass at tier 3"

  - number: 2
    name: Safe
    founder_question: "Could anyone be harmed? (security, leaked credentials, dangerous patterns)"
    wired: true
    wired_in: "0.8.0"
    deepened_in: "0.16.0"  # Phase 2 iteration 1 of upsurge plan: primitive catalogue declared
    founder_skill: "/sulis:check-security"
    operator_skills: null  # codebase-assess scheduled for Phase 5 retirement; SEC + DAT + SC primitives migrate into check-security
    extra_args: []
    covers:
      - "SEC-01..07 (access control / authentication / injection / input validation / XSS / SSRF / secrets in git history)"
      - "DAT-01..05 (encryption at rest / TLS / PII / secrets management / audit logging)"
      - "SC-01..04 (CVE / freshness / SBOM / transitive depth)"
      - "Optional when --url: DAT-02 TLS analysis + INF-03 HTTP headers"
      - "Tool wrappers (semgrep / gitleaks / trivy / testssl / curl) flagged NEW pending Phase 2 iteration 2"

  - number: 3
    name: Works
    founder_question: "Do the tests pass? Does it do what it should?"
    wired: true
    wired_in: "0.6.0"
    deepened_in: "0.16.0"
    founder_skill: "/sulis:check-tests"
    operator_skills: null  # regression logic + coverage logic live directly in check-tests
    extra_args: ["--run", "--timeout", "60"]  # code-health passes --run by default; tighter timeout than check-tests' standalone default
    covers:
      - "Tests pass when run (existing)"
      - "Regressions (newly-failing tests vs baseline) (existing)"
      - "CQ-02 test coverage quality (pytest-cov / vitest coverage / jest coverage; wrapper NEW)"
      - "Functional spec parity (when spec exists; future)"
      - "Smoke / deploy verification (future)"

  - number: 4
    name: Survives
    founder_question: "Does it handle failure gracefully?"
    wired: true
    wired_in: "0.10.0"
    deepened_in: "0.16.0"
    founder_skill: "/sulis:check-reliability"
    operator_skills: null  # codebase-assess Armor primitives migrating into check-reliability
    extra_args: []
    covers:
      - "Missing timeouts on HTTP / subprocess / DB calls (existing)"
      - "Silent-except (try/except/pass) (existing)"
      - "Broad-except without re-raise (existing)"
      - "INF-04 verbose-error / debug-mode-in-prod (Semgrep wrapper NEW)"
      - "DAT-05 audit-logging (manual hypothesis; HYPOTHESIS infrastructure NEW)"

  - number: 5
    name: Understandable
    founder_question: "Can a new person read it?"
    wired: true
    wired_in: "0.5.0"
    deepened_in: "0.16.0"
    founder_skill: "/sulis:check-readability"
    operator_skills: null  # audit logic is INSIDE check-readability
    covers:
      - "Naming clarity per identifier (existing)"
      - "Module cohesion / kitchen-sink-file detection (existing)"
      - "Jargon density per module (existing)"
      - "CQ-01 cyclomatic complexity (lizard wrapper NEW)"
      - "CQ-03 code duplication (jscpd wrapper NEW)"

  - number: 6
    name: Evolves
    founder_question: "Can we change it without breaking things?"
    wired: true
    wired_in: "0.11.0"
    deepened_in: "0.16.0"
    founder_skill: "/sulis:check-maintainability"
    operator_skills: null
    extra_args: []
    covers:
      - "Dead code (unused functions / classes / imports / constants) — advisory-default (existing)"
      - "CQ-05 review practices via git-log analysis (manual hypothesis; HYPOTHESIS infrastructure NEW)"
      - "Migration completion (deferred to future iteration — needs migration-marker convention)"
      - "Surface contract drift (deferred to future iteration — project-specific)"

  - number: 7
    name: Polished
    founder_question: "Does the project feel professional?"
    wired: true
    wired_in: "0.11.0"
    deepened_in: "0.16.0"
    founder_skill: "/sulis:check-polish"
    operator_skills: null
    extra_args: []
    covers:
      - "Documentation completeness (README, CHANGELOG, LICENSE, plugin.json keywords)"
      - "CQ-04 technical debt density (TODO/FIXME/HACK markers) — check-polish is the canonical CQ-04 owner; codebase-assess defers here post-Phase 5"
      - "File hygiene (trailing whitespace, mixed line endings, trailing newline)"
      - "Performance / accessibility / UX deferred — need upstream design choice (which perf budget? which a11y standard?)"
```

## Tier-gating semantics

Per `.architecture/sulis-checkup/TDD.md` ADR-002:

- **Hard stop:** if a tier 1 OR tier 2 finding has severity `critical`, the
  orchestrator skips tiers N+1..7 entirely. The report stops at tier N with
  the failing finding and the remediation.
- **Soft de-prioritise:** if a tier 1 or 2 finding has severity `high` (not
  critical), or any tier 3+ finding fires, the orchestrator runs all
  remaining tiers but visually de-emphasises higher-tier findings.
- **Per-finding gating:** a single finding may opt into hard-stop semantics
  by declaring `gate: hard-stop` in its metadata.

**v0.16.0 note:** all 7 tiers are wired (since v0.11.0; deepened against
v0.7.0 methodology in v0.16.0). Hard-stop logic for tier 1/2 CRITICAL
findings is in `orchestrator._apply_gating()` and fires when applicable.

For each tier, primitive coverage is documented in the consuming skill's
SKILL.md frontmatter (`verification_spiral.custom_dimensions` → Primitive
Coverage Completeness) and scored under SPIRAL_TEMPLATES in
`iterations/{N}/VERIFICATION_REPORT.md`. Per-tool wrappers flagged NEW
in iteration 1 (v0.16.0) are scheduled for build-out in iteration 2 +
later commits.

## Founder override flags

- `--check-everything` — disable hard-stop; run all tiers regardless of
  lower-tier failures. Report still surfaces would-have-stopped findings
  at the top with `(WOULD HAVE STOPPED)` tag.
- `--tier=N` — run only tier N (and its hard-stop prerequisites if any
  haven't been resolved). Used for focused re-runs. **In v1, only
  `--tier=5` produces non-stubbed output.**

## How to wire a new tier

Adding a tier-skill (e.g., `/sulis:check-security` for tier 2):

1. Author the tier-skill via `sulis:add-skill` (five gates).
2. Update this registry: `wired: true`, `wired_in: "{plugin-version}"`,
   `founder_skill: "/sulis:check-security"`, `covers:` enumerated.
3. The orchestrator picks up the registry change automatically — no code
   change to `orchestrator.py` required if the tier-skill follows the
   founder-skill contract (returns CHECKUP-compatible JSON in `--raw`
   mode).
4. Bump sulis plugin version (minor — new functionality).
5. Document the wiring in code-health's CHANGELOG entry.

## Founder-vocab tier names

Operator-side primitive IDs (MEA-04, CQ-01, SEC-07, INF-02, DAT-04, SC-03,
etc.) MUST NEVER appear in founder mode. The translation:

| Operator primitive | Canonical tier (post-v0.16.0 upsurge) | Rationale |
|---|---|---|
| SEC-01..07 | Tier 2 (Safe) | security category — direct fit |
| DAT-01 encryption at rest | Tier 2 (Safe) | data-protection — hypothesis primitive |
| DAT-02 TLS | Tier 2 (Safe) when --url | data-protection deployed surface |
| DAT-03 PII / PHI | Tier 2 (Safe) | data-protection direct fit |
| DAT-04 secrets management | Tier 2 (Safe) | data-protection direct fit (overlap with SEC-07 git history) |
| DAT-05 audit logging | Tier 4 (Survives) | hypothesis primitive — failure-mode-adjacent (auth events) |
| SC-01..04 | Tier 2 (Safe) | supply-chain — direct fit |
| INF-01 container security | Tier 1 (Exists) | build-time concern |
| INF-02 deploy-config secrets | Tier 1 (Exists) | build-time / deployment manifest concern |
| INF-03 HTTP headers | Tier 2 (Safe) when --url | deployed surface adjacent to TLS |
| INF-04 verbose-error / debug-mode | Tier 4 (Survives) | reliability failure mode |
| CQ-01 cyclomatic complexity | Tier 5 (Understandable) | readability concern |
| CQ-02 test coverage quality | Tier 3 (Works) | works = tested |
| CQ-03 code duplication | Tier 5 (Understandable) | readability — duplication harms clarity |
| CQ-04 technical debt density | Tier 7 (Polished) | check-polish is canonical CQ-04 owner |
| CQ-05 review practices | Tier 6 (Evolves) | process-side maintainability |

**MECE check (post-v0.16.0):**

- **Mutually exclusive:** each primitive belongs to exactly one tier. DAT-04 + SEC-07 overlap in coverage (git history secret scan) but live in the same tier (Tier 2) so no cross-tier collision.
- **Collectively exhaustive within declared scope:** the 25 codebase-assess primitives all map to a tier; no orphan primitives.
- **Maslow ordering holds:** tier-1 failure (no build) implies tier-2 (can't be safe if it doesn't run), tier-3 (can't pass tests), tier-4..7 cascade.
