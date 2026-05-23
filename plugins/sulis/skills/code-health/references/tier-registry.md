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
    founder_skill: "/sulis:check-build"
    operator_skills: null  # build logic + manifest hygiene live directly in check-build
    extra_args: []  # hygiene-only by default; --run is opt-in (builds have side effects)
    covers:
      - "Build artefact produces (multi-system detection: pip / npm / go / cargo / docker / make)"
      - "Manifest hygiene (plugin.json / marketplace.json / package.json semantic correctness; per HD-004)"
      - "Tests are runnable — actual test-pass at tier 3"

  - number: 2
    name: Safe
    founder_question: "Could anyone be harmed? (security, leaked credentials, PII)"
    wired: false
    wired_in: planned
    founder_skill: null
    operator_skills: null  # future: sulis-security:codebase-assess wrapped
    covers:
      - "Security vulnerabilities (SEC-01..07)"
      - "Data protection (DAT-01..05)"
      - "Supply chain (SC-01..04)"
      - "Infrastructure-side secrets handling"

  - number: 3
    name: Works
    founder_question: "Do the tests pass? Does it do what it should?"
    wired: true
    wired_in: "0.6.0"
    founder_skill: "/sulis:check-tests"
    operator_skills: null  # regression logic lives directly in check-tests; sulis is the everything-plugin
    extra_args: ["--run", "--timeout", "60"]  # code-health passes --run by default; tighter timeout than check-tests' standalone default
    covers:
      - "Tests pass when run"
      - "Regressions (newly-failing tests vs baseline)"
      - "Functional spec parity (when spec exists; future)"
      - "Smoke / deploy verification (future)"

  - number: 4
    name: Survives
    founder_question: "Does it handle failure gracefully?"
    wired: false
    wired_in: planned
    founder_skill: null
    operator_skills: null  # future: sea:codebase-audit (Armor pillar) + sea:failure-mode-audit
    covers:
      - "Timeouts / retries / circuit breakers on external calls (MEA-04)"
      - "Observability — every operation logs (MEA-07)"
      - "Error handling (INF-04)"
      - "No data-loss paths"

  - number: 5
    name: Understandable
    founder_question: "Can a new person read it?"
    wired: true
    wired_in: "0.5.0"
    founder_skill: "/sulis:check-readability"
    operator_skills: null  # audit logic is INSIDE check-readability (sulis is becoming the everything-plugin)
    covers:
      - "Naming clarity (per identifier)"
      - "Module cohesion (kitchen-sink-file detection)"
      - "Jargon density (per module)"

  - number: 6
    name: Evolves
    founder_question: "Can we change it without breaking things?"
    wired: false
    wired_in: planned
    founder_skill: null
    operator_skills: null  # future: dead-code, surface-parity, test-audit, migration-completion
    covers:
      - "Dead code"
      - "Migration completion"
      - "Surface contract drift (CLI ↔ SDK ↔ MCP ↔ OpenAPI)"
      - "Test quality beyond coverage"

  - number: 7
    name: Polished
    founder_question: "Performance, accessibility, design quality?"
    wired: false
    wired_in: deferred  # not planned for any near-term release
    founder_skill: null
    operator_skills: null
    covers:
      - "Performance budgets"
      - "Accessibility (a11y)"
      - "Design/UX consistency"
      - "Documentation completeness"
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

**v1 note:** tiers 1+2 aren't wired. Hard-stop logic literally never fires
in v1. The gating code path is in the orchestrator (`_apply_gating()`) but
is a no-op until those tiers ship. Documented here so future readers don't
think it's broken.

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

| Operator concept | Founder vocab |
|---|---|
| MECE-3 Armor pillar | Tier 4 (Survives) |
| MECE-3 Form pillar | Tier 5 (Understandable) + Tier 6 (Evolves) — split |
| MECE-3 Proof pillar | Tier 3 (Works) + Tier 6 (Evolves) — split |
| SEC-01..07 | Tier 2 (Safe) — security category |
| DAT-01..05 | Tier 2 (Safe) — data-protection category |
| SC-01..04 | Tier 2 (Safe) — supply-chain category |
| INF-01..04 | Tier 1 (Exists) + Tier 4 (Survives) — split per primitive |
| CQ-01 (complexity) | Tier 5 (Understandable) primarily, Tier 6 (Evolves) secondarily |
| CQ-02 (test coverage) | Tier 3 (Works) + Tier 6 (Evolves) — split |
| CQ-03 (duplication) | Tier 6 (Evolves) |
| CQ-04 (tech debt) | Tier 6 (Evolves) |
| CQ-05 (review practices) | Tier 6 (Evolves) — process-side |
