# Change Work Standard

<!-- summary -->
A **change** is the unit of work in the Sulis marketplace. Every piece
of work that evolves the system — from a one-line config tweak to a
multi-week new feature — is bounded by a change. A change is realised
as a dedicated git branch + worktree, named `change/{primitive}-{slug}`
where `primitive` is one of the 22 change primitives already used by
SEA. All artifacts produced *for* that change — specification,
architecture, work packages, hardening deltas, code, tests, code-review
reports, security findings — live on that branch. When the change is
shipped, the branch merges to `dev`. Multiple changes run in parallel,
each on their own branch, with no cross-change coordination required.

CW-01..CW-08 codify this. The model resolves the per-project
`.specifications/{x}/` and `.architecture/{x}/` collision problem
documented in this conversation: parallel work today shares a branch,
so artifact directories conflict. Branching by change makes those
directories disjoint by construction.
<!-- /summary -->

> **Version:** 0.2.0
> **Status:** Active — Calibration Period (90 days from 2026-05-21)
> **v0.2.0 amendment** (Phase 4 of change-as-primitive build, 2026-05-25): CW-04 gains the **Auto back-integration** subsection — merge-not-rebase mechanism with two trigger points (post-WP-merge + pre-WP-start) and structured conflict handling. Operationalises what CW-04's two-level worktree hierarchy makes possible: keeping the change branch current with `dev` without breaking in-flight WP worktrees.
> **Applies to:** Every Sulis-marketplace skill or tool that produces
> artifacts under `.specifications/`, `.architecture/`, `.security/`,
> `.pitch/`, or any other project-scoped directory; every executor
> worktree; every train run.

---

## Provenance

This standard synthesises four established conventions.

| Source | Year | Contribution |
|---|---|---|
| **OpenSpec** (Fission AI) | 2025 | The `openspec/changes/{proposal-id}/` directory pattern — a change is a first-class object with its own state, separate from the canonical spec. SEA's Hardening Deltas already inherit this shape; CW extends it to the whole change lifecycle. |
| **Conventional Commits 1.0.0** | 2017 | Verb-prefixed change types (`feat`, `fix`, `refactor`, `chore`, etc.). CW maps these onto the existing 22-primitive vocabulary. |
| **SEA Change Primitives** (`plugins/sulis/references/change-primitives.md`) | This marketplace | The 22-primitive catalogue — EXPAND (Create, Extend, Reuse, Compose, Generate), REORGANISE (Move, Refactor, Inline, Merge, Decompose, Abstract), SUBSTITUTE (Replace, Strangle, Wrap), CONTRACT (Deprecate, Delete), REINFORCE (Test, Instrument, Secure, Harden, Gate, Document). Branch naming inherits this. |
| **GIT-01..GIT-10** (Git Workflow Standard) | This marketplace | The two-branch dev/main model. CW slots between dev and the executor's per-WP branches — `change/...` branches live above WP branches and below dev. |

The synthesis itself is a Sulis-marketplace contribution. No prior
literature packages change-as-unit-of-work with two-level worktree
nesting + the change-primitive vocabulary together.

---

## Counter-Evidence (BI disclosure)

Honest disclosure of what could fail:

- **Long-lived change branches diverge from main.** A change that takes
  three months falls behind the daily integration on `dev`. Mitigated
  by CW keeping changes small (most should ship in days, not months),
  but the failure mode is real.
- **Some changes are too small to warrant a branch.** A typo fix, a
  one-line config edit — the branch + worktree overhead is heavier
  than the change. CW-05 carves out a "trivial change" path that
  bypasses the worktree.
- **Cross-change coordination is unstated.** This v0.1.0 explicitly
  assumes changes are independent. If real practice surfaces
  dependencies (Change B blocked on Change A), CW-07 is wrong and
  needs a change-DAG layer.
- **The change-primitive vocabulary is opinionated.** Teams without
  SEA's primitive taxonomy can't easily adopt the naming convention.
  CW-02 makes the primitive optional with a sensible default
  (`change/feat-...` for unclassified work).

---

## Adversarial Comparison (AT disclosure)

Four structural alternatives were considered and rejected:

| Alternative | Why it might be right | Why rejected |
|---|---|---|
| **Specification as unit of work** | Aligns with "spec-driven development" branding | Forces every change to look like the big-spec case. Most changes don't need an SRD or TDD; "specification" was making the model heavier than necessary. |
| **Project as unit (current default)** | No new concept; just keep using `.specifications/{project}/` on `dev` | The problem this standard exists to solve. Parallel work on the same project collides at the artifact-directory level. |
| **Per-skill branching** (one branch per SRD session, one per SEA session) | Maximum isolation | Chaos. Skills aren't natural units — a change might use SRD then SEA then executors. Per-skill branches force constant merging between artifacts that belong to the same logical change. |
| **No branching, everything on `dev`** | Simple | The problem we're solving. Doesn't scale beyond 1 active change per project. |

The decisive criterion is **cohesion** — a change groups artifacts that
belong together (the SRD, the TDD, the WPs, the code, the security
findings — all about the same evolution of the system) and isolates
them from artifacts that don't.

---

## Boundary Definition

This standard governs **how a change is bounded, branched, and
lifecycled** as a unit of work. It does **not** govern:

- **What the change does to the code** — that's the change primitives
  + the executor's RGB cycle
- **What artifacts a change must produce** — varies; some changes have
  full SRDs, others have just a WP + code
- **How code review or security review work inside a change** — handled
  by their respective standards (CR-01..CR-09, sulis-security)
- **The merge mechanics from `dev` to `main`** — handled by GIT-01..GIT-10
- **Inter-change dependency or coordination** — explicitly deferred to a
  future v0.2.0 (see Non-goals)

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block the change from being accepted. |
| **SHOULD** | Default. Deviation documented in the change's journal. |

---

## CW-01: A Change Is the Unit of Work (MUST)

**Every unit of work that evolves the codebase is bounded by a change.**
A change has a start, a middle, and an end. Its boundary is a git
branch + an associated worktree directory. All artifacts produced for
the change — specifications, architecture, work packages, code, tests,
hardening deltas, code-review reports, security findings — live on
that branch.

When the change is shipped, the branch merges into `dev`. When the
branch merges, the change is over.

### Why this matters

- One conceptual unit groups artifacts that belong together
- Parallel changes can't collide on shared artifact directories
  (`.specifications/{x}/` lives on Change A's branch; Change B has
  its own copy on its own branch)
- The lifecycle is observable — `git branch | grep change/` lists
  active work; merges are the completion signal

---

## CW-02: Branch Naming — `change/{primitive}-{slug}` (MUST)

The branch convention is `change/{primitive}-{slug}` where:

- `primitive` is one of the 22 change primitives from
  `plugins/sulis/references/change-primitives.md`, lowercased: `create`,
  `extend`, `reuse`, `compose`, `generate`, `move`, `refactor`,
  `inline`, `merge`, `decompose`, `abstract`, `replace`, `strangle`,
  `wrap`, `deprecate`, `delete`, `test`, `instrument`, `secure`,
  `harden`, `gate`, `document`.
- `slug` is a 2-5 word kebab-case descriptor.

**Default if the primitive is unclassified:** use the Conventional
Commits type as a fallback — `feat`, `fix`, `chore`. So
`change/feat-payments` is acceptable when the work hasn't yet been
classified.

### Examples

| Branch | Primitive | Meaning |
|---|---|---|
| `change/create-payments` | EXPAND/Create | New payments domain |
| `change/strangle-task-service` | SUBSTITUTE/Strangle | Migrate task-service out |
| `change/refactor-http-client` | REORGANISE/Refactor | Behaviour-preserving cleanup |
| `change/harden-stripe-resilience` | REINFORCE/Harden | Add timeouts + CB to Stripe calls |
| `change/delete-deprecated-v1-api` | CONTRACT/Delete | Remove v1 endpoints |
| `change/feat-coupon-management` | (unclassified) | New feature; primitive TBD |

The primitive in the name is documentation. Reviewers see at a glance
what kind of change is on the branch.

---

## CW-03: Artifact Homes Stay the Same (MUST)

Existing artifact directories — `.specifications/{project}/`,
`.architecture/{project}/`, `.security/{project}/`, `.pitch/{slug}/`,
etc. — do not move. They continue to live at their existing paths.
**What changes is the branch they live on.**

