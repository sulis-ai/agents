# sulis-execution — End-to-End Test Spec

This document specifies the E2E test that validates the
sulis-execution plugin end-to-end on a synthetic mini-project. The
test is **specification + manual replay**, not yet automated CI —
automation requires the Sulis platform-sdk's deploy + health
operations to be implemented, which lands in `sulis-platform-sdk`
v0.2+.

## Synthetic test fixture

Create `.architecture/test-e2e/`:

```
.architecture/test-e2e/
├── TDD.md
├── adrs/
│   └── ADR-001-storage-choice.md
└── work-packages/
    ├── INDEX.md
    ├── WP-001-add-user-model.md       (primitive: Create)
    ├── WP-002-extend-user-roles.md    (primitive: Extend, dependsOn: WP-001)
    └── WP-003-reuse-existing-auth.md  (primitive: Reuse, dependsOn: WP-001)
```

### TDD.md (skeleton)

```markdown
# Test E2E — Technical Design

## §1 Storage layer
The system uses an in-memory dict-based store for the test fixture.
Real persistence is out of scope.

## §2 User model
A User has: id (UUID), email (string, unique), roles (set of strings).

## §3 Auth
Auth uses HTTP Basic over TLS in the fixture. Production would use
OAuth 2.1 + OIDC per CP-05.

## §4 Endpoints
- POST /users
- GET /users/{id}
- POST /users/{id}/roles
```

### INDEX.md

```markdown
# Work Package INDEX — test-e2e

## Status summary
- Done: 0
- In flight: 0
- Blocked: 0
- Pending: 3

## WPs
| ID | Title | Primitive | Status | Depends | Blocks | Token | TDD § |
|---|---|---|:---:|---|---|---:|---|
| WP-001 | add-user-model | Create | pending | — | WP-002, WP-003 | 5k | 2 |
| WP-002 | extend-user-roles | Extend | pending | WP-001 | — | 3k | 2 |
| WP-003 | reuse-existing-auth | Reuse | pending | WP-001 | — | 2k | 3 |

## Recommended order
WP-001 → (WP-002 ∥ WP-003)
```

## Test scenarios

### Scenario 1 — Happy path (v0.4 sequential)

**Setup:** Stub Sulis SDK returns canned `succeeded` for all deploys
and `healthy` for all health checks.

**Run:**
```
claude --agent sulis-execution:orchestrator
# Internally invokes the orchestrator on .architecture/test-e2e/
```

**Expected outcome:**
- WP-001 picked first (lowest sequence_id, no deps).
- Executor dispatched for WP-001:
  - Worktree created at `../wp-001-worktree/`.
  - Red: tests for the User model written, all fail (model doesn't
    exist).
  - Green: User class created. Tests pass.
  - Blue: refactor (maybe extract a UUID helper).
  - Lint / type-check pass.
  - Commit + push the branch.
  - CI polled, green.
  - Squash-merge to `dev`. Remote branch deleted.
  - Stub SDK deploy → `succeeded`.
  - Stub SDK health → `healthy`.
  - Smoke-test (e.g. `curl /users/{a-new-uuid}`) → expected
    response.
  - WP-001 INDEX status: `done`.
  - Worktree removed.
- Orchestrator picks WP-002 (now ready, dep done).
- (Sequential execution; WP-003 runs after WP-002.)
- All 3 WPs done. Terminal status: *"3 of 3 WPs done."*

**Pass criteria:**
- INDEX final state: all `done`.
- 3 squash-merge commits on `dev`.
- 3 `## Acceptance Evidence` blocks in WP files with merge SHAs +
  deploy URLs + smoke verdicts.
- No BLOCKER files created.
- No worktrees left on disk.

### Scenario 2 — Injected CI failure (in-scope self-heal)

