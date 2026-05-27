# Decompose Validation — terminal-launcher-port

> **Rubric:** [`plugins/sulis/references/decompose-validation-rubric.md`](../../../plugins/sulis/references/decompose-validation-rubric.md)
> **Date:** 2026-05-25 (SEA-authored amendment after MUC-A5 remediation — Sulis previously authored an amendment directly; this is the principled SEA replacement)
> **WP set:** 7 WPs (WP-001 through WP-007)
> **Verdict:** **PASS** (1 SHOULD with rationale)

---

## Scope of this validation

This rubric run covers the full 7-WP set as a single coherent decomposition. The prior 4-WP set (WP-001..WP-004 covering only the launcher mechanism) is superseded by this expanded set, which integrates the launcher with the session-binding concerns from the change-as-primitive design doc § "Session binding".

The 7 WPs partition into two cohesive concerns (see INDEX.md for diagram):

- **A — Launcher mechanism** (WP-001 → WP-002 → WP-003 → WP-004)
- **B — Session integration** (WP-005, WP-006, WP-007)

The two concerns ship together at v0.43.0. The rubric below validates them as one set.

---

## P1 — Inventory Completeness

Every WP must have Context, Contract, Definition of Done (Red-Green-Blue), Sequence, Estimated Token Cost, Dependencies.

| WP | Context | Contract | DoD/RGB | Sequence | Token | Deps |
|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-007 | ✓ | ✓ | ✓ (manual-smoke variant; agent-body changes are not unit-testable in the conventional sense — documented procedures stand in for unit tests) | ✓ | ✓ | ✓ |

**P1: PASS** — all six required sections present in all seven WPs.

---

## P2 — Atomicity

Each WP must have a single responsibility. Touch surface ≤ 15 files (MUST), ≤ 8 (SHOULD). No "and" in titles or purpose statements.

| WP | Touch surface | "and" in title? | Single responsibility? |
|---|---|---|---|
| WP-001 | 2 (`_terminal_launcher.py` + test file) | Title uses `+` (compound foundational deliverable: module file with its initial validators and script builder — same logical capability, not multiple) | Yes — pure-logic foundation |
| WP-002 | 1 (extends existing `_terminal_launcher.py` + its test file = 2 actually) | No | Yes — dispatchers only |
| WP-003 | 2 (extends existing files) | No | Yes — public entry-point composition |
| WP-004 | 5 (`sulis-change` + plugin.json + marketplace.json + CHANGELOG + smoke-test doc) | Title says "composes recon + pre-prompt + launcher" — composition is the single responsibility; the surface bundles a shipping-cut release (version bump + changelog) | Yes — shipping-cut granularity (SHOULD-level rationale below) |
| WP-005 | 3 (new module + new test + `sulis-change` extension) | No | Yes — recon writer only |
| WP-006 | 2 (extends `_terminal_launcher.py` + its test file) | No | Yes — pre-prompt delivery extension |
| WP-007 | 5 (1 agent body + 3 manual smoke docs + 1 verification report touch — does not modify, just respects) | No | Yes — session-start agent behaviour |

**SHOULD-rationale for WP-004:** The shipping-cut WP bundles three small bookkeeping concerns (argparse flag, `cmd_start` modification, version bump + changelog) with the composition itself. The MUST ceiling of 15 files is well clear (5 files); the SHOULD target of 8 is met. Bundling the version bump with the composition is correct sequencing — there is no other WP at which the v0.43.0 release should land, because no other WP completes the founder-facing feature.

**P2: PASS-WITH-RATIONALE** — all touch surfaces under MUST and SHOULD ceilings; WP-004's shipping-cut composition documented above.

---

## P3 — Module Naming + Clean Code

No jargon prefixes, no single-letter abbreviations, descriptive kebab-case slugs.

