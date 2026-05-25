---
name: code-health
description: Use when the founder wants to know if everything is OK — runs a comprehensive code-health check across all 7 tiers (Exists / Safe / Works / Survives / Understandable / Evolves / Polished) and produces one prioritised report covering 25 primitives across security / data protection / code quality / supply chain / infrastructure. Default mode is "deep" — dispatches 7 parallel agents for LLM-mediated per-tier interpretation (NOT_APPLICABLE framing, finding re-routing, contextual judgment). Use --mode fast for CI / cron (subprocess-only, zero tokens). Use --mode audited for production-readiness reviews (deep + Independence Check). Read-only; never modifies code.
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD]
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions:
    - name: "Tier MECE Coverage"
      threshold: ">= 4/5"
      standard_reference: "plugins/sulis/skills/code-health/references/tier-registry.md MECE footer"
      scorer: generating_agent
      evidence_required: "25 of 25 codebase-assess primitives map to exactly one tier; no orphans; Maslow ordering holds"
    - name: "Independence Check via fresh-context dispatch (Audited mode)"
      threshold: ">= 3/5"
      standard_reference: "SPIRAL_TEMPLATES.md HEAVY_TIER_DEFAULT Independence Check"
      scorer: external_sub_agent
      evidence_required: "In Audited mode, one tier is re-dispatched as an independent Agent (Explore subagent_type, fresh context, no shared reasoning); divergence flagged"
related_skills:
  - relationship: depends_on
    skill: check-build
  - relationship: depends_on
    skill: check-security
  - relationship: depends_on
    skill: check-tests
  - relationship: depends_on
    skill: check-reliability
  - relationship: depends_on
    skill: check-readability
  - relationship: depends_on
    skill: check-maintainability
  - relationship: depends_on
    skill: check-polish
  - relationship: depends_on
    skill: _lib/baseline
  - relationship: depends_on
    skill: _lib/scope
---

# Code Health

## Conclusion (Pyramid)

The one comprehensive code-health check. Walks all 7 tiers; runs them in one of three modes; produces a single tiered CHECKUP.md. All 7 tiers are wired (since v0.16.0) and tool-integrated (since v0.20.0); cross-validation against `codebase-assess` shows 100% primitive-level parity (v0.23.0+; see `tests/cross_validation/expected_divergence.md`).

The audit is read-only. It NEVER modifies code. Findings include rename and refactor suggestions; they are *advisory text only*.

## The seven tiers

All wired (since v0.16.0); all tool-integrated (since v0.20.0):

| Tier | Founder question | Tool stack |
|---|---|---|
| 1 Exists | Does it build? Manifest hygiene? Container security? Deploy secrets? | builder + hadolint + Trivy + Gitleaks |
| 2 Safe | Could anyone be harmed? (SEC-01..07, DAT-01..05, SC-01..04) | Semgrep + Gitleaks + Trivy + testssl + curl_probe |
| 3 Works | Do the tests pass? Test coverage quality? | per-framework + pytest-cov / vitest / jest |
| 4 Survives | Does it handle failure gracefully? Verbose-error / debug mode? Audit logging? | regex + Semgrep + hypothesis |
| 5 Understandable | Can a new person read it? Cyclomatic complexity? Duplication? | regex + lizard + jscpd |
| 6 Evolves | Can we change it without breaking things? Review practices? | regex + git-log + hypothesis |
| 7 Polished | Documentation / tech-debt density / file hygiene | regex (canonical CQ-04 owner) |

Tier registry lives at `references/tier-registry.md` — adding a wired tier
is a registry update + a tier-skill, not a SKILL.md rewrite.

## Three invocation modes

### Deep mode (DEFAULT — founder-interactive)

Claude (the session running `/sulis:code-health`) dispatches 7 `Agent` calls in parallel — one per tier. Each agent runs in **fresh context** with its own subagent_type, invokes its tier's scanner script, applies contextual interpretation lenses (NOT_APPLICABLE-for-non-web-repos, MUC-F4 cap, test-fixture recognition, etc.), and returns a structured JSON + founder-mode markdown. Claude aggregates the 7 returns into a single CHECKUP.md.

Unlocks: NOT_APPLICABLE framing for non-web repos / re-routing of findings to their semantically-right primitive / per-tier MUC-F4 overwhelm cap / test-fixture identification without allowlist entries.

Cost: ~50k tokens per code-health run (7 agents × ~5–10k each). The founder-facing improvement is worth the cost for interactive runs — without contextual interpretation, founders see misleading subprocess output (PASS on SEC-01 for a CLI-only repo, etc.).

### Audited mode

