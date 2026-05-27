# Hardening Deltas — Batch 4 Retroactive Code Review

> **Bundle:** `PR-batch4-retro-2026-05-23T132739Z/`
> **Source review:** `REVIEW.md`
> **Status:** Drafts (`status: proposed`) — promote to `accepted` in each file's frontmatter when ready, then run `/sea:harden HD-NNN`.

## Drafted

| ID | Title | Severity | Pillar | Lens |
|---|---|---|---|---|
| HD-013 | Restore lost diagnostic log for non-JSON / empty `gh compare` output | MEDIUM | armor | architecture + quality |
| HD-014 | Remove dead `_CIConfig` / `_DeployConfig` state in `FakeGHClient` | LOW | proof | quality |

## Suggested acceptance order

1. **HD-013** — MEDIUM observability regression. Surgical (~6 LOC). Restores parity with pre-HD-005 production debugging behaviour. Ship as a behaviour-preservation patch.
2. **HD-014** — LOW design-cleanup. Surface a foot-gun for future test authors; closes a latent strict-ci divergence. Ship at convenience, not load-bearing.

Neither finding blocks Batch 6 (HD-008). Neither requires reverting Batch 4.

## Source review verdict

The Batch 4 commit was sound. The review verdict was **Approve with fixes** — no CRITICAL or HIGH findings; the deltas above are forward-fix observations that the per-batch code-review process would have caught had it been in place at v0.22.0.
