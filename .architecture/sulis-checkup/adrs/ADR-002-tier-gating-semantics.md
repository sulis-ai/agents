---
id: ADR-002
title: Tier gating semantics — hard stop at tier 1+2 critical, soft de-prioritise elsewhere
status: accepted
date: 2026-05-23
deciders: [iain, sea-architect-agent]
---

## Context

The Maslow tier ordering (1→2→3→4→5→6→7) is load-bearing: lower tiers
gate higher tiers conceptually. But the brief asks how that translates to
runtime behaviour. Three viable shapes:

1. **Hard stop at every tier failure** — any failure at tier N prevents
   tier N+1 running. Aggressive but consistent with the Maslow claim.
2. **Run everything, render in priority order** — every tier runs
   regardless; the report orders by load-bearing-ness. Permissive but
   loses the gating signal.
3. **Severity-aware hybrid** — tier N failure short-circuits tier N+1 only
   if N is below some threshold AND the finding's severity is above some
   threshold.

The brief explicitly asks: hard stop vs soft de-prioritise vs per-finding;
severity-aware; default + founder override.

## Decision

**Two-mode gating with a per-finding escape hatch:**

- **Hard stop:** triggered by `critical` severity at tier 1 (Exists) or
  tier 2 (Safe), OR by any per-finding `hard_stop: true` flag. When
  triggered, do NOT run higher tiers. Render the report with the
  failing tier at top and a `(STOPPED HERE)` marker.
- **Soft de-prioritise:** every other case. All tiers run; the report
  orders failing tiers first, then findings within each tier by severity.
- **Override:** `--check-everything` disables hard-stop; `--tier=N` runs
  only tier N.

## Options Considered

### Option 1 — Hard stop at every tier failure

**Pros:** consistent with Maslow framing. Simple to explain.

**Cons:**
- A tier 3 `partial` (e.g. "one test failure in the auth module") would
  prevent tier 4 (Survives) from running. But the founder asking "does
  my code survive failure?" doesn't need a clean tier 3 to get a useful
  answer — they need an answer about resilience.
- A tier 5 `partial` ("the function is named obscurely") would prevent
  tier 6 from running. That's absurd — naming has nothing to do with
  evolvability assessment.

**Rejected because:** tier ordering is about *load-bearing-ness* (what
fix is most important to do first), not *blocking the assessment*. A
tier-5 naming finding doesn't make a tier-6 dead-code finding invalid;
it just means the naming finding is more urgent to fix.

### Option 2 — Run everything, render in priority order (chosen for tiers 3-7)

**Pros:**
- Founder gets a complete picture from one command.
- No "I only saw a partial picture because tier 3 had one issue".
- Re-runs after fixes are cheaper because the previous run already
  collected all data.

**Cons:**
- Tier 4-7 results are noise if the project doesn't build (tier 1).
  Running `/sulis:codebase-audit` against a non-compiling codebase
  produces meaningless output.

**Accepted with the exception:** if tier 1 fails critically, the
tier-4 audit *literally cannot run* — the audit tools need a buildable
state. Same for tier 2 critical (a leaked secret means we shouldn't be
running further heavy analysis that might log paths containing the
secret). For tier 1 + tier 2 critical, hard-stop is the right call.

### Option 3 — Severity-aware hybrid (chosen for the per-finding escape)

**Pros:**
- Allows future calibration ("we learned that tier 3 `critical` should
  also hard-stop").
- Per-finding flag allows specific cases (a `medium` finding showing data
  loss is more urgent than the severity letter suggests) to opt in.

**Cons:**
- Adds a knob. Knobs accumulate.

**Accepted in narrowed form:** the per-finding `hard_stop: true` flag is
the escape hatch. It's used sparingly — only when a finding indicates
"continuing the assessment risks harm" (e.g. discovered active data
exfiltration). Source skills declare this in the finding's metadata; the
checkup graph honours it.

## Why not generalise the severity-aware mode

The temptation: "hard-stop when tier ≤ T AND severity ≥ S". This is too
clever. The Maslow claim is *categorical* — tier 2 is more load-bearing
than tier 5 because of *what each tier checks*. Critical at tier 5 (e.g.
"the entire codebase is one 5000-line file") is real but doesn't prevent
running tier 6 analysis. Critical at tier 1 makes everything else literally
impossible to verify.

Hard-coding the rule "tier 1 or tier 2, critical only, OR per-finding flag"
is the simplest expression of the categorical claim. More flexibility would
require justifying each new rule with a concrete case; we don't have those
cases yet.

## Override semantics

| Flag | Behaviour |
|---|---|
| `--check-everything` | Disable hard-stop. Tier 1 + tier 2 critical findings still appear at top of report with `(WOULD HAVE STOPPED)` tag, but all tiers run. |
| `--tier=N` | Run only tier N. Hard-stop conditions from below tier N are ignored. Use case: focused re-check after fixing a tier-2 issue. |
| (none) | Default — hard-stop at tier 1+2 critical, soft elsewhere. |

No `--no-tier=N` skip flag. A founder who wants to skip a tier without a
reason has bigger process problems than this command can solve. Findings
can be dismissed individually via the report's healing shortcuts (with a
reason recorded in `.checkup/{project}/dismissed.json`).

## Consequences

**Positive:**
- Founders see the load-bearing fix first in 95% of runs.
- A non-building project produces a focused report (fix the build, then
  re-check) instead of a noisy 7-tier wall.
- A leaked secret produces a focused report (rotate, then re-check)
  instead of getting buried under naming findings.
- Override flag exists for the "I want the full picture" case (e.g.
  before a security audit, before a release sign-off).

**Negative:**
- Founders running the checkup for the first time on a project that has
  tier 1 + tier 2 issues won't see the higher-tier findings until they
  fix lower tiers. They may interpret "tier 4 not assessed" as
  "tier 4 is clean", which it isn't.
- Mitigation: the report's at-a-glance section uses `[—] Not checked yet`
  not `[✓] Pass` for skipped tiers, explicitly marked.

**Neutral:**
- Per-finding `hard_stop` flag adds a source-skill responsibility (the
  primitive must decide whether to set it). Defaults to false unless the
  source skill explicitly opts in.