Today: `.specifications/payments/SRD.md` is on `dev` and conflicts
with parallel work.

After CW: `.specifications/payments/SRD.md` is on `change/create-payments`
while Change B's edits to a different spec live on `change/refactor-orders`.
Disjoint by branch, not by path.

### Implication for skills

Skills (SRD, SEA, sulis-security, IDC, etc.) do not need to know
they're on a change branch. They write to the same paths as before.
The branch isolation is provided by git, not by the skill's awareness.

### Implication for tools

The `sulis-change` tool (CW-08) handles branch creation, worktree
provisioning, and merge-back. Skills invoked inside the worktree see
a normal repo with a normal current branch.

---

## CW-04: Two-Level Worktree Hierarchy (MUST)

A change worktree is the top level. Executor WP worktrees nest inside
it.

```
~/repo                              ← main (and dev tracked via fetch)
~/repo-change-create-payments       ← change worktree, branched off dev
  ├── (executor WP worktrees branch off the change branch, not dev)
  ~/repo-wp-001-payments-schema     ← branched off change/create-payments
  ~/repo-wp-002-payments-handler    ← branched off change/create-payments
```

The diagram above shows *worktree paths*; the *branch ref* shape is a
separate concern, stated next.

### WP branch refs (MUST)

A WP's *branch ref* is `wp/{primitive}-{slug}/wp-{nnn}-{slug}` — it nests
under `wp/`, NOT under the change branch's `change/{primitive}-{slug}`
prefix. Nesting a WP ref under the change branch is a git directory/file
conflict: `refs/heads/` cannot hold a ref at `change/foo` and a ref under
`change/foo/...` simultaneously. The `wp/` prefix carries the same change
identity without the conflict, so the train resolver scopes its branch glob
per-change and never matches a foreign change's recycled WP number. See
ADR-001 (change `wp-branch-collision`).

In-flight branches minted the old bare `feat/wp-{nnn}-{slug}` way during the
one-release compat window still resolve via the executor journal (which
records the exact pushed branch, any prefix); a WP under a change scope never
resolves to a foreign change's `feat/wp-{nnn}-*` branch. The bare `feat/`
glob survives one release only for legacy callers that supply no change
scope; its removal is a tracked follow-up.

### WP id labels (MUST)

A WP's *id label* is `{CH-HANDLE}-WP-NNN` (e.g., `CH-5DMB1N-WP-001`) — the
id-label twin of the branch-ref scoping above. The per-change `NNN` sequence is
unchanged (still the human-friendly 1/2/3 within a change); the `CH-HANDLE`
prefix makes the id globally unique across changes, so two changes can no longer
both mint a colliding bare `WP-001`. This closes for the *id* the same collision
class #283 closed for the *branch* — the two together retire cross-change WP
collisions for good.

Legacy bare `WP-NNN` ids minted before this change stay **understood for one
release**: the WP-id matcher recognises the prefixed shape, the legacy bare
shape, and the existing source-tagged `WP-{SOURCE}-{NNN}` shape from the same
parse, and there is **no migration pass** rewriting any existing committed id.
Dropping bare-id support is a tracked follow-up — the back-compat window closes
deliberately once the in-flight bare ids have drained, mirroring how the bare
`feat/` branch glob's removal is tracked above. See `WORK_PACKAGE_STANDARD.md`
WP-01 (the `id` row) and ADR-002 (change `unique-wp-ids`).

### What this means for the executor

The executor's `wpx-pipeline` and `wpx-train` are unchanged in
mechanics — they still branch off the *current* dev pointer. The only
change: in a change-bounded workflow, "current dev" from the executor's
perspective is the change branch (`change/create-payments`), not the
global `dev`. The executor's worktree branches off it; merges go back
into it; the train ships within the change.

When all the change's WPs are merged into the change branch and the
change is verified end-to-end, the change branch itself merges into
`dev`.

### What this means for the train

`wpx-train` runs *inside a change*. Its scope is the WPs on the
change branch. It batches them, rebases each onto the change branch
(not `dev`), bundled-tip CI on the change branch, sequential merge
into the change branch. The train is the per-WP integration layer
within a change; the change merge is the per-change integration layer
within `dev`.