Deep mode + a second-pass Independence Check per `SPIRAL_TEMPLATES.md` HEAVY_TIER_DEFAULT. One of the 7 tier responses is re-dispatched as a fresh-context `Agent(subagent_type=Explore, ...)` call with NO access to the prior agent's reasoning. Divergence between the two runs flagged in the CHECKUP.

Unlocks: SPIRAL_TEMPLATES HEAVY-tier compliance — the Independence Check requirement is satisfied for free by the dispatched-agent fresh-context property.

Cost: ~55k tokens (deep mode + 1 extra agent).

### Fast mode (opt-in — CI / cron / ambient monitoring)

`orchestrator.py --mode fast` shells out to each `check-*/scripts/*.py`. Zero tokens. Mechanical. Deterministic. **Explicitly opt-in** since v0.26.0 — use when running without Claude in the loop (CI pipelines, cron jobs, ambient monitoring dashboards). Subprocess output is honest but lacks contextual judgment — founders running ad-hoc should use deep mode.

## Two output modes (orthogonal to invocation mode)

- **Founder mode (default).** Tiered report in plain English with FE-06 applied. Per-tier traffic-light. Drill-down only for failed tiers. No internal IDs in chrome.
- **Operator mode (`--raw`).** Tiered JSON envelope with per-tier raw findings. For piping or for engineers wanting machine-readable output.

## Scope auto-detection

PR-scope (local diff vs auto-detected base branch) or codebase-scope. Override with `--scope`, `--base-branch`, or `--pr-number`. The orchestrator (fast mode) and the per-tier agents (deep/audited) all honour the resolved scope.

## When invoked — DEEP mode (DEFAULT)

The orchestrator can't dispatch Agents (it's pure Python). The dispatch logic lives here, executed by Claude in the session running `/sulis:code-health`.

1. **Resolve scope.** Auto-detect PR vs codebase. Echo it.

2. **Read the agent prompt templates** under `agent_prompts/`. There are 7 of them, one per tier.

3. **Dispatch 7 Agent calls in a single message** (parallel — same primitive as the cross-validation runner pattern):

   ```
   Agent(check-build,           subagent_type=Explore,        prompt=agent_prompts/check-build.md)
   Agent(check-security,        subagent_type=general-purpose, prompt=agent_prompts/check-security.md)
   Agent(check-tests,           subagent_type=general-purpose, prompt=agent_prompts/check-tests.md)
   Agent(check-reliability,     subagent_type=Explore,        prompt=agent_prompts/check-reliability.md)
   Agent(check-readability,     subagent_type=Explore,        prompt=agent_prompts/check-readability.md)
   Agent(check-maintainability, subagent_type=Explore,        prompt=agent_prompts/check-maintainability.md)
   Agent(check-polish,          subagent_type=Explore,        prompt=agent_prompts/check-polish.md)
   ```

   Substitute `{repo_root}`, `{scope}`, and `{project}` into each prompt template before dispatching.

4. **Each agent returns a structured response.** Per the prompt template contract, each agent emits:
   - A `## Per-tier verdict` line: `PASS | NEEDS_ATTENTION | FAILED | NOT_YET_CHECKED`
   - A `## Findings` list (file:line — severity — message), capped per the MUC-F4 presentation cap (≤ 10 per category)
   - A `## Primitive coverage` table mapping each primitive to PASS / ADVISORY / CONCERN / CRITICAL / HYPOTHESIS / NOT_ASSESSED / NOT_APPLICABLE
   - A `## Founder-mode summary` paragraph (1-3 sentences for the CHECKUP)

5. **Aggregate.** Invoke `scripts/aggregator.py` with the 7 agent responses as `--tier-response <path>` args; it merges into a single CHECKUP.md.

6. **Present the CHECKUP** (template below).

## When invoked — FAST mode (opt-in; CI / cron)

Invoke when running without Claude in the loop. Honest mechanical output; no contextual interpretation.

1. **Resolve scope.** Auto-detect PR vs codebase. Echo it.
2. **Run the orchestrator.**
   ```bash
   python3 plugins/sulis/skills/code-health/scripts/orchestrator.py \
     --mode fast \
     [--scope auto|pr|codebase] \
     [--pr-number N] \
     [--raw]
   ```
3. **Translate to founder English** (if a human will read it). For each tier render per-tier verdict + drill-down for non-passing.
4. **Present the CHECKUP** per the founder-mode template below.

Note: fast mode output may show PASS on primitives that deep mode would mark NOT_APPLICABLE (e.g., SEC-01 on a CLI-only repo). This is acceptable for mechanical CI checks; not acceptable for founder-interactive runs.

## When invoked — AUDITED mode

