# Sizing — harden-embed-safe-tools (embedding L1+L2 into the governed action-surface)

> Computed at draft-architecture. Subsequent skills read this rather than
> recompute. Refresh if SPEC scenarios (SC-E1..E9) or scope (D1–D8) change.
> Change: CH-522P6P · `harden` · base SHA 2da4d842.

## Inputs

Brownfield-equivalence basis. This change wraps already-shipped libraries
(`_safe_fetch`, `_file_tools`, `_file_scope`) into denyable tool identities +
a governance hook, and adds ONE resolver extension. Phases 1–3 are buildable
backend; Phases 4–5 are doc/config. The decisions (D1–D8) are LOCKED in the
Working Set — this is build-only sizing, not a decision count.

## sFPC (simplified Function Point Count)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 2 | the write-roots resolver output (the shared root-set); the hook decomposition state (compound-Bash sub-command list) |
| EIF (external interfaces) | 1 | the Claude Code harness (PreToolUse stdin/stdout contract + `.mcp.json` registration + permission/sandbox config) |
| EI (mutating ops) | 4 | the 4 scoped file ops exposed as MCP (`read`/`write`/`move`/`remove`) |
| EO (deriving ops) | 4 | write-roots resolution; hook path-scope decision; hook Bash-family decision; compound-Bash decomposition |
| EQ (retrieving ops) | 2 | `safe_fetch` + `safe_search` exposed as MCP (read-back over the existing gateway) |
| **sFPC** | **13** | → tier **M** band (11–30) |

## ASR count (architecturally significant requirements)

| Source | Count | Items |
|---|---|---|
| NFRs | 3 | single-source-of-truth resolver (no L2/L3 drift); narrowest-root; canonical-path resolution (`/tmp`→`/private/tmp`) |
| Integrations | 3 | agent → MCP server; harness PreToolUse → hook; resolver → {file-tools, sandbox recipe} |
| In-scope scenarios as ASRs | 6 | SC-E1..E6 (verifiable now) |
| Deferred/attested scenarios | 3 | SC-E7..E9 (labelled, half-testable-now) |
| Cross-cutting policies | 2 | enforcement-locus honesty-labelling (every rule names its locus + threat-scope); fail-closed default (hook + resolver) |
| **ASR** | **17** | → tier **L** band (16–40) |

## Tier

**M→L boundary.** sFPC 13 → M; ASR 17 → low-L. **Take M** (the higher-tier
rule yields L, but the ASR count is inflated by honesty-labelling +
deferred-scenario bookkeeping that ride existing decisions rather than new
design; the build surface is genuinely M-sized — three small components
wrapping shipped code). One bounded context (the agent execution boundary,
continued from CH-E22SX6). Three independent sub-components buildable in
parallel (MCP server, hook, resolver) — resolver feeds the hook + file-tools.

## Per-pillar coverage (from existing code + prior TDD)

| Pillar | Coverage | Consequence for the TDD |
|---|---|---|
| **Form** | **Partial** — the L1 ports (`FetchGateway`/`OutboundFetcher`) + L2 resolver (`_file_scope`) already exist and are the seams this change wraps. New: the MCP-server adapter (an EXPAND-Create adapter over the existing tool functions), the hook module, the resolver extension. | Form section names ONLY the new components + cites the prior TDD for the seams it builds on. No re-derivation of hexagonal. |
| **Armor** | **Partial** — secret-scrub + fail-closed scope already in the libraries. New armor: the hook as a deterministic deny-gate (locus ii); permission deny-rules; the sandbox recipe (locus iii). | Armor section is the heart of this change — enforcement-locus tiering, honesty-labelling, the compound-Bash decomposition. |
| **Proof** | **Good** — existing contract + scenario tests for L1/L2 (`test_safe_fetch_*`, `test_file_*`). New: MCP-server contract test (tools enumerate), hook-invocation tests, resolver single-source test, the SC-E1..E6 automated scenario suite. | Proof section names the new test artifacts + the honest deferral of SC-E7..E9 halves. |

## Length target

Tier M → ~150–250 line TDD. Form is short (mostly references to the prior
TDD's seams); Armor + Proof carry the weight (the genuinely new design).

## Circuit breakers

None expected to fire. ADR count target ≤ 6 for tier M; this change produces
**4** (MCP file-tool shape; MCP packaging; hook decomposition strategy;
resolver shared-output shape). Each is a decision affecting >1 component or
rejecting a viable alternative AND not covered by the prior change's ADRs.

## User-confirmation record

Tier **M**, confirmed by the build scope handed in the change brief (Phases
1–3 buildable, 4–5 doc/config). Override path: if the resolver extension or
the hook grows past one module each, re-tier to L and re-decompose.
