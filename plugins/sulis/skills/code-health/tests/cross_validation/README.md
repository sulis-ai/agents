# Cross-validation — code-health vs codebase-assess

> **Phase 4 of the upsurge plan.** Verify code-health surfaces every finding
> codebase-assess produces (modulo timing + acceptable differences). Target
> ≥ 95% parity per target.

## Methodology

For each target project:

1. Run `/sulis:code-health --project NAME` → captures CHECKUP.md + per-tier
   raw envelopes
2. Run `/sulis:codebase-assess acme NAME` → captures
   `.security/{NAME}/viability-report-{TIMESTAMP}.md`
3. Diff the two outputs at the primitive level:
   - For each codebase-assess primitive (SEC-01..07 + DAT-01..05 + CQ-01..05
     + SC-01..04 + INF-01..04): does code-health's corresponding tier
     surface the same finding (or NOT_ASSESSED with consistent reason)?
   - Tally MATCH / DIVERGENT / NOT_ASSESSED_BOTH / NOT_ASSESSED_CODE_HEALTH_ONLY
4. Categorise divergence:
   - **Real code-health bug** (fix in code-health)
   - **Acceptable difference** (document; e.g., codebase-assess is heavier so
     surfaces more findings on the same primitive)
   - **Intentional difference** (code-health takes a different angle by
     design)

## Parity target

≥ 95% MATCH rate per target. NOT_ASSESSED counts as MATCH when both report
the same NOT_ASSESSED reason (e.g., "Semgrep wrapper not yet built").

## Current state (Phase 4 iteration 1 — pre-wrapper)

Cross-validation cannot meaningfully run until the per-tool wrappers are
built (Phase 2 iteration 2+). Current code-health output for most
primitives is NOT_ASSESSED; codebase-assess produces real findings via
Semgrep / Gitleaks / Trivy / etc. The divergence is structural (wrapper-
pending), not bug-driven.

**Phase 4 framework deliverable (this iteration):**

- Comparison script skeleton (`compare.py`) — reads both outputs + emits
  divergence report
- Synthetic fixture directory (`synthetic_fixture/`) — hand-crafted code
  exercising each primitive (PASS case + CRITICAL case per primitive)
- Expected-divergence ledger (`expected_divergence.md`) — for each
  primitive, current status + revisit trigger
- Real-target run scripts (`run_marketplace.sh`, `run_platform.sh`) —
  invoke both tools on the agents marketplace + platform repo

**Phase 4 iteration 2 deliverable (post-wrapper-build):**

- Run comparison against this marketplace; record parity rate
- Run against platform repo; record parity rate
- Update expected_divergence.md with measured rates + per-primitive notes
- Target ≥ 95% MATCH; below threshold = follow-up work in iteration 3

## Targets

- **This marketplace (`agents`)** — primary; smallest + best-understood
- **Synthetic fixture (built in iteration 2)** — exercises every primitive
- **Platform repo (`/Users/iain/Documents/repos/platform`)** — real-world
  comparison

## Comparison script (skeleton)

See `compare.py` — currently a stub with the divergence-categorisation
algorithm. Wires up once the per-tool wrappers exist + the two outputs
have comparable shape.

## What "≥ 95% parity" means

- 95% of primitives produce the same status (PASS / ADVISORY / CONCERN /
  CRITICAL / HYPOTHESIS / NOT_ASSESSED) in both tools
- Of the 5% that diverge: each divergence is categorised + documented
- code-health's NOT_ASSESSED count is allowed to be lower than codebase-
  assess's (means more primitives are wired); the reverse (more NOT_ASSESSED
  in code-health) means wrappers are still pending and is also acceptable
  with a revisit trigger

## What this does NOT measure

- Performance parity (code-health is intended to be faster ambient
  monitoring; codebase-assess is the canonical heavy audit until Phase 5
  retirement)
- Output format parity (code-health emits CHECKUP.md + tier envelopes;
  codebase-assess emits viability-report-{TIMESTAMP}.md — different shapes
  by design)
- Cross-primitive chain detection (codebase-assess Cycle 3; code-health's
  equivalent is `_lib/chains.py` — flagged NEW in the orchestrator)