| WP | Slug | Verdict |
|---|---|---|
| WP-001 | `build-launch-script-and-validators` | ✓ |
| WP-002 | `platform-dispatchers` | ✓ |
| WP-003 | `launch-change-terminal-entry-point` | ✓ |
| WP-004 | `sulis-change-spawn-integration` | ✓ |
| WP-005 | `pre-spawn-context-write` | ✓ |
| WP-006 | `pre-prompt-heredoc-delivery` | ✓ |
| WP-007 | `agent-change-context-greeting` | ✓ |

New names introduced across the set:

- `write_change_context(change_id, metadata, repo_root) -> Path` — verb-noun-noun, clear
- `_PRIMITIVE_NEXT_STEP_HINTS: dict[str, str]` — descriptive, capitalised constant
- `_build_change_pre_prompt(...) -> str` — verb-noun-noun, snake_case
- `pre_prompt: str | None` — descriptive, snake_case, single-purpose parameter
- `_validate_pre_prompt(text) -> tuple[bool, str]` — verb-noun, matches existing validator shape
- `_PRE_PROMPT_HEREDOC_TAG: str` — descriptive constant
- `_PRE_PROMPT_MAX_BYTES: int` — descriptive constant
- `_change_context` module name — descriptive, lowercase-snake, matches `_wpxlib` convention

No jargon prefixes, no single-letter abbreviations, no shorthand outside established marketplace vocabulary.

**P3: PASS**.

---

## P4 — Dependency Graph Correctness

No cycles. All `dependsOn` targets exist. Transitive depth ≤ 8. Valid topological order. `dependsOn` and `blocks` declarations consistent.

```
WP-001 ──→ WP-002 ──→ WP-003 ──→ WP-006 ──→ WP-004
                         │                     ↑
WP-005 ────────────────────────────────────────┤
                                               │
WP-007 (independent — no edges in either direction)
```

| Check | Result |
|---|---|
| No cycles | ✓ |
| All `dependsOn` targets exist within the set | ✓ |
| Transitive depth | 5 (WP-001 → WP-002 → WP-003 → WP-006 → WP-004) — well under the depth-8 ceiling |
| Valid topological order | ✓ — numerical order is one valid topological order; Round 1 / Round 2 ordering in INDEX.md is another |
| `blocks` declarations reciprocal with `dependsOn` | ✓ — every "WP-X blocks WP-Y" has a matching "WP-Y dependsOn: [..., WP-X, ...]" |

