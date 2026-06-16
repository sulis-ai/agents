---
id: WP-005
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
title: governed-action-surface standard (D8 2-axis criterion) + locus-honesty test + quality nudge
kind: docs
primitive: document
group: reinforce
status: pending
dependsOn: [WP-003, WP-004]
scenarios: [SC-E6]
verification:
  adapter: docs
  na: false
  artifact: "plugins/sulis/scripts/tests/unit/test_locus_honesty.py"
token_cost: { input: ~9k, output: ~8k }
---

# WP-005 — governed-action-surface standard + locus-honesty test + quality nudge

# (Phase 5)

## Context

TDD §Armor (enforcement-locus tiering) + D8 (the 2-axis criterion is broader
than this change — graduate it to a standard) + SPEC §Phase 5. This WP writes
the durable home of the D8 criterion, adds the test that asserts every rule
honours its locus (SC-E6), and adds the prose quality nudge (locus i — quality
only). Depends on WP-003 + WP-004 (the rules + recipe it describes + tests).

## Contract

- **New:** `plugins/sulis/references/.../governed-action-surface-standard.md`
  — the D8 criterion as a reference standard:
  - **The 2 axes:** invocation-substrate (raw-Bash / CLI / MCP) × governance
    (ungoverned / hook-governed / permission-denied). Governance ≠ MCP — a
    PreToolUse hook governs CLIs without converting them.
  - **MCP criterion (narrow):** MCP-ify iff (typed/structured contract OR
    denyable identity at a trust boundary) AND no selection-surface bloat.
    Default = CLI. Binding constraint = selection accuracy, not token cost.
  - **The honesty-labelling rule:** every embedded rule names exactly one
    enforcement-locus (i/ii/iii) + threat-scope (accidental-now / adversarial-
    deferred); a rule must not claim a locus it does not hold.
  - Worked classification: MCP now = safe-fetch + scoped-file ONLY; ~55
    sulis-*/wpx-* stay CLI; one governance hook; NEVER 1:1 the 21 emit-*.
- **New:** `tests/unit/test_locus_honesty.py` — parses the standard + the
  shipped config/hook + the recipe; asserts each rule carries a locus +
  threat-scope and none over-claims (e.g. no prose rule labelled locus-ii; no
  MCP-identity rule labelled "enforced"). **SC-E6.**
- **Modified:** agent defs / relevant skills — add the prose quality nudge
  "prefer safe_fetch for clean, low-token output" (locus i — explicitly a
  quality preference, a bypass costs polish not safety; D4).

## Definition of Done

### Red
- [ ] `test_locus_honesty.py::test_every_rule_labelled` — over the standard +
      config + recipe, every rule has {locus, threat-scope}. **Fails** (no
      standard yet).
- [ ] `::test_no_overclaim` — no locus-i (prose) rule claims harness/OS
      enforcement; the MCP-identity rule is labelled necessary-not-sufficient;
      the sandbox recipe is labelled the adversarial-subprocess owner. **SC-E6.**

### Green
- [ ] Write the standard (CP-01..05: cite the criterion as the durable
      convention, not novelty). Add the quality nudge. All Red pass. **SC-E6
      satisfied.**

### Blue
- [ ] The standard references — does not restate — the verified harness
      contracts (link the hooks/permissions/sandboxing docs) and the prior
      change's L1/L2 TDD. Confirm the nudge is unambiguously locus-i (no
      safety claim). Cross-link the WP-004 recipe.
