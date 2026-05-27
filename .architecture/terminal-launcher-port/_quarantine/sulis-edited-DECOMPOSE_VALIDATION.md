# Decompose Validation — terminal-launcher-port

> **Rubric:** [`plugins/sulis/references/decompose-validation-rubric.md`](../../../plugins/sulis/references/decompose-validation-rubric.md)
> **Date:** 2026-05-25 (expanded to 7-WP set after user-flagged Phase 5 + Phase 6 integration gap)
> **WP set:** 7 WPs (WP-001 through WP-007)
> **Verdict:** **PASS** (1 SHOULD with rationale)

---

## Two-cluster validation

The set splits into two clusters that the rubric validates independently:

- **Cluster A — Launcher mechanism** (WP-001..WP-004): the original 4-WP set; PASS confirmed in the prior validation.
- **Cluster B — Integration** (WP-005, WP-006, WP-007): 3 new WPs added to close the Phase 5 + Phase 6 integration gap.

The full 7-WP graph composes A + B into one dependency-coherent set (see INDEX.md).

---

## P1 — Inventory Completeness

Every WP has Context, Contract, DoD/RGB, Sequence, Token cost, and Dependencies.

| WP | Context | Contract | DoD/RGB | Sequence | Token | Deps |
|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-007 | ✓ | ✓ | ✓ (with manual-smoke variant — agent-body changes aren't unit-testable in the conventional sense) | ✓ | ✓ | ✓ |

**P1: PASS** (all 6 required sections present in all 7 WPs).

---

## P2 — Atomicity

Single responsibility per WP. Touch surface ≤ 15 files (MUST), ≤ 8 (SHOULD). No "and" in titles or purpose.

| WP | Touch surface | "and" in title? | Single responsibility? |
|---|---|---|---|
| WP-001 | 2 | (Compound title: "with X + Y" — same logical capability per prior validation) | Yes — pure-logic foundation |
| WP-002 | 2 | No | Yes — dispatchers only |
| WP-003 | 2 | No | Yes — entry-point composition |
| WP-004 | 5 | Compound — shipping cut combines 3 small bookkeeping concerns (per prior validation rationale) | Yes (shipping-cut granularity) |
| WP-005 | 3 (new recon module + tests + sulis-change extension) | No | Yes — recon only |
| WP-006 | 2 (extends existing launcher files) | No | Yes — HERE-DOC support |
| WP-007 | 5 (1 agent body + 3 manual smoke docs + 1 implicit ARCH update) | No | Yes — session-bound agent behaviour |

**P2: PASS-WITH-RATIONALE** (WP-004 retains its prior shipping-cut rationale; no new "and" violations introduced by WPs 005/006/007).

---

## P3 — Module Naming + Clean Code

No jargon prefixes, no single-letter abbreviations, descriptive kebab-case slugs.

New entries:

| WP | Slug | Verdict |
|---|---|---|
| WP-005 | `pre-spawn-recon` | ✓ |
| WP-006 | `here-doc-pre-prompt` | ✓ |
| WP-007 | `sulis-agent-reads-change-id` | ✓ |

New function names per WP-005 contract:
- `write_change_context(change_id, metadata, repo_root) -> Path` — verb-noun-noun, clear
- `_CHANGE_PRIMITIVE_HINTS: dict[str, str]` — descriptive constant name

New parameter in WP-006:
- `pre_prompt: str | None` — descriptive, snake_case, single-purpose

No jargon prefixes, no single-letter abbreviations, no shorthand outside established marketplace vocabulary.

**P3: PASS**.

---

## P4 — Dependency Graph Correctness

No cycles, all targets exist, transitive depth ≤ 8, valid topological order.

```
WP-001 ─→ WP-002 ─→ WP-003 ─→ WP-006 ─→ WP-004
                                          ↑
WP-005 ─────────────────────────────────  │
                                          │
WP-007 (independent)
```

| Check | Result |
|---|---|
| No cycles | ✓ |
| All dependsOn targets exist | ✓ (all reference WPs in the set) |
| Transitive depth | 5 (WP-001 → WP-002 → WP-003 → WP-006 → WP-004) — well under 8 |
| Valid topological order | ✓ (numerical order is one valid topological order; alternative: WP-001, WP-005, WP-007 in round 1) |
| All `blocks` declarations consistent with reciprocal `dependsOn` | ✓ |

**P4: PASS**.

---

## P5 — Performance + Non-Functional Requirements

Endpoint/handler WPs have a `## Performance` section with measurable bounds.

None of the 7 WPs are endpoint/handler WPs. The closest is WP-005 (recon writes to disk synchronously) — its perf bound is implicit in NFR-3 (spawn-time < 2s end-to-end). The recon must complete in well under 2s for the overall spawn-time NFR to hold. Documented in WP-005 Notes: "Recon does not modify the repo. Pure-read git operations only" — this is the path to keeping it sub-second.

**P5: PASS** (no endpoint/handler WPs; NFR-3 surfaced via manual smoke + implicit in recon Notes).

---

## P6 — Peer-Collision Risk

No two WPs `Create` the same file.

| File | Created by | Extended by |
|---|---|---|
| `plugins/sulis/scripts/_terminal_launcher.py` | WP-001 | WP-002, WP-003, WP-006 |
| `plugins/sulis/scripts/tests/unit/test_terminal_launcher.py` | WP-001 | WP-002, WP-003, WP-006 |
| `plugins/sulis/scripts/_change_recon.py` (or extension to `_wpxlib.py` — choose at impl time) | WP-005 | — |
| `plugins/sulis/scripts/tests/unit/test_change_recon.py` | WP-005 | — |
| `plugins/sulis/scripts/sulis-change` | (existing) | WP-004, WP-005 |
| `plugins/sulis/agents/sulis.md` | (existing) | WP-007 |
| `plugins/sulis/.claude-plugin/plugin.json` | (existing) | WP-004 |
| `.claude-plugin/marketplace.json` | (existing) | WP-004 |
| `plugins/sulis/CHANGELOG.md` | (existing) | WP-004 |
| Manual smoke-test docs (4 files) | WP-004 (1) + WP-007 (3) — distinct files | — |

WP-001 and WP-005 are the only creators. They create DIFFERENT files. WP-005 introduces 2 new files (recon module + test); WP-001 introduces 2 different new files (launcher + test).

**No peer-collision.** WP-004 + WP-005 both extending `sulis-change` is sequential (WP-005 lands first per dep graph; WP-004 builds on the WP-005 changes).

**P6: PASS**.

---

## Verdict

**PASS** (1 SHOULD with rationale carried over from the original validation — WP-004 shipping-cut atomicity).

All 6 MUST phases pass. The 3 new WPs (WP-005, WP-006, WP-007) close the user-flagged Phase 5 + Phase 6 integration gap by:

- WP-005 — making `~/.sulis/changes/{change_id}/CONTEXT.md` exist for the pre-prompt to reference
- WP-006 — delivering the HERE-DOC pre-prompt the design doc describes (with shell-safety guards)
- WP-007 — making Sulis recognize `SULIS_CHANGE_ID` and greet contextually

After all 7 ship at v0.43.0, the founder running `sulis-change start --slug X --primitive Y --spawn` gets the design-doc UX: a new terminal opens with a focused Sulis session that knows about the change.

The remaining design-doc elements (founder-facing `/sulis:change start` slash command, dashboard, reattach) are Phase 6 work, explicitly out of scope for this WP set.

Ready for `/sulis:run-all`.
