# VERIFICATION_REPORT — ux-designer (add-agent v0.2.0, greenfield)

**Verdict: PASS.**
**Tier:** STANDARD + founder-facing perspectives. **Audience:** founder-facing, dual-register. **Mode:** greenfield.

---

## Gate 1 — Find

- **BRIEF_PACK / prior-art:** 7 existing agents checked (context-cartographer, requirements-analyst, engineering-architect, executor, security-reviewer, orchestrator, sulis). **No existing agent owns the visual contract / UX surface** — it is produced *inline* by engineering-architect (draft-architecture step 3.5b) as a sub-task. CC verdict: **VALIDATED** (7 independent agents checked; none own the surface-design role).
- **Dispatch-trigger collision:** none. "visual contract / user-facing surface / mockup / sign-off" does not overlap any existing agent's trigger (architect = system; analyst = requirements; executor = build).
- **Could this be a skill?** **NO.** It needs its own conversational context (the iterative founder sign-off dialogue + Mobbin probe + mockup iteration), its own role (surface specialist), and is dispatched like requirements-analyst. The UI *skills* (design-system, honest:build-ui) are tools a surface specialist uses, not the facilitating role. Justification recorded.
- **Primitives (5, fan-out ≤7, depth 1):** inspiration probe · token/visual selection · experience+a11y · mockup production · founder sign-off. Independent + falsifiable; provenance = extracted from UX_VISUAL_DESIGN_STANDARD's four layers + #45.
- **Sub-step 1c (Specialist Boundary):** N/A — **specialist agent, not a coordinator** (it is dispatched, does not dispatch). `delegation: null`, `routes_to: []`.
- **Scope addition (founder request 2026-06-03):** the agent also owns **visual design at the system level** — when no design system/language exists it establishes one (step 0: Identity → Visual → three-tier tokens, per UXD-01/02/04/05) OR asks the founder which to use (identity/brand is founder-owned). Primitive count 5 → **6** (+ design-language establishment). It honours all four platform UX standards: WCAG-AA (UXD-07), agentic-interface (UXD-10), **cognitive-load (UXD-16 — newly added to the sulis standard, CL-01..06)**, and the design-lifecycle establishment conventions (UXD-01/02/04/05). Re-validated: body 238 lines (≤300), suite 1747 green, route/agent validation green.

## Gate 2 — Scope Lock

name `ux-designer` · plugin `sulis` · audience **founder-facing** · model `inherit` · tools `[Read, Write, Edit, Bash, WebFetch, WebSearch]` (least-privilege; + Mobbin MCP when connected) · `user_invocable: true` · register **dual** (`founder_mode: default`; `technical_mode: markdown_with_paths`). Standards phased (UX_VISUAL_DESIGN + CONTRACT_FIRST + CRITICAL_THINKING in processing; TONE + COACHING + AAF in output). Tier STANDARD. Top gotchas (≤7): token-invention, font-load (L-13), Mobbin visual-copy (UXD-15), sign-off-without-founder-yes, register-leak, jargon-in-review. `context_sources` populated (4 standards + design-instance + founder-english). "Could this be a skill?" = NO (recorded above).

## Gate 3 — Generate

`plugins/sulis/agents/ux-designer.md` parses (valid YAML frontmatter). Pyramid: leads with `## Role`. All Gate-2 frontmatter blocks present. **Body density:** ~210 lines — within STANDARD target (≤300). Every operational section carries a `> Standards:` citation header; no standard restated (cite-don't-restate honoured). Linguistic audit: zero forbidden-vocabulary terms; preferred vocabulary used. Founder-mode + technical-mode examples both present (the sign-off prose + the raw contract block).

## Gate 4 — Evaluate (spiral, STANDARD + founder-facing)

| Dimension | Score | Threshold | Pass |
|---|---|---|---|
| ACCA (accurate/complete/consistent/actionable) | 5/5 | 3 | ✓ |
| Evidence grounding | 4/5 | 3 | ✓ |
| Structural coherence (MECE role/workflow/output) | 5/5 | 3 | ✓ |
| Honest uncertainty | 4/5 | 3 | ✓ |
| Codebase Referential Integrity | 5/5 | 5 | ✓ |
| **Coaching Delivery** (founder-mode sign-off) | 7/7 | 6/7 | ✓ |
| **Tone Conformance** | 7/7 | 6/7 | ✓ |
| **Register Switch Correctness** | 19/20 | 18/20 | ✓ |
| **Body Density Conformance** | 4/4 | 3/4 | ✓ |

**Referential Integrity:** all cited paths resolve — UX_VISUAL_DESIGN_STANDARD.md, CONTRACT_FIRST_STANDARD.md, COACHING_STANDARD.md, TONE_STANDARD.md, founder-english.md, audience-adapted-framing-standard.md (verified on disk). Dispatched-by `draft-architecture` + the `kind: contract` visual-contract WP from `plan-work` both exist. Mobbin MCP tool named with availability-gating (no hard dependency).

## Gate 5 — Adversarial Review

- **MUC-A1 Prescriptive leak — PREVENTED.** Sign-off uses questions over statements (COACHING cited at step 5); founder-mode example invites calibration.
- **MUC-A2 Banned vocabulary — PREVENTED.** Linguistic audit clean; TONE cited.
- **MUC-A3 Defensive-triggering phrasing — PREVENTED.** Structural framing in the example ("does the empty checkout match…" not "your screen is missing…").
- **MUC-A4 Missing commercial outcome — PREVENTED.** Founder-mode anchors on what the user sees/does, not "mockup produced".
- **MUC-V1 Sign-off-without-founder-yes (surface-specific) — PREVENTED.** Body states `signed_off_at` is only set after a real founder yes; the #45 toolchain gate is the structural backstop (can't flip the WP to done otherwise).
- **MUC-R1 Technical-mode leaks into founder-mode — PREVENTED.** Register flag; founder-mode default; example shows plain English.
- **MUC-R2 Founder-mode drops signal — PREVENTED.** Load-bearing paths (mockup file, WP id) surfaced in BOTH registers (stated explicitly).
- **MUC-R3 Switch ambiguity — PREVENTED.** "more detail" defaults to deeper founder-mode; technical-mode only on explicit trigger.
- **MUC-F1 Operator-jargon leak — PREVENTED.** FE-06 scan cited; "empty state" not "zero-data variant".
- **MUC-F6 Stubbed-vs-active blur — PREVENTED.** L-13 (fonts must load) prevents a dead mockup reading as live brand.
- **Over/under-dispatch — OPEN_RISK (low).** Description could match a pure-copy/content task that isn't really a surface. *revisit_by:* first 3 mis-dispatches OR Q3 2026. Workaround: founder redirects to requirements-analyst/build-content.
- **Tool leakage — PREVENTED.** Body uses only declared tools; Mobbin MCP gated on availability, not assumed.

All ≥3 required categories addressed; all PREVENTED or OPEN_RISK with revisit-trigger.
