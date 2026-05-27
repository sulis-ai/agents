# Lessons — cockpit-mvp execution (CH-01KSJA)

> **Source:** the first real end-to-end exercise of the four standards +
> change-as-primitive execution, building the cockpit MVP (a local-only
> React + Node read-only review tool) in this repo.
> **Captured:** 2026-05-27, post-implement, from the bound session's
> retrospective.
> **Why this file exists:** the post-ship lessons-capture step (the
> mechanism this run motivated) isn't built yet — this is the manual
> first instance. `.architecture/` is gitignored (lesson #6), so the
> durable home for lessons is `docs/lessons/`, which travels with the repo.

Each lesson carries a disposition per the finding-triage policy
(`sulis.md` → Decision Discipline → Finding-triage policy):
**fix-now (CW-05)** / **task** / **SEA** (substantive, needs a spec).

---

## Genuine tooling bugs

### L-01 — `resolve_current_change()` returns null at startup · SEA
Returned `null` despite `SULIS_CHANGE_ID` set + a valid change branch +
manifest existing. The bound session fell back to reading
`.changes/create-cockpit-mvp.yaml` directly. The whole change-context
greeting flow depends on this resolving — real miss.
*Disposition: SEA (needs investigation — env-var read, manifest lookup,
or branch resolution).* → **Cluster A**

### L-02 — Two tools disagree on the INDEX column name, unresolvably · SEA
`wpx-index list-ready` requires the column lowercased to exactly
`depends`; `_wpxlib.parse_index_md` (used by `wpx-train` + `wpx-index
status`) requires `depends on`. **No single header satisfies both.** The
architect emitted `Depends on` (correct for the hot path) which silently
broke `list-ready`. Internal schema inconsistency — the two parsers must
share one normaliser.
*Disposition: SEA (shared normaliser).* → **Cluster A**. Highest value
(blocks any change from running).

### L-03 — Producer emits `Status: ready`; every consumer expects `pending` · SEA
`plan-work`/architect emits `ready`; `list-ready` filters for `pending`,
`wpx-train` eligibility checks `pending` — `ready` is invisible to all of
them. The decomposition was **un-runnable as shipped** until 16 rows + 16
frontmatters were migrated `ready → pending` by hand. Producer (plan-work)
and consumers (wpx-*) must agree on the initial-status vocabulary.
*Disposition: SEA (producer/consumer contract).* → **Cluster A**. Highest
value (blocks any change from running).

### L-04 — `wpx-worktree create` hardcodes `origin/dev` as base · SEA
No support for CW-04 change branches. Every executor dispatch (~10) needed
a manual `git worktree add -b … origin/change/…` + hand-written sidecar.
The worktree helper doesn't know change branches exist.
*Disposition: SEA (change-branch awareness in the worktree helper).*
→ **Cluster A**

### L-05 — run-all/wpx-train doesn't fit a `deploy_target: none` repo · SEA
The train requires `--deploy-workflow` and is built around
deploy→health→smoke. This is a published-artifact marketplace — `dev` is
the release surface. The bound session hand-drove the whole dispatch loop
(flip status → dispatch → merge-to-change-branch → flip done) instead of
the train. No clean "published-artifact, merge-to-change-branch, no-deploy"
mode.
*Disposition: SEA — **already logged as task #39.*** → **Cluster A**

## Hygiene / model gaps

### L-06 — `.architecture/` is gitignored — audit trail doesn't travel · TASK
Every WP journal, code-review bundle, and sidecar lives only locally and
never travels with the branch. The hybrid-storage promise
("reviewable in one PR") is half-met: `.changes/` manifest + spec travel,
the architecture audit trail doesn't. **Policy call needed:** should the
WP journals + review bundles travel with the change branch?
*Disposition: task (policy + .gitignore decision).*

### L-07 — Sidecar files aren't gitignored · FIX-NOW (CW-05)
`.wpx-base-sha` got swept into a worktree commit and nearly leaked onto
dev — caught at the squash. The `.executor-*-dev-sha` / `.wpx-base-sha`
family must be in `.gitignore`.
*Disposition: fix-now — pure CW-05.* **Fixed in this commit.**

### L-08 — Parallel dispatch can't honour EP-03 (extract-shared-primitive) · SEA
Two parallel executors independently built the same `relativeTime` helper
(one in `utils/`, one in `components/` — which then case-collided on
macOS); WP-006/WP-007 both appended classes to `errors.ts` and conflicted.
The shared-primitive rule can't fire across two simultaneously-running
worktrees. **Decomposition lesson:** shared utilities should be their own
**upstream WP**, not left to be discovered inside two parallel siblings.
*Disposition: SEA — a `plan-work` amendment (hoist shared primitives to an
upstream WP before parallel siblings).* → **Cluster C**

## Session slips (not the plugin)

- Backticks in a commit-message body got eaten by the shell. Use plain
  quotes in commit bodies.
- First wrote `d['data']['wps']` against `wpx-index status` when the key is
  `entries` — output schema wasn't where assumed.

---

## Triage summary

| Cluster | Lessons | Disposition |
|---|---|---|
| **A — executor doesn't fit change-branch + published-artifact model** | L-01, L-02, L-03, L-04, L-05 | One SEA change (highest value; L-02 + L-03 block any change from running un-surgically). L-05 = task #39. |
| **B — hygiene** | L-06 (task), L-07 (fixed now) | L-07 done; L-06 needs a policy call. |
| **C — decomposition method** | L-08 | `plan-work` amendment (shared primitive → upstream WP). |

Priority order from the bound session: **L-03 + L-02** (block runs), then
**L-04 + L-05** (change-branch execution model), then **L-01**.

---

## Post-ship test findings (2026-05-27, during "ship it and test it")

### L-09 — `npm run dev` ran `vite` from the wrong root; client never served · FIXED
The `dev`/`dev:client` scripts ran bare `vite` from the package root, but
`index.html` + `client/vite.config.ts` live in `client/`. Vite booted ("ready")
but 404'd on every path — the documented dev-run never served the UI. **CI's
E2E passed** because Playwright's webServer points Vite at the right root,
masking the broken dev-run. Lesson: a green E2E gate doesn't prove the
*documented* dev-run works — they're different invocations. Fix: `vite` →
`vite client` (positional root) in both scripts. Verified end-to-end:
`npm run dev` → client 200 + `<title>Sulis cockpit</title>`, server 200.
*Disposition: fixed in this commit (CW-05).*

### L-10 — ship-flow chained cleanup to an unconfirmed merge · covered by #38
The cockpit had already squash-merged to dev at 00:12 (3711658), but the
change store still showed it "ready to ship" (the #38 auto-cleanup gap) — so
a re-ship was attempted, and the command chain ran `nuke` before confirming
the (rejected, redundant) merge succeeded. No harm (work was safe on dev +
remote), but the ship flow MUST: (a) detect already-merged changes before
re-shipping, (b) only clean up after a confirmed-successful merge. Folds into
#38.

### Note — demo seed
A demo change record (CH-DEMO01, pointing at the repo root) was seeded into
the local store for the visual test; it is not a real change and should be
removed after the browser walkthrough.
