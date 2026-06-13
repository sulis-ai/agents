# Working Set — refactor-de-branch-scope-the-brain

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Move the Brain store out of the per-change git worktree so it is no longer branch-scoped; relocate it to live alongside the Brain's settings (user-level), closing the capture/recall loop across changes.

## 2. Current best solution  (→ Design)
_(not yet established)_

## 3. Decisions in flight  (→ Decision; status: proposed)
_(none yet — one entry per non-trivial choice being weighed: the choice, options
considered, rejected alternatives + rationale, status proposed→accepted on lock)_

## 4. Open questions / unknowns
_(none yet — the live "what we still don't know" parking lot)_

## 5. Rejected so far  (→ Decision.rejected_alternatives)
_(none yet — paths tried and abandoned, **with the why**)_

## 6. Working log  (append-only)
- 2026-06-13T11:34:10Z — Working Set created.
- 2026-06-13T11:34:10Z — Corrected a stale change binding inherited from a previous session (env pointed at 01KTYF88; worktree is 01KV0C44 de-branch-scope-the-brain).
- 2026-06-13T11:35:52Z — Recon done. Single resolver _brain_location.py:brain_base_dir owns location; default <repo_root>/.brain/instances is the branch-scoping bug (worktree repo_root → brain lives in worktree, lost at ship). Settings home already user-level ~/.sulis. Fix = retarget the default to user-level, leave override chain intact. 4 call sites all route through the resolver.
- 2026-06-13T12:09:06Z — DECISION: brain default → user-level home (~/.sulis), namespaced per project/tenant (mirrors product-store layout ~/.sulis/instances/{tenant_id}/). Override chain unchanged (explicit > SULIS_BRAIN_BASE_DIR > repo-contract brain_location > default). Constraint: orphan nothing — Sulis's own in-repo committed brain must keep resolving (via explicit repo-contract brain_location). REJECTED: single shared global brain (founder chose per-project separation).
- 2026-06-13T12:10:09Z — AUDIT done (focused, single-resolver). Current behaviour pinned by tests/unit/test_brain_location.py: precedence explicit>env>contract>default — KEEP. Only the default branch changes. Tenant identity reuse: derive tenant_id from repo-contract 'repo:' slug via existing Sha256CrockfordTenantDeriver (no new source of truth). New default path mirrors settings store: ~/.sulis/instances/{tenant_id}/.brain/instances. SINGLE hardening delta. Tests to update: test_default_is_repo_brain_unchanged + test_absent_contract_field_falls_to_default (they encode the OLD default) → re-characterise to new user-level default; ADD per-tenant separation test. Orphan-nothing: set Sulis's own .sulis/repo-contract.yml brain_location explicitly to keep its committed in-repo brain. journey-walk: exempt — non-user-facing internal plumbing.
- 2026-06-13T12:48:00Z — IMPLEMENTED + GREEN. Resolver default → sulis_state_base()/.brain/instances (reuses _change_state.sulis_state_base, honours SULIS_STATE_DIR). _user_level_default() helper w/ best-effort import fallback. Override chain intact. Sulis dogfood pinned via repo-contract brain_location: .brain/instances (orphan-nothing). _brain_emit_helper degraded fallback also de-branch-scoped. Tests: brain_location 11/11 incl. new de-branch-scope property test; isolation fixtures (SULIS_BRAIN_BASE_DIR pin) added to test_change_emission + test_sulis_change_emits_entity. Full unit 2925 pass; brain integration 108 pass; compileall + manifest lint OK.
