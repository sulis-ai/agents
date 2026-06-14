---
id: WP-004
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
title: sandbox-enable recipe — document the locus-iii backstop consuming the resolver roots
kind: docs
primitive: document
group: reinforce
status: pending
dependsOn: [WP-002]
blocks: []
scenarios: [SC-E8, SC-E9]
verification:
  adapter: docs
  na: true
  justification: "Doc/config WP — no runtime surface. The recipe is a documented settings.json template + the sandbox_write_roots consumer instruction; correctness is asserted by SC-E5's single-source test (WP-002) and the SC-E8/E9 deferred-attested labels. No code to drive."
token_cost: { input: ~7k, output: ~6k }
---

# WP-004 — sandbox-enable recipe (Phase 4, doc/config)

## Context

TDD §Armor (Layer 3) + ADR-004 (sandbox emit) + the verified sandboxing docs.
The OS backstop (locus iii) — the **only** layer that catches subprocess
bypass. Sulis does not build a sandbox (Claude Code ships Seatbelt/bubblewrap);
this WP documents enabling + configuring it, consuming the WP-002 resolver
output so the writable paths never drift from the file-tools scope. Depends on
WP-002 (the `sandbox_write_roots` emit it instructs the operator to paste).

## Contract

- **New:** a recipe doc (under the plugin's docs / the standard from WP-005)
  giving the `settings.json` `sandbox` block:
  - `sandbox.enabled: true`.
  - `sandbox.filesystem.allowWrite` = the `sandbox_write_roots(...)` output
    (ADR-004 path-prefix form).
  - `sandbox.filesystem.denyRead` = creds (`~/.aws`, `~/.ssh`) — the default
    read policy allows these unless denied (verified in docs).
  - `sandbox.network.allowedDomains` = the proxy egress host **only**.
  - consumer-managed `failIfUnavailable: true` + `allowUnsandboxedCommands: false`
    for strict mode (managed-settings note: only a consumer can make it
    operator-proof — SC-E9).
- Honesty labels: the proxy does **not** inspect TLS → broad `allowedDomains`
  permits domain-fronting exfil; **GAP-β deferred**, named. The recipe carries
  its enforcement-locus (iii) + threat-scope (adversarial-subprocess, closed
  only when enabled).

## Definition of Done

### Red
- [ ] A doc-section assertion (folded into `test_locus_honesty.py`, WP-005)
      checks the recipe section exists + carries its locus + threat-scope +
      the GAP-β / TLS caveat + the "consumer-managed = operator-proof" note.
      **Fails** until the recipe is written.

### Green
- [ ] Write the recipe; it references `sandbox_write_roots` as the source of
      `allowWrite` (no hand-maintained second list). SC-E8 (real session inside
      the sandbox) + SC-E9 (operator-proof) are **labelled deferred-attested**
      — the recipe states exactly what an attested run must show and who owns
      it; it does not claim them green.

### Blue
- [ ] Cross-link from the standard (WP-005) and the prior change's L3 deferral
      note. Confirm no settings value is hand-duplicated from the resolver.