Like deep mode, plus an Independence Check second pass per `SPIRAL_TEMPLATES.md` HEAVY tier:

1. Run deep mode (steps 1-5 above).

2. **Pick the highest-stakes tier** from the deep-mode response (typically tier 2 Safe, since security findings carry highest founder-trust weight).

3. **Re-dispatch the same tier as a fresh-context Independence Check:**
   ```
   Agent(<same tier>, subagent_type=Explore, prompt=agent_prompts/independence-check.md)
   ```

   `independence-check.md` instructs the sub-agent to score the original agent's findings against the standards, with explicit exclusion: NO access to the original agent's reasoning chain; only the SKILL.md + standards + the raw scanner output.

4. **Compare** the original tier-2 response and the Independence Check's verdict. Flag divergence in the CHECKUP under `## Independence Check`.

5. **Aggregate + present** — the CHECKUP gains an Independence Check section.

## Founder-mode CHECKUP template

```
🩺 Code Health — {scope description}
Mode: {fast | deep | audited}

At a glance:
  Tier 1 — Exists:         ✅ Clear
  Tier 2 — Safe:           🟡 needs attention (3 findings)
  Tier 3 — Works:          ⏸ no test framework
  Tier 4 — Survives:       ✅ Clear
  Tier 5 — Understandable: 🟡 needs attention (58 complexity hotspots)
  Tier 6 — Evolves:        ⚠ things to verify (1 hypothesis)
  Tier 7 — Polished:       ✅ Clear

What needs your attention:

🟡 Tier 2 — Safe
  Three security concerns surfaced (semgrep deep scan):
  1. `plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py:40` — XXE
     vulnerability (use defusedxml instead of native xml lib)
  ...

Things to verify with the team:

  - {CQ-05 hypothesis}: Review practices likely informal:
    100% direct-to-main commits last 90 days; no PR template.
    Confidence: SUPPORTED.

What's not yet checked:

  Tier 3 — no test framework detected at repo root.
```

## Handle shortcuts

- **Safe shortcuts:** `[N] drill into tier N findings`, `[N] open file at finding`. Echo-before-act.
- **No fix shortcut.** This skill never modifies code (see Gotcha #4).

## Gotchas

- **Mode selection matters.** Deep is the default for founder-interactive runs where contextual interpretation matters. Fast is opt-in for ambient monitoring (CI / cron). Audited is for production-readiness reviews + SPIRAL_TEMPLATES HEAVY compliance. Don't run audited per commit — it's a deliberate review action.
- **The orchestrator can't dispatch agents.** Deep/audited mode logic lives in this SKILL.md (Claude executes); `orchestrator.py` is the fast-mode default + the tool the per-tier agents call. Same pattern as `sulis-execution`'s run-all skill.
- **Stubbed tiers must look different from passing tiers.** Founder glancing at 6 ✅ might think everything passed — but some are "didn't run" (e.g., CQ-02 when no test framework). Use `⏸ no test framework` or `⏳ not yet checked` distinct from `✅ Clear`.
- **Don't fabricate verdicts for NOT_ASSESSED primitives.** Honest "tool unavailable" beats false-green.
- **Founder might assume code-health can fix things.** This skill composes read-only audits; it never modifies code. Suggestions are advisory text only.
- **Tier names are founder-vocab; operator IDs must stay hidden.** Primitive IDs (SEC-07, CQ-01) must NEVER appear in founder mode. Per-tier agents handle translation.

## Vocabulary

- **code-health** — the umbrella property this skill measures.
- **tier** — a Maslow-for-code level (1 through 7).
- **checkup** — the report this skill produces.
- **fast / deep / audited mode** — invocation modes; see "Three invocation modes" above.
- **Independence Check** — SPIRAL_TEMPLATES HEAVY tier requirement; satisfied in audited mode by re-dispatching a tier as a fresh-context agent.
- **NOT_APPLICABLE** — contextual judgment from deep/audited mode that a primitive doesn't apply to this codebase shape (e.g., SEC-01 on a CLI-only repo). Distinct from NOT_ASSESSED (tool unavailable).

## When to invoke this skill

- Founder asks "is everything OK?", "give me a comprehensive check", "is my code in good shape?", "is the codebase healthy?"
- Production-readiness review or external audit preparation (use AUDITED mode)
- CI / cron ambient monitoring (use FAST mode)

## When NOT to invoke this skill

- Founder asks specifically about one tier — use that tier's skill directly (`/sulis:check-security`, etc.)
- Founder wants to fix something — this skill suggests; doesn't act
- Operator wants per-tier raw JSON — invoke the individual `check-*` scripts with `--raw`