**Setup:** Same as Scenario 1, but the CI stub fails on WP-002's
first push with a known error (e.g. *"test_role_assignment failed:
expected ['admin'], got []"*).

**Expected outcome:**
- Executor on WP-002 reaches step 7 (CI poll); sees failure.
- Observe captures the verbatim CI log.
- Orient runs Five Whys:
  1. Why did test_role_assignment fail? → Expected ['admin'], got [].
  2. Why []? → The role-assignment code path didn't run.
  3. Why? → The code added in Green only handles `user.roles.add()`,
     not the request-body deserialisation.
  4. Why? → The Extend primitive added the new branch but the
     handler doesn't pass the role from the request body.
  5. Why? → Forgot to wire the request-body parsing.
- Decide: minimum change → wire the request-body field into the
  `roles.add()` call.
- Act: apply the fix, re-push, CI polls, green this time.
- Squash-merge proceeds. Deploy + health + smoke green.
- WP-002 done.

**Pass criteria:**
- Self-heal trace recorded in `.executor-WP-002.md`.
- 1 attempt consumed of CI-failure budget (3 max).
- No BLOCKER file (failure was in scope and resolved).
- Final INDEX: WP-002 done.

### Scenario 3 — Injected deploy infra failure (out-of-scope escalation)

**Setup:** Stub SDK returns `failed` for WP-003's deploy with the
error *"503 — staging cluster reports 'no healthy upstream'."*

**Expected outcome:**
- Executor on WP-003 reaches step 8 (deploy).
- Observe captures the verbatim deploy error.
- Orient runs Five Whys:
  1. Why failed? → 503 from staging.
  2. Why 503? → No healthy upstream pods.
  3. Why? → Deploy didn't roll out.
  4. Why? → Cluster reports `InsufficientCapacity`.
  5. Why? → Staging cluster is at quota.
- Scope check: **out of scope**. Cluster quota is infra, not the
  WP's contract.
- Halt. Write `BLOCKER-WP-003.md`:
  - Verbatim observation (the 503 error).
  - Five Whys trace.
  - Root cause: staging cluster quota exhaustion.
  - Scope verdict: out-of-scope (scope guard fired).
  - Plain-English summary: *"WP-3 is blocked — staging cluster is
    at its capacity limit and a new deploy can't fit. This isn't a
    code issue. The platform team needs to free up capacity. Once
    done, I can retry the deploy."*
- Orchestrator records the blocker; no other WPs depend on WP-003,
  so terminal status: *"2 of 3 WPs done; 1 blocked on staging
  infrastructure."*

**Pass criteria:**
- BLOCKER-WP-003.md written with correct EL-08 format.
- WP-003 INDEX status: `blocked`.
- Worktree at `../wp-003-worktree/` left in place (per scope-guard
  rule — evidence for investigation).
- 0 attempts consumed of executor's self-heal budget for deploy
  (the scope guard fires immediately on out-of-scope diagnosis).

### Scenario 4 — Retry after external resolution

**Setup:** Continue from Scenario 3. Imagine the platform team has
freed up cluster capacity; the stub SDK now returns `succeeded` for
deploys.

**Run:**
```
/sulis-execution:retry WP-003
```

**Expected outcome:**
- Retry skill archives `BLOCKER-WP-003.md` and `.executor-WP-003.md`
  to `.archive/`.
- Resets INDEX status to `pending`.
- Cleans up the old worktree at `../wp-003-worktree/`.
- Dispatches the executor fresh on WP-003.
- This time deploy + health + smoke all pass.
- WP-003 done.

**Pass criteria:**
- `.archive/BLOCKER-WP-003-<timestamp>.md` exists.
- `.archive/.executor-WP-003-<timestamp>.md` exists.
- New `## Acceptance Evidence` block on WP-003 reflects the
  successful run.
- Final INDEX: all 3 WPs done.

## What this E2E test validates

- 10-step lifecycle end-to-end (v0.3).
- Dependency ordering and topological dispatch (orchestrator v0.4).
- In-scope OODA self-heal (Scenario 2 — EL-01..05).
- Out-of-scope scope-guard escalation (Scenario 3 — EL-06).
- Retry flow with archive preservation (Scenario 4).
- BLOCKER record format (EL-08).
- WP `## Acceptance Evidence` shape (lifecycle.md output contract).
- No PR ceremony on merges (GIT-05).
- Worktree cleanup timing (GIT-07 — at done, not at merge; left in
  place on escalation).

## When to run

- Manually after each version bump (v0.1 → v0.5) to confirm the
  released version handles the scenarios.
- Automated CI when `sulis-platform-sdk` v0.2+ ships with real
  deploy + health operations (replaces the stubs in this spec).

## Out of scope for this E2E

- REORGANISE / SUBSTITUTE / CONTRACT primitives — v0.5 scaffolds
  are documented, but the synthetic fixture uses only EXPAND-group
  primitives for v0.4-era validation.
- Parallel execution — orchestrator v0.4 is sequential-only;
  parallelism lands later.
- Production `dev → main` promotion — that's the concierge's
  founder-confirmed ceremony, separate from the executor's
  contract.
- Multi-project orchestration — one WP INDEX per project.