### Auto back-integration (MUST — added in v1.1.0 Phase 4)

A change branch can sit out for hours or days while WPs ship through
it. Meanwhile, `dev` moves on (other founders, other changes, hotfix
deploys). The change branch needs to stay current with `dev` to avoid
accumulating a multi-day merge debt — but not so eagerly that
in-flight WP worktrees lose their base commit.

**Mechanism: merge, not rebase.** The change branch is updated from
`dev` via `git merge --no-edit origin/dev` — preserving commit SHAs so
any in-flight WP worktrees branched off the change branch's previous
tip remain valid. Rebase would rewrite SHAs and break those worktrees.

**Two trigger points (both MUST fire):**

| When | What runs | Why |
|---|---|---|
| After every WP merges back to the change branch | `git fetch origin dev && git merge --no-edit origin/dev` on the change branch; push | Active driver — keeps change branch within one WP of dev |
| Before every new WP starts (executor Step 0 arrival check) | Same merge invocation; fast no-op if change branch is already up-to-date | Defence in depth — catches teammate pushes to `dev` that happened between WPs |

Both together. After-merge is the active driver; before-WP is the
safety net for inter-WP `dev` motion.

**Conflict handling.** If `git merge origin/dev` on the change branch
fails:

- **Do not auto-resolve.** Pause the WP-in-flight and surface the
  conflict in founder English: *"Dev moved while you were working —
  there's a conflict in `src/auth.py` between your change and what was
  merged 12 minutes ago. Want me to walk you through resolving it?"*
- **Founder picks** one of three options:
  1. Resolve interactively (operator walks the conflict files)
  2. Abandon back-integration for now (continue on stale change
     branch; the conflict surfaces again next merge attempt)
  3. Abort this WP (`git reset` the WP branch; the WP is rebuilt
     after the change branch is current)

**Why this lives in CW-04.** The two-level worktree hierarchy CW-04
codifies makes back-integration possible (the change branch is the
integration point; updates flow into it without touching WP worktrees).
The auto back-integration mechanism is the operational rule that keeps
the hierarchy current.

See `lifecycle.md` Step 0 (arrival check) and Step 12.5
(post-WP back-integration) for the executor's per-step touchpoints.

---

## CW-05: Lifecycle — Start, Work, Finish (MUST)

Three operations, each owned by the `sulis-change` tool (CW-08):

### Start

```
sulis-change start {slug} [--primitive {primitive}]
```

Creates `change/{primitive}-{slug}` branched off the latest `dev`.
Provisions a worktree at `~/{repo-name}-change-{primitive}-{slug}/`.
Writes a one-line metadata file at `.changes/{primitive}-{slug}.yaml`
(or equivalent) on the change branch noting `started_at`, `primitive`,
`slug`, the dev SHA at branch.

### Work

No tool ceremony. The user works in the change worktree as a normal
repo. Skills, executors, the train all operate normally. Commits land
on the change branch.

### Finish

```
sulis-change finish {slug}
```

Rebases the change branch onto latest `dev`. Merges (or opens a PR;
configurable). On clean merge, removes the worktree, deletes the
local branch, optionally archives metadata.

### Trivial-change carve-out (SHOULD)

For changes too small to justify a branch — a typo fix, a one-line
config tweak, a comment edit — the user MAY work directly on `dev`.
The carve-out applies when **all three** of:

- Diff is ≤30 lines
- No new artifacts (no new SRD, TDD, WP, etc. produced)
- No code execution paths changed (text, comments, config-only)

This carve-out is documented because forcing every typo through a
worktree wastes more time than it saves.

---

## CW-06: One Project Per Change (MUST)

A change scopes to **one** project. Its branch may touch
`.specifications/payments/` OR `.architecture/orders/` — but not
both. Cross-project work is two separate changes.

### Why

- Reviewers can scope their attention to one project's artifacts
- The change-primitive captures the action on one subject
- Cross-project changes are usually two distinct evolutions wearing
  one branch — splitting forces the right boundary

### Multi-project work as two changes

If `change/create-payments` requires a small modification in `orders`,
that's a separate `change/extend-orders-for-payments`. The two changes
land independently; if they have a hard dependency, the dependent one
waits for the other to merge.

