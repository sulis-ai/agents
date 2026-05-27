# Hardening Deltas — PR-batch5-2026-05-23T124318Z

Drafts produced by `/sea:code-review` against the Batch 5 working-tree
changes (HD-001 + HD-007 — plan/commit/verify split + verifying_gates
phase). All deltas ship at `status: proposed`; promote to `accepted`
to queue them for `/sea:harden`.

## Severity-ordered

| ID | Severity | Title | Lens |
|---|---|---|---|
| HD-010 | CRITICAL | `cmd_mark_gates_complete` silently truncates train YAML record (`read_train_run_record` does not exist) | architecture + quality |
| HD-012 | HIGH | SDK lags wpx-train CLI — no `mark_gates_complete`; `run()` missing `enable_gate_handoff`; `TrainRunResult.outcome` Literal missing `awaiting_gates` | architecture |
| HD-011 | MEDIUM | `render_train_state_plain_english` missing `verifying_gates` description; contains dead `code_review` entry | quality |

## Recommended acceptance order

1. **HD-010 first.** Silent data-loss bug; blocks the commit. Pre-merge.
2. **HD-012 next.** Pre-merge or immediately post-merge — must land
   before any SDK consumer adopts the gate-handoff path. The orchestrator
   has already noted this is a known gap.
3. **HD-011 last.** Quality polish; can ship in the same commit or a
   small follow-up.

## Dependency graph

```
HD-010 (CRITICAL) ──┐
                    ├──→ Batch 5 ship gate
HD-011 (MEDIUM)  ───┘

HD-012 (HIGH) ───→ Batch 5.1 or co-shipped
```

No inter-delta dependencies — each closes a distinct gap.

## Provenance

All three sourced from the code review at
`../REVIEW.md` (CR-04 evidence: file:line + quoted text per finding).
