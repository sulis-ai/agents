---
id: ADR-004
title: One write-roots resolver, two shapes — Python roots + sandbox-config emit
status: accepted
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
date: 2026-06-13
relates_to: SPEC §Phase 3, D5, D7
extends: harden-agent-execution-boundary/ADR-004   # the multi-root allowlist this builds on
grounded_in:
  - https://code.claude.com/docs/en/sandboxing      # allowWrite path prefixes; worktree .git auto-allow
---

# ADR-004 — One write-roots resolver, two shapes: Python roots + sandbox-config emit

## Context

D5/D7 require ONE config-derived resolver computing the allowed write-roots,
consumed by BOTH (a) the L2 file-tools scope check (the hook + the MCP
`scoped_file`) AND (b) the Phase-4 sandbox recipe — with **no drift** between
the two. The existing `_file_scope.resolve_allowed_roots` already computes a
canonical, narrowest-root, per-operation allowlist (`AllowedRoots`) for the
file-tools (prior change's ADR-004). What is missing:

- The **brain dir** as a writable root. The brain is moving out of the
  worktree (v0.153.0 `brain_base_dir`); the agent writes to it constantly, so
  its **resolved** path must be a writable root — but only when it is *outside*
  the worktree (the default in-worktree brain needs no extra root). Today
  `resolve_allowed_roots` does not include it.
- A **second emit shape**: the sandbox config wants `allowWrite` path strings
  (`/abs`, `~/`, `./` prefixes — NOT the `//abs` permission syntax), derived
  from the SAME roots the file-tools use.

## Decision

**Extend `_file_scope.py`** (do not fork). Two additions:

1. **`resolve_allowed_roots` gains the resolved brain root.** It calls
   `brain_base_dir(repo_root)` (the single #127 resolver — never hardcode
   `~/.sulis`). If the resolved brain path is **inside** the worktree (the
   default), it adds NO root (already covered by the worktree root). If it is
   **outside** the worktree (a relocated brain), it adds the resolved brain
   subtree as a **shared rw** root — narrowest: the specific resolved subtree,
   never all of `~/.sulis/` (which holds other changes' state + sockets +
   cache → reopens the #130 cross-change risk). A new optional
   `brain_dir: Path | None` field on `AllowedRoots` carries it; `permitted_for`
   includes it for all four ops (the brain is legitimately shared rw).

2. **A new pure function `sandbox_write_roots(roots: AllowedRoots) -> list[str]`**
   emits the SAME root set as sandbox `allowWrite` path strings. It is the ONE
   adapter from the canonical `AllowedRoots` to the sandbox-config shape; the
   recipe (Phase 4) and any test read its output. Because both the file-tools
   check and the sandbox emit derive from one `AllowedRoots`, they cannot
   drift — this is the single-source-of-truth guarantee made structural.

Both stay canonical (`.resolve()`-d, `/tmp`→`/private/tmp`) and narrowest-root.

## Rationale (the recommended convention)

- **Extend the existing resolver, don't add a parallel one.** A separate
  L2-list and L3-list is the exact drift D5 rejects. One `AllowedRoots` value
  → two consumers (the bool scope check; the string emit) is the
  single-source pattern.
- **`brain_base_dir` is the established resolver** (#127) — using it (not a
  hardcoded path) is the convention; hardcoding `~/.sulis` is the rejected
  bespoke alternative that breaks on relocation.
- **Narrowest-root** is the security invariant the prior change established;
  the brain addition honours it (specific resolved subtree, conditional on
  being outside the worktree).
- **The sandbox auto-allows the linked-worktree's shared `.git`** (verified in
  the sandbox docs) — so the git-common-dir root is partly redundant under the
  sandbox, but the L2 file-tools check still needs it. Emitting it in
  `allowWrite` is harmless + keeps the two consumers reading one set; we note
  the redundancy rather than special-casing it out.

## Alternatives considered

- **Separate sandbox-roots resolver** — REJECTED (drift; D5).
- **Hardcode the brain at `~/.sulis/brain`** — REJECTED (breaks on a relocated
  or in-worktree brain; ignores `brain_base_dir`; D5/D7).
- **Always add the brain root unconditionally** — REJECTED. The default brain
  is in-worktree; adding it then either duplicates the worktree root or, worse,
  if mis-resolved, widens scope. Conditional-on-outside-worktree is narrowest.
- **Allow all of `~/.sulis/`** — REJECTED hardest (reopens #130 cross-change
  contamination; D5/D7 confirmed-rejected anti-pattern).

## Consequences

- `_file_scope.py` is the only file changed for the resolver (extend, not
  create) → WP-002 is a REORGANISE-Abstract + EXPAND on one module.
- The hook (ADR-003) and the MCP `scoped_file` (ADR-001) both call
  `within_allowed_scope` / `resolve_allowed_roots` — they inherit the brain
  root for free.
- The sandbox recipe (Phase 4, WP-004) documents pasting
  `sandbox_write_roots(...)` output into `sandbox.filesystem.allowWrite`, plus
  `denyRead` for creds (`~/.aws`, `~/.ssh`) and `allowedDomains` = the proxy
  egress host only.
- SC-E5 (resolver single-source, narrowest-root, relocated-brain allowed,
  sibling-change refused, file-tools set == sandbox set) is this resolver's
  scenario.