(This is the future-v0.2 inter-change coordination space; for v0.1.0
it's manual via "merge order".)

---

## CW-07: No Inter-Change Coordination Required (MUST — for v0.1.0)

For this v0.1.0 of the standard, **changes are independent**. No
coordination between change branches is required. Each branch merges
to `dev` on its own schedule.

### Implication

If `change/create-payments` and `change/refactor-orders` happen
simultaneously, they merge in whatever order they're ready. No
"change DAG" is maintained. No "Change B is blocked on Change A"
status is tracked.

### Why this is acceptable for v0.1.0

In practice, most parallel changes are independent — they touch
different projects, different domains, different artifact sets. The
overhead of tracking dependencies isn't justified until real practice
shows dependencies actually arising.

### When this assumption breaks

If real practice surfaces routine inter-change dependencies (e.g.,
Change B is consistently blocked on Change A landing), CW-07 becomes
wrong and a future v0.2.0 adds a change-level dependency layer.
That's a deferred concern.

---

## CW-08: Composition with Marketplace Standards (MUST)

CW slots between several existing standards. The composition contracts:

### With GIT-01..GIT-10 (Git Workflow)

GIT-01 defines the two-branch model (`dev`, `main`). CW-08 adds a
third layer: change branches live between them — `change/*` branches
off `dev`, merge back into `dev`. Promotion `dev → main` remains
ceremony-bounded per GIT-06. **CW does NOT change GIT-01..GIT-10**;
it extends the topology one layer up.

### With RC-01..RC-13 (Repository Contract)

RC-04 (branch protections), RC-05 (merge queue config on `dev`), RC-06
(required Actions workflows) apply unchanged. The merge queue on `dev`
batches change-branch merges the same way it batches WP merges today.

### With change primitives (`plugins/sulis/references/change-primitives.md`)

The 22-primitive vocabulary becomes load-bearing — it's the
`{primitive}` part of the branch name. Changes to the primitive
catalogue (additions, renames) require coordinated updates to CW-02's
allowed prefixes.

### With executor + train

The executor (`/sulis-execution:run-wp`) and the train (`wpx-train`)
now operate on the change branch, not `dev` directly. The contract:

- Executor reads `current dev SHA` to mean **the change branch's HEAD**, not `origin/dev`.
- WP branches branch off the change branch.
- The train's `dev` target for merges is the change branch.
- When the change is ready, `sulis-change finish` merges the change
  branch into the actual `dev`.

### With code-review and the PR Hygiene Standard

`/code-review` operates inside a change. It reviews a PR (or the whole
change branch) the same way it does today. PR Hygiene Standard
(PH-01..PH-08) measures the *change's shape*, not the train batch's.
The per-WP review still happens during execution; the per-change
review happens before merging the change to `dev`.

### With SRD and SEA artifact production

SRD and SEA write to their existing directories, unchanged. The change
branch is where those writes happen; the merge to `dev` is when other
work sees them.

---

## Calibration (CC + FR disclosure)

### Confidence tier

| Element | Tier | Basis |
|---|---|---|
| CW-01 Change as unit of work | SUPPORTED | OpenSpec + RFCs + PEPs + feature-branch workflows all converge here |
| CW-02 Branch naming with primitive | SUPPORTED | Conventional Commits + SEA's existing primitive vocabulary |
| CW-04 Two-level worktree nesting | UNVALIDATED | Novel synthesis; no prior literature packages this with WP-level worktrees |
| CW-05 Lifecycle commands | SUPPORTED | Direct adaptation of git worktree + the existing executor pattern |
| CW-06 One project per change | EMERGING | Asserted by analogy to "single responsibility CL" (Google); not yet empirically validated for cross-project changes |
| CW-07 No inter-change coordination | EMERGING | Deliberate v0.1.0 simplification; will revisit |
| **The synthesis as a whole** | UNVALIDATED | New standard; calibration determines whether this earns its keep |

### Falsification criteria

**STOP applying CW if:**
- After 90 days, ≥30% of changes need cross-change dependency tracking → CW-07 wrong; needs v0.2.0 with change-DAG
- ≥50% of changes are "trivial" (qualify for the CW-05 carve-out) → maybe the carve-out should be the default and changes are for bigger work only
- Branch lifetime averages >4 weeks → either changes are too big or the model breaks

**PIVOT if:**
- Two-level worktree nesting (CW-04) causes practical confusion (e.g., executors picking up the wrong "current dev") → revisit the nesting strategy

**RE-EVALUATE if:**
- An external standard emerges that subsumes this (e.g., OpenSpec extending into full lifecycle)

### Pre-mortem

If this standard fails after calibration, the most likely reasons:

1. **Change branches diverge from dev too quickly.** Without explicit
   rebase discipline, change branches accumulate merge debt.
2. **The primitive vocabulary becomes a friction.** Founders + agents
   spend more time choosing the right `change/{primitive}-...` prefix
   than the documentation benefit justifies.
3. **One-project-per-change forces artificial splits.** Real work
   often touches two projects; CW-06's "split into two changes" rule
   feels arbitrary.
4. **The trivial-change carve-out is the actual common case.** Most
   changes are small; the branching ceremony is overhead for most.

---

## Non-goals (deferred to v0.2+)

- **Change dependency graph.** Tracking "Change B blocked on Change A".
  v0.1.0 assumes independence per CW-07; v0.2.0 may add a `.changes/INDEX.md`
  with `dependsOn` edges if dependencies surface in practice.
- **Long-running changes / staging across multiple merges.** A change
  too big for one merge needs decomposition — but the decomposition
  pattern (linked-change-train? sub-change branches?) isn't specified
  yet.
- **Cross-project changes as a first-class concept.** Today CW-06
  forces a split; v0.2.0 may add explicit multi-project changes.
- **The `sulis-change` tool implementation.** This standard is design;
  the tool implementation is a separate ADR + work package.

---

## Anchor Cases

Production cases accrue here. Each anchor names the date, repo,
change, and what CW-NN rule(s) it exercised or stressed.

*(None yet — this is a greenfield standard.)*

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-05-21 | Initial standard. CW-01..CW-08 synthesised from OpenSpec, Conventional Commits, SEA change primitives, GIT-01..GIT-10. Greenfield — no anchor cases yet; 90-day calibration begins. |
| 0.2.0 | 2026-05-25 | **CW-04 amended (additive).** Auto back-integration subsection added — codifies the merge-not-rebase mechanism with two trigger points (post-WP-merge active driver + pre-WP-start safety net) and structured conflict handling (interactive resolve / defer / abort options). Operationalises what CW-04's two-level worktree hierarchy makes possible. Phase 4 of the change-as-primitive build; pairs with lifecycle.md Step 0 + Step 12.5 amendments. Backwards-compatible — existing change branches without auto back-integration continue to work; the new mechanism activates only via the Phase 5 executor implementation. |
| 0.3.0 | 2026-06-10 | **CW-04 amended (additive).** Added the **WP branch refs (MUST)** subsection — a WP's branch ref is `wp/{primitive}-{slug}/wp-{nnn}-{slug}`, nesting under `wp/` (not under the `change/{primitive}-{slug}` prefix, which would be a git directory/file ref conflict). Scopes the train resolver's branch glob per-change so it cannot match a foreign change's recycled WP number (change `wp-branch-collision`, root cause of #105/#106; see ADR-001). Backwards-compatible — legacy bare `feat/wp-{nnn}-{slug}` branches still resolve via the executor journal + a one-release glob fallback for no-scope callers; fallback removal is a tracked follow-up. |
| 0.4.0 | 2026-06-10 | **CW-04 amended (additive).** Added the **WP id labels (MUST)** subsection — the id-label twin of the WP branch-ref scoping: a WP's id label is `{CH-HANDLE}-WP-NNN`, the `CH-HANDLE` prefix making the id globally unique across changes while the per-change `NNN` sequence is unchanged. Closes for the id label the same cross-change collision class #283 closed for branches (change `unique-wp-ids`, CH-5DMB1N; see ADR-002). Backwards-compatible — legacy bare `WP-NNN` and source-tagged `WP-{SOURCE}-{NNN}` ids stay understood for one release (no migration); bare-id-support removal is a tracked follow-up. |
