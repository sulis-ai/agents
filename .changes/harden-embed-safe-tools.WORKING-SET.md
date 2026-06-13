# Working Set — harden-embed-safe-tools

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Embed shipped L1 (safe-fetch proxy) + L2 (scoped file-tools) into how the agent operates so they are actually used (not bypassed by raw WebFetch/Read/Write/Bash) — via harness enforcement, not prose. Decide the embedding approach + exactly how far the Claude Code harness can enforce before/around the OS sandbox.

## 2. Current best solution  (→ Design)
A **tiered stack keyed to enforcement-locus** (NOT a single convention-vs-enforcement pick — that fork is a false trichotomy). Enforcement-locus is the primitive: every rule is adjudicated at exactly one of (i) **model judgment** (prose — advisory, bypassable), (ii) **Claude Code's tool adjudicator** (permission deny-rules + PreToolUse hooks — deterministic + hard-blocking for *recognized direct tool calls*; model-unbypassable under managed settings), (iii) **OS kernel** (the shipped Seatbelt/bubblewrap sandbox — covers *all* processes incl. spawned subprocesses). The plan, cheapest→strongest:
1. **Permission deny-rules** block raw network/file tools (`WebFetch`, `Bash(curl…/wget…)`); allow only the safe-fetch tool. (Locus ii. Note: arg-matching on Bash is fragile per Anthropic docs — block the *tools*, lean on the sandbox for the rest.)
2. **PreToolUse hook = the #130-grade structural guard:** match `Write|Edit|Bash`, read `tool_input.file_path`/`command`, run #130's `within_change_scope`, return `deny`/exit 2 for out-of-scope. Hard-blocks; overrides allow-rules. (Locus ii.)
3. **Enable the SHIPPED OS sandbox** (`sandbox.enabled`, narrow `allowedDomains`, `denyRead` creds; consumer-side managed `failIfUnavailable`+`allowUnsandboxedCommands:false`). Only this catches subprocess bypass (`python -c 'open()'`, obfuscated curl). (Locus iii.)
4. **Prose (convention) ONLY for quality** — "prefer safe-fetch for clean/low-token output" in sulis.md/agent-defs/skills. A bypass there costs polish, not safety.
Discipline that prevents false-safety: **every embedded rule is labelled by its enforcement-locus + threat-scope** (accidental-closed-now vs adversarial-deferred). Grounded in 4 critical-thinking spirals: 01KW3BZNS… → 01KTZRTN0… → 01KTZTCSP2… → 01KV0G2GCKXZR82C03WHPA17XD.

## 3. Decisions in flight  (→ Decision; status: proposed)
- **D1 — Embed via enforcement-locus tiering, not a single approach.** Options: pure convention (A) / harness-enforced (C) / wait-for-OS-sandbox (B). Chosen: tiered mix keyed to where each rule is adjudicated. Status: **proposed (lock pending the build).**
- **D2 — L2 embeds as a PreToolUse `within_change_scope` hook, not prose.** Rationale: this repo's #211 prose warning failed twice; #130 fixed it structurally. A safety rule must carry ≥ locus-(ii) backing. Status: **proposed.**
- **D3 — "L3" is mostly an ENABLE, not a BUILD.** The OS sandbox ships in Claude Code (Seatbelt/bubblewrap, macOS/Linux/WSL2). So the remaining bespoke L3 work shrinks to a TLS-aware safe-fetch-only egress proxy (GAP-β). Status: **proposed (reframes the roadmap).**
- **D4 — Convention is acceptable ONLY where bypass is a quality miss, never a safety hole.** Status: **proposed.**

## 4. Open questions / unknowns
- **Q1 (load-bearing, verify FIRST):** Are L1/L2 exposed as distinct *tool identities* so "deny raw / allow safe" is expressible? If not, embed at the agent `allowedTools`/`disallowedTools` layer instead (still locus ii). The whole plan rests on this.
- **Q2:** What managed-settings can a *consumer* realistically apply? Sulis (a plugin) ships strong defaults the *model* can't self-bypass; *operator-proof* unbypassability needs the consumer to apply managed settings + strict sandbox — Sulis can't impose that on a machine the operator administers.
- **Q3:** Exact scope of the deferred GAP-β work — a TLS-terminating, safe-fetch-only egress proxy (the sandbox's proxy does NOT do TLS inspection, so broad allowlists allow domain-fronting exfil).
- **Q4:** Can the agent disable its own hooks (`disableAllHooks`)? Closed under managed `allowManagedHooksOnly` + sandbox-denies-settings-writes; open under plain plugin/project scope (operator-controlled, not model).

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- **Pure-convention embedding (prose-only) as a safety boundary** — REJECTED. This repo's #211 prose warning failed twice before #130 replaced it structurally; instruction-only embedding leaks. Convention survives only for *quality* surfaces (D4).
- **Treating "L3" as a far-off bespoke build** — REJECTED/REFRAMED. The OS sandbox already ships in Claude Code; enabling it closes the subprocess gap now. Only the TLS-aware egress proxy is genuinely still to build.
- **Treating the shipped sandbox as a COMPLETE boundary** — REJECTED. Its proxy doesn't do TLS inspection → deliberate exfil via a *permitted* broad domain (GAP-β) survives. It closes accidental over-reach (GAP-α, the #211-shaped real threat) decisively; GAP-β stays deferred. Never claim "enforced" beyond the locus that delivers it.
- **Bash arg-matching deny-rules** (`Bash(curl <url>*)`) as the network control — REJECTED per Anthropic docs (fragile; bypassable by option-ordering/redirects/env-runners). Block the network *tools* + lean on the sandbox instead.

## 6. Working log  (append-only)
- 2026-06-13T12:56:37Z — Working Set created.
- 2026-06-13T12:57:46Z — Seeded from the 4-spiral chain: enforcement-locus tiering (deny-rules + within_change_scope PreToolUse hook + enable shipped OS sandbox; prose only for quality). L3 reframed as mostly-enable. GAP-α closed-now / GAP-β (TLS egress) deferred. First verify: L1/L2 are distinct tool identities (Q1).