Reciprocal-check trace:
- WP-001 blocks [WP-002, WP-003] → WP-002 dependsOn [WP-001] ✓; WP-003 dependsOn [WP-001, WP-002] ✓
- WP-001 also blocks WP-006 (via WP-006's dependsOn [WP-001, WP-003]) — INDEX.md and WP-001 both note this transitively
- WP-002 blocks [WP-003] → WP-003 dependsOn [WP-001, WP-002] ✓
- WP-003 blocks [WP-004, WP-006] → WP-004 dependsOn includes WP-003 ✓; WP-006 dependsOn [WP-001, WP-003] ✓
- WP-005 blocks [WP-004] → WP-004 dependsOn includes WP-005 ✓
- WP-006 blocks [WP-004] → WP-004 dependsOn includes WP-006 ✓
- WP-007 blocks [] (independent leaf)

**P4: PASS**.

---

## P5 — Performance + Non-Functional Requirements

Endpoint/handler WPs require a `## Performance` section with measurable bounds.

None of the 7 WPs are endpoint/handler WPs in the HTTP/RPC sense. The relevant non-functional bound is **NFR-3: spawn-time < 2s end-to-end** (from the handoff doc). The path that consumes this budget is `sulis-change start --spawn` → recon → pre-prompt build → launcher dispatch. Per-WP allocation:

| WP | Budget contribution to NFR-3 | Captured in |
|---|---|---|
| WP-005 (recon) | 3 git subprocess calls expected to complete in < 500ms on a normal-sized repo | WP-005 Notes |
| WP-004 (pre-prompt build) | Pure string assembly — negligible (< 10ms) | WP-004 Notes |
| WP-003 (script write + dispatch) | One file write + one subprocess spawn — typically < 200ms | WP-003 Notes |

The end-to-end bound is observed via the manual smoke procedure `smoke_sulis_change_start_spawn.md` (per WP-004) — the operator times the invocation and reports whether the 2s NFR holds. CI cannot verify the bound (no desktop), so the smoke procedure is the formal verification surface.

**P5: PASS** — no endpoint/handler WPs; NFR-3 surfaced and allocated across WPs; verification path documented.

---

## P6 — Peer-Collision Risk

No two WPs `Create` the same file. Sequential `Extend` on the same file is safe; parallel `Create` is not.

| File | Created by | Extended by | Collision? |
|---|---|---|---|
| `plugins/sulis/scripts/_terminal_launcher.py` | WP-001 | WP-002, WP-003, WP-006 | No — single creator; extends run after WP-001 lands |
| `plugins/sulis/scripts/tests/unit/test_terminal_launcher.py` | WP-001 | WP-002, WP-003, WP-006 | No — same pattern |
| `plugins/sulis/scripts/_change_context.py` | WP-005 | — | No |
| `plugins/sulis/scripts/tests/unit/test_change_context.py` | WP-005 | — | No |
| `plugins/sulis/scripts/sulis-change` | (existing) | WP-004, WP-005 | Sequential — WP-005 lands first (WP-005 blocks WP-004); WP-004 builds on WP-005's modifications. Same-file sequential extends are safe. |
| `plugins/sulis/agents/sulis.md` | (existing) | WP-007 | No — single extender |
| `plugins/sulis/.claude-plugin/plugin.json` | (existing) | WP-004 | No — single extender |
| `.claude-plugin/marketplace.json` | (existing) | WP-004 | No — single extender |
| `plugins/sulis/CHANGELOG.md` | (existing) | WP-004 | No — single extender |
| Manual smoke-test docs (5 files, distinct) | WP-004 (1) + WP-007 (3) + WP-005-or-WP-004 (1) | — | No — distinct files |

WP-001 and WP-005 are the only `Create` primitives. They create different files (`_terminal_launcher.py` vs `_change_context.py`). No peer collision.

WP-004 and WP-005 both extend `sulis-change`. The dependency edge (WP-005 blocks WP-004) ensures WP-005 lands first; WP-004 reads the modified file and extends further. Sequential same-file extends are safe per the rubric.

**P6: PASS**.

---

## Verdict

**PASS** (1 SHOULD-rationale carried — WP-004 shipping-cut atomicity, justified above).

All six MUST phases pass. The 7-WP set is:

- **Inventoried** — every WP has the required sections
- **Atomic** — each WP has a single responsibility; touch surfaces well under MUST and SHOULD ceilings
- **Named** — descriptive kebab-case slugs; new abstracts named descriptively
- **Graph-correct** — no cycles, depth 5, all references valid, reciprocal `dependsOn` / `blocks`
- **NFR-aware** — spawn-time budget allocated across the path and verified via manual smoke
- **Collision-free** — two independent `Create` primitives produce different files; same-file extends are sequenced

After WPs 001..007 ship at v0.43.0, the founder running `sulis-change start --slug X --primitive Y --spawn` gets the design-doc UX:

1. Branch + worktree + metadata exist (existing behaviour)
2. `~/.sulis/changes/{change_id}/CONTEXT.md` is on disk (WP-005)
3. A new terminal opens in the worktree (WP-001..003) with `SULIS_CHANGE_ID` set
4. The terminal runs `claude --agent sulis` briefed by a HERE-DOC pre-prompt (WP-006 delivery, WP-004 body)
5. The Sulis agent verifies the binding, reads CONTEXT.md, and greets the founder in change-context mode (WP-007)

Remaining design-doc elements (founder-facing `/sulis:change start` slash command, dashboard, reattach) are explicitly Phase 6 work and are not part of this WP set.

**Ready for `/sulis:run-all`.**
