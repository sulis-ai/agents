# CI/CD Batching Analysis — per-WP vs. per-batch pipeline stages

**Date:** 2026-05-19
**Author:** synthesised from code-read + web research
**Status:** Analysis & recommendation; no code changed yet
**Skill invoked:** `/idc:market-research` (pivoted to technical research — pitch-deck market evidence not applicable to this question)

---

## TL;DR (read this first)

You're right that per-WP integration + deployment carries real overhead. The
established convention for the problem you're describing is **the merge queue
with speculative batch CI** — pioneered by Bors (Rust), industrialised by
Shopify's Shipit, productised by GitHub Merge Queue and GitLab Merge Trains.
Adopt it; don't invent a new concept.

The natural batch unit already exists in SEA's output — it's the **topological
level of the WP DAG** (the "Recommended Implementation Order" sections in
INDEX.md). No new SEA primitive needed. Each level is the set of WPs that
become unblocked at the same time, and within a level WPs are by construction
non-overlapping (SEA guarantees disjoint file-scope at decompose time). That's
the exact precondition a merge queue needs.

The split that matches the convention is:

| Today (per-WP) | Tomorrow (mixed) |
|---|---|
| Steps 1–7 per-WP | Steps 1–7 **stay per-WP** |
| Step 8 (CI poll + squash-merge) per-WP | Step 8a (fast branch CI) **per-WP**; Step 8b (full integration CI on speculative merged ref) **per-batch** |
| Step 9 (deploy) per-WP | Step 9 **per-batch** — one deploy per topological level |
| Step 10 (health + smoke) per-WP | Step 10 **per-batch** — one health window per level |
| Step 11 (security review) per-WP | Step 11 **per-WP, parallel** after batch deploy (each WP's DoD stays distinct) |
| Step 12 (cleanup) per-WP | Step 12 **per-WP** |

Wall-clock saving is modest (the orchestrator already parallelises today).
The real saving is **CI compute (N→1)**, **deploy events (N→1)**, **rollout
risk surface (N→1)**, and **observability noise (N→1)** per level.

---

## Scope & questions

**Primary question.** Today every Work Package runs the full 12-step lifecycle
end-to-end. Can we chunk integration + deployment above the WP boundary while
keeping local TDD per-WP? If so, what's the natural batch unit, and what does
the established CI/CD convention say?

**Sub-questions.**
1. What does SEA already produce that could serve as a batch boundary?
2. Which sulis-execution steps are local (cheap, must stay per-WP) and which
   are global (expensive, candidates for batching)?
3. What's the established industry convention? (CP-01: never go neutral; name it.)
4. What's the concrete proposed structure, and what are the trade-offs?

---

## Part 1 — SEA produces a DAG, not a hierarchy

I read `plugins/sea/agents/engineering-architect.md`,
`plugins/sea/skills/decompose/SKILL.md`, and
`plugins/sea/references/change-primitives.md` end-to-end.

**Finding 1 — There is no "slice" or "phase" concept above WP.** SEA's
decompose output is a flat list of Work Packages with `dependsOn` / `blocks`
edges between them. The organising structure is the DAG itself.

**Finding 2 — The DAG has natural topological levels.** Every INDEX.md emits
a "Recommended Implementation Order" section that's a topological sort of
the WP graph. Example from `decompose/SKILL.md:284-286`:

```
1. WP-001
2. WP-002, WP-003   ← parallel; both depend only on WP-001
3. WP-004, WP-007, WP-008   ← parallel; depend on WP-003
```

Each numbered line is a **level**. Within a level, WPs are independent (no
edges between them, disjoint file-scope). Between levels, the lower level
must merge to `dev` before the higher level can start.

**This is the batch unit.** A level is exactly what a merge queue wants —
N independent changes that need integration testing as a group before
deployment.

**Finding 3 — Change primitives cluster by deployment risk.** From
`change-primitives.md`:

| Group | Primitives | Risk profile |
|---|---|---|
| **EXPAND** | Reuse, Compose, Extend, Generate, Create | Low–Medium (new code, existing tests cover reused pieces) |
| **REORGANISE** | Move, Refactor, Inline, Merge, Decompose, Abstract | Medium–High (characterisation test **mandatory**) |
| **SUBSTITUTE** | Replace, Strangle, Wrap | Medium–High (Strangle requires removal plan) |
| **CONTRACT** | Deprecate, Delete | Low if Deprecate-first; High if Delete-without-Deprecate |
| **REINFORCE** | Test, Instrument, Secure, Harden, Gate, Document | Orthogonal — low individual risk |

This suggests risk-shaped batch sizing: mixed-primitive batches of 4–5 are
safe; same-primitive REORGANISE / SUBSTITUTE batches should be smaller (2–3);
Delete WPs are best run as singletons.

---

## Part 2 — Per-WP step inventory

From `plugins/sulis/references/lifecycle.md` and
`plugins/sulis/agents/executor.md`. Each step labelled LOCAL (in
the worktree, no external infra) or GLOBAL (polls external CI / deploy /
health), with qualitative cost estimate.

| Step | Stage | Local/Global | Cost | Batching candidate? |
|---|---|---|---|---|
| 1 | Worktree + branch | LOCAL | seconds | No — must be per-WP for isolation |
| 1.5 | Plan generation | LOCAL | 1–2 min | No — scope-guard per-WP |
| 2 | RED (failing tests) | LOCAL | 5–15 min | No — TDD is per-WP |
| 3 | GREEN (minimum impl) | LOCAL | 10–30 min | No |
| 4 | BLUE (refactor) | LOCAL | 5–20 min | No |
| 5 | Docs update | LOCAL | 0–10 min | No |
| 6 | Lint / type / format | LOCAL | 2–10 min | No — fast, per-WP feedback |
| 7 | Commit + push | LOCAL | 1–5 min | No |
| **8** | **CI poll + rebase + squash-merge** | **GLOBAL** | **15–45 min** | **Yes — split into 8a (branch CI per-WP) + 8b (integration CI per-batch)** |
| **9** | **Deploy poll** | **GLOBAL** | **5–15 min** | **Yes — one deploy per batch** |
| **10** | **Health + smoke** | **GLOBAL** | **5–20 min** | **Yes — one health window per batch** |
| 11 | Security review | GLOBAL | 5–15 min | Partial — runs per-WP (per-WP DoD) but spawned in parallel after batch deploy |
| 12 | INDEX flip + cleanup | LOCAL | 1–3 min | No |

**Total GLOBAL overhead per WP today:** ~30–95 min (Steps 8 + 9 + 10 + 11).
For a 5-WP topological level today: 5 × CI runs, 5 × deploy events, 5 ×
health-check windows, 5 × security review spawns. With batching: 1 × of each
(except Step 11 which stays per-WP but runs concurrently).

---

## Part 3 — The established convention

CP-01: name the convention, don't present a neutral menu.

**The convention is the merge queue with speculative batch CI.** Origin:
Bors (Rust, 2014), to keep `master` always green. Industrialised at scale
by Shopify (1000+ developers, 400+ commits/day to master) with their
open-source `Shipit` tool. Productised by GitHub (GitHub Merge Queue, 2023+
GA) and GitLab (Merge Trains).

### The pattern (from the [Shopify post](https://shopify.engineering/successfully-merging-work-1000-developers) and [GitHub Merge Queue docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue))

1. **Per-PR (fast feedback).** Branch CI runs the cheap stuff on every push:
   linting, unit tests, type-checking, smoke tests. Target ≤10–15 min.
   This gate keeps PRs unmergeable until they're individually green.
2. **Queue entry.** When a PR is approved + branch-CI green, it enters the
   merge queue. The PR is now in line, not yet merged.
3. **Speculative batch.** The queue manager creates a synthetic merge
   commit containing the next N queued PRs merged together on top of `main`.
   N is the batch size (Shopify: 8; GitHub default: 5; debugg.ai advice: start
   at 3–4).
4. **Batch CI.** Full integration / e2e / slow tests run on the synthetic
   ref via the `merge_group` event. This is the expensive run — but it's
   amortised across N PRs.
5. **Atomic batch result.**
   - **Green:** all N PRs squash-merge to `main` at once. Single CI compute,
     single deploy event downstream.
   - **Red:** bisect. Split the batch in half, re-run CI on each half,
     recursively isolate the failing PR(s). O(log N) extra CI runs. Failed
     PRs are ejected; remaining PRs re-batch.
6. **Failure tolerance.** Shopify tolerates K successive failures of the same
   PR before ejection (Shopify uses 3, based on a 25 % flake rate empirically
   observed). This prevents flake from punishing good PRs.

### Concurrency

Shopify runs **3 batches concurrently** ("at any given time, we run CI on 3
batches worth of pull requests"). GitHub Merge Queue lets you configure
"max entries to build" similarly.

### DORA finding (and why it doesn't undermine this)

[DORA's State of DevOps](https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment)
shows that elite performers deploy frequently with short lead time and low
failure rate — i.e., **don't** batch deployments into release trains.

**This doesn't contradict the merge queue pattern.** The merge queue
preserves continuous deployment semantics from the developer's point of view
(every PR is independently mergeable, no fixed release window) while
amortising the **CI cost** of full integration testing across N changes.
The PR-author lead time goes up by minutes (waiting for the batch ahead),
not days (waiting for the next release train).

What the DORA finding does undermine is **traditional release trains** —
fixed Tuesday/Thursday deploy windows where multiple weeks of changes ship
together. That's a different pattern and is **not** what's being proposed
here.

### Monorepo affected-only builds (orthogonal optimisation)

[Nx affected](https://nx.dev/) and [Turborepo filtering](https://turbo.build/)
add another layer of saving — only run CI for projects whose dependency
graph was actually touched. Bazel does the same via the build graph. This
composes with batching: per-batch CI runs only the affected test sets, not
the whole suite. One [50-developer monorepo reported skipping 80% of tasks](https://dev.to/alex_aslam/turbocharge-your-monorepo-battle-tested-tips-for-nx-turborepo-and-bazel-pros-214h)
this way.

---

## Part 4 — Recommendation

### The batch unit

**Use SEA's existing topological-level structure.** No new primitive needed
in SEA. The `/sulis:run-all` orchestrator already walks the INDEX
DAG and identifies the unblocked-WP set per level — that set **is** the
batch.

### The pipeline split

```
Per-WP (executor agent, Steps 1-7) — unchanged
  ├─ Worktree + plan
  ├─ RED-GREEN-BLUE
  ├─ Docs + lint
  └─ Commit + push to feat/wp-NNN

Per-WP (Step 8a, NEW — fast branch CI) — runs in CI per push
  └─ Lint + unit tests + type-check + smoke
     Target ≤15 min. Gate: must be green before queue entry.

Per-batch (Steps 8b + 9 + 10 — merge queue) — runs once per topological level
  ├─ Speculative merge: synthetic ref = dev + WP-A + WP-B + ... + WP-N
  ├─ Full integration / e2e CI on the synthetic ref via merge_group event
  ├─ On green: squash-merge all N WPs to dev atomically
  ├─ Deploy the merged batch (one Sulis SDK deploy event)
  ├─ Health-check the deployed batch (one window)
  └─ Smoke-test the deployed batch (one run)

Per-WP (Step 11) — runs in parallel after batch deploy succeeds
  └─ Spawn sulis-security:security-reviewer per WP
     Each WP's DoD is distinct; semantic stays per-WP.

Per-WP (Step 12) — runs after Step 11 verdict
  └─ INDEX flip + acceptance evidence + worktree cleanup
```

### Risk-shaped batch sizing

Emit a `batch_hint` field per WP from `sea:decompose` based on primitive group:

| Primitive group | Suggested batch size |
|---|---|
| EXPAND-only batch | 5–8 |
| REINFORCE-only batch | 5–8 |
| Mixed EXPAND + REINFORCE | 5 |
| REORGANISE-heavy | 2–3 |
| SUBSTITUTE-Strangle | 2 |
| SUBSTITUTE-Replace | 3 |
| CONTRACT-Delete | **1 (singleton)** |
| CONTRACT-Deprecate | 3 |

The orchestrator reads `batch_hint`, packs WPs into batches respecting both
the DAG level **and** the risk-group ceiling. A 6-WP level with 4 EXPAND + 2
REORGANISE WPs can split into two batches: one batch of 4 EXPAND, one batch
of 2 REORGANISE.

### Failure handling

Adopt Shopify's pattern verbatim:
- On batch CI failure, bisect (O(log N) extra CI runs)
- Tolerate K=3 successive failures of the same WP before ejection (covers flake)
- Ejected WP becomes a BLOCKER (existing primitive); remaining batch re-tests
- On batch deploy/health failure, roll back the entire batch (it's atomic by
  construction; no partial state)

### Where this lives in the code

- **`sea:decompose`** — emit `batch_hint` field per WP (1-line config change
  in the WP template)
- **`/sulis:run-all` orchestrator** — already walks the DAG; adds
  a "pack into batches respecting batch_hint" step before dispatching to
  executors
- **`wpx-pipeline`** — split Step 8 into 8a (branch CI per-WP) and 8b
  (merge-group CI per-batch). The merge_group event hook is new.
- **GitHub Merge Queue** — enable on the `dev` branch; configure max group
  size = 8, status-check timeout = 60 min, failure tolerance = 3.
  Free with GitHub Actions.
- **Step 9-10** — `wpx-pipeline` polls per-batch instead of per-WP.
  The polling primitives already exist; the looping is the change.

---

## Trade-offs you're choosing between

| Today (per-WP) | Proposed (merge queue + per-batch deploy) |
|---|---|
| ✓ Maximum throughput per-WP (no waiting on batch peers) | ✗ A WP waits for its batch (minutes, not days) |
| ✓ Simple orchestration (parallel dispatcher) | ✗ More complex (queue manager + bisection) |
| ✗ N× CI compute per level | ✓ 1× CI compute per level (with O(log N) on failure) |
| ✗ N× deploy events per level | ✓ 1× deploy event per level |
| ✗ N× health windows per level | ✓ 1× health window per level |
| ✗ N× rollback decisions per level | ✓ 1× rollback decision per level (batch-atomic) |
| ✓ One failing WP blocks only itself | ✗ One failing WP can hold up its batch peers (until ejected via failure-tolerance) |
| ✗ Hard to attribute health-check regressions to specific WPs (since deploys overlap) | ✓ Clear attribution: a regression points to one batch (then bisect within) |

The decisive question is **CI compute cost**. If your CI minutes are
metered and a single WP CI run is non-trivial, the savings compound fast.
At Shopify's scale (400 commits/day) the merge queue was load-bearing for
cost AND reliability. At your scale today the cost saving is smaller but
the reliability and observability win is the same — one rollout window per
level, not N.

---

## Where this report stops short

- **Concrete CI minute cost calculation.** I don't have your current CI
  pricing or per-WP CI duration. If you give me a recent CI run's duration
  and your minutes/month budget, I can put concrete numbers on the
  before/after.
- **GitHub Merge Queue specifics for your repo.** I haven't checked your
  `.github/workflows/` for `pull_request` vs `merge_group` event triggers.
  Migrating requires re-tagging some workflows.
- **Whether `sea:decompose` already emits enough for batch packing.** I
  read the skill end-to-end; `batch_hint` is a new field. Could also be
  inferred at the orchestrator from `primitive` + `dependsOn` without a
  schema change.
- **Concrete Work Package proposal for the migration.** The next move is
  `sea:blueprint` on this analysis to produce a TDD + decomposed WPs for
  the migration itself.

---

## Sources

**Codebase reads:**
- `plugins/sea/agents/engineering-architect.md`
- `plugins/sea/skills/decompose/SKILL.md` (lines 206-288 INDEX.md structure;
  lines 284-286 topological order example)
- `plugins/sea/references/change-primitives.md` (22 primitives, 5 groups)
- `plugins/sulis/references/lifecycle.md`
- `plugins/sulis/agents/executor.md`

**Web research:**
- [Shopify Engineering — Successfully Merging the Work of 1000+ Developers](https://shopify.engineering/successfully-merging-work-1000-developers)
- [Shopify Engineering — Introducing the Merge Queue](https://shopify.engineering/introducing-the-merge-queue)
- [GitHub Docs — Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [GitHub Docs — Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
- [Mergify — The Origin Story of Merge Queues](https://mergify.com/blog/the-origin-story-of-merge-queues/)
- [Mergify — Merge Queue Batches](https://docs.mergify.com/merge-queue/batches/)
- [debugg.ai — Merge Queues / Release Train 2025: batched commits, auto-reverts, CI bisection](https://debugg.ai/resources/merge-queues-release-train-2025-batched-commits-auto-reverts-ci-bisection-green-main)
- [bors-ng/bors-ng on GitHub](https://github.com/bors-ng/bors-ng)
- [Tenki — GitHub Merge Queue in 2026: How It Works & Handling Flaky Required Status Checks](https://tenki.cloud/blog/github-merge-queue-setup)
- [Atlassian — Continuous integration vs. delivery vs. deployment](https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment)
- [SRE School — What is Release train?](https://sreschool.com/blog/release-train/)
- [Codefresh — The Pain of Infrequent Deployments, Release Trains and Lengthy Sprints](https://codefresh.io/blog/infrequent-deployments-release-trains-and-lengthy-sprints/)
- [DEV Community — Turbocharge Your Monorepo: Nx, Turborepo, Bazel](https://dev.to/alex_aslam/turbocharge-your-monorepo-battle-tested-tips-for-nx-turborepo-and-bazel-pros-214h)
- [Nx — Affected commands documentation](https://nx.dev/)
- [arXiv — Improving Merge Pipeline Throughput in Continuous Integration via Pull Request Prioritization](https://arxiv.org/html/2508.08342v1)
- [Harness DevOps Academy — What is Continuous Integration?](https://www.harness.io/harness-devops-academy/what-is-continuous-integration-ci)
- [GitHub Shopify/shipit-engine](https://github.com/Shopify/shipit-engine)
