---
title: Tool surface is a second walk pass with the generalised binding-EXISTS bar
status: accepted
kind: adr
---

# ADR-003 — Tool surface is a second walk pass with the generalised binding-EXISTS bar

## Context

FR-07 (retained) walks the UI surface at `draft-architecture/SKILL.md` step
8.5: each hop classified EXISTS (file+function) / planned-WP / GAP, with a
sharper bar for host-rendered hops (binding both sides + real-host round-trip).
FR-08 adds a second surface — the API/SDK/MCP tool surface. FR-09 requires a
tool hop to be EXISTS only if BOTH the handler AND its ServiceSpec binding are
cited; a serving handler without a binding is a GAP (the generalised
"looks-built-but-isn't-wired" lesson, MUC-02). FR-19 requires the tool walk to
draw its operations from the interface contract (§7.6 of the design).

The step-8.5 procedure (pull the scenario set, walk hop-by-hop, classify, write
a `## Journey Walk` table, gate on a bare GAP) already exists and is proven for
UI + host-rendered hops.

## Decision

Extend step 8.5 with a **second walk pass** producing a **second table** — the
tool-surface `## Journey Walk` — reusing the existing procedure. The tool pass:
(1) reads the interface contract section (FR-18) as the *source of operations*
to walk (FR-19); (2) for each operation, cites the handler AND its binding ⇒
EXISTS, or a planned WP ⇒ planned-WP, or neither ⇒ GAP; (3) classifies a
handler-without-binding as GAP (FR-09, NFR-S02). The binding bar is the
**generalisation** of the host-rendered bar already in step 8.5 — not a new
rule, the same "wired, not just serving" discipline applied to every tool
operation. Both tables are persisted in the document (NFR-D02). A bare GAP in
either table blocks design completion.

## Options Considered

- **Second walk pass reusing step 8.5's procedure (CHOSEN).** Minimal delta;
  the binding bar generalises an existing rule; both tables persisted; the
  exemption path (pure docs/infra) is retained from #85.
- **A separate tool-walk skill** — rejected: duplicates step 8.5's pull /
  classify / gate logic; two procedures drift; the founder-facing gate would
  fire from two places.
- **A weaker tool-EXISTS bar (handler serving is enough)** — rejected:
  reintroduces exactly the false-EXISTS bypass (MUC-02) the change exists to
  close; violates FR-09 / NFR-S02.

## Consequences

- **Positive:** the machine consumer's path gets the same outside-in proof the
  human's does; false EXISTS is structurally caught; the binding bar is one
  rule, generalised, not two. Bounded extra cost (NFR-S01: ≤ +1 turn).
- **Negative:** step 8.5 grows; the agent must now identify the machine
  consumer's path and the contract operations. Mitigated by FR-19 (the contract
  *is* the operation source — the agent doesn't invent the path).
- **Neutral:** the host-rendered bar (mcp-ui-surface-patterns.md) is unchanged;
  the tool bar references it as its generalisation.
