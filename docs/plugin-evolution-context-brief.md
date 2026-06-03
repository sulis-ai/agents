# Context brief: Sulis plugin evolution (handoff to the thread owner)

> **You are:** the agent owning the *main thread of context* for how the Sulis plugin + marketplace evolves — versioning, distribution, deployment model, and the migration to trunk-based. This brief is your orientation: the verified state, the decision taken, what's been ruled out (so you don't re-litigate), the open threads, and the hard constraints.
> **Authored:** 2026-06-02, after a long investigation into why a shipped release wasn't reaching consumers. Facts tagged **[verified]** were tested live this session.
> **Companion docs (read both):**
> - `claude-code-plugin-distribution-brief.md` — the mechanical truths about Claude Code marketplaces (version resolution, SSH clone, source schema).
> - `sulis-distribution-and-deployment-design.md` — the design options (Model A/B) + migration paths + the deployed-product (build-once-deploy-many) model.

---

## 1. The situation in one paragraph

Sulis is distributed as a Claude Code plugin via the `sulis-ai/agents` marketplace. The marketplace reads `marketplace.json` from the repo's **default branch**, which is **`dev`** — the integration branch. So consumers install unreleased `dev` content, and version bumps (which land on `main` via the release robot) never reach them. v0.88.0 shipped to `main` on 2026-06-02 but **consumers still see 0.87.0**. The founder has decided to fix this structurally by moving to **trunk-based development (Model A): `main` becomes the single default + integration + release branch.** The migration has not yet started.

---

## 2. Verified current state (2026-06-02)

| Fact | Value |
|---|---|
| Repo | `sulis-ai/agents` (**public**) |
| Default branch | **`dev`** [verified] |
| `dev` `plugin.json` | **0.87.0** [verified] |
| `main` `plugin.json` | **0.88.0** [verified] |
| Umbrella version (`main`) | 1.133.0 · latest tag `v1.133.0` [verified] |
| `sulis` marketplace source | relative `"./plugins/sulis"` (https-safe) on both branches [verified] |
| What consumers get today | **0.87.0** (they read `dev`); v0.88.0 is **stranded on `main`** |
| In-flight `change/*` branches | **70** [verified] |
| Content commits on `dev` not on `main` | 53 (incl. the **Scenario verification engine** — ~2,600 lines, genuinely unreleased) |
| Changesets on `dev` | 30 — **but most were already consumed into v0.88.0 on `main`**; only ~2 are genuinely new (`chore-vendor-scenario`, `create-testable-state-done`). See §8. |

---

## 3. The decision taken

**Model A — trunk-based.** Target end-state:
- `main` = default branch = integration = release line. **No long-lived `dev`.**
- Short-lived feature/change branches → `main`, gated by CI + the change/review/ship discipline.
- Releases are **tags** on `main`. Consumers read `main` (default) → relative source → released version, https-safe. The "marketplace reads the default branch" behaviour becomes *correct by construction*.
- Staging/canary, if ever needed, is a **release channel** (separate repo/default-branch), never a branch-per-environment.

Rationale: it's the dominant industry convention, needs zero new infrastructure, and dissolves the whole problem class (stranded releases, dev-resync, SSH pinning, squash/ancestry drift). Full reasoning in the design doc §3–4.

---

## 4. Ruled out — do not re-litigate (with the killing reason)

| Option | Why it's dead |
|---|---|
| **Pin the plugin `source` to a github ref/tag (`main`)** | `github`-typed plugin sources clone over **SSH** (`git@github.com`); fails for https-only consumers — **[verified] on this machine** (no SSH keys; install failed `Permission denied (publickey)`). Tried, deployed (PR #149), and **reverted (PR #150)** because it broke install. |
| **`{source: "git", url: "https://…"}`** | "source type your Claude Code version does not support" [verified]. |
| **Catalog `version` field as the fix** | The catalog `version` field is **ignored** for resolution; the plugin's own `plugin.json` on the source ref governs [verified: catalog 9.9.9 lost to plugin.json 1.0.0]. |
| **Keep `dev`/`main` AND make `main` default** | GitHub couples default branch ↔ default PR base (no separate setting). Making `main` default forces PRs to base on `main` while work merges to `dev` — "poor ergonomics." Only coherent if you drop `dev` (i.e. go full Model A). |
| **Branch-per-environment** (`dev`/`staging`/`prod` branches → envs) | Named anti-pattern; branches model temporary divergence, environments are permanent difference. Use artifact promotion + config, not branches. |

---

## 5. Open threads / live decisions

1. **Sequencing the migration (FOUNDER LEANS: release-first).** Recommended: (a) one final `dev→main` release (→0.89.0) so `main` is content-complete incl. the Scenario engine, (b) flip default to `main`, (c) new work branches from `main`, (d) triage the 70 branches, (e) simplify the robot. Alternative: flip now at 0.88.0, release the Scenario work next cycle. **Awaiting the founder's call between these.**
2. **v0.88.0 is still un-delivered** — resolved by step (a)/(b) above under either sequencing.
3. **The 70 `change/*` branches** — need triage: delete stale (most look like old experiments), rebase live ones onto `main`. **Gradual, not big-bang.** Not on the critical path.
4. **Release-robot simplification** — once on trunk, drop the `dev→main` promotion PR + auto-back-merge + the ancestry drift guard; releases become a tag on `main`. Deferred until after the cutover.
5. **GitHub Release page** — the robot tags but does not publish a Release *page* (issue #148). Decide whether to wire `gh release create` in.

---

## 6. Hard constraints & gotchas (carry these forward)

- **Version comes from `plugin.json` on the source ref, not the catalog `version` field.** [verified]
- **Relative sources are the only https-safe option.** Any `github`/tag-pinned source = SSH = breaks https consumers. [verified]
- **`/plugin update` does not refresh the marketplace clone** (issue [#35752]); always `/plugin marketplace update <name>` first, or it reports "already at latest" against a stale clone. [verified — it bit us]
- **Can't pin a marketplace *registration* to a non-default branch** (issue [#23551], open). The default branch *is* the distribution line.
- **Repo is squash-merge-only** (`allow_merge_commit=false`, `allow_rebase_merge=false`) [verified]. This is why `dev→main` squash-releases diverge the branches and the ancestry drift guard then blocks the next change. Trunk-based removes this pain.
- **`dev` is protected** (PR reviews + `branch-ci` required; `enforce_admins=false` so an admin can override). `main` has no required checks.

---

## 7. Companion artifacts & filed issues

- Design + migration: `docs/sulis-distribution-and-deployment-design.md`
- Mechanics reference: `docs/claude-code-plugin-distribution-brief.md`
- GitHub issues filed this session (all on `sulis-ai/agents`):
  - **#151** — github plugin sources clone over SSH; blocks https pinning (the load-bearing finding).
  - #147 — squash-only repo + ancestry drift guard makes post-release `dev` re-sync impossible via PR.
  - #148 — release robot tags but doesn't publish a GitHub Release page.
  - #141–144 — build-tooling lessons (stale local clone, wrap-step idempotency, INDEX summary drift, 10 pre-existing worktree-lifecycle test failures).

---

## 8. The `dev`/`main` tangle (a real risk for the next release)

`dev` and `main` have **diverged**, not just by version. The v0.88.0 release squashed `dev`'s then-content into `main` and **deleted the consumed changesets on `main` only** — `dev` still carries those ~28 already-released changesets *plus* ~2 genuinely-new ones. So:
- A naive "run the release train on `dev`" would **re-process already-released changesets** and miscompute the next version.
- Before the final `dev→main` release (migration step a), reconcile the changeset set: the next release should bump only for the genuinely-new work (the Scenario engine / testable-state, tier ≈ minor → 0.89.0), not re-count the 28.
- This tangle is *the* reason to stop doing `dev→main` squash-promotion at all — which trunk-based achieves. Treat the final release as a careful one-off, then retire the machinery.

---

## 9. Working principles for this thread

- **Verify, don't assume.** This whole investigation existed because authoritative-looking web docs were *wrong* about version resolution, and a "validated" fix (#149) was only validated under a hidden git config that masked the SSH failure. Test against the live `claude plugin` CLI before concluding.
- **Founder owns the irreversible/shared calls:** changing the default branch, force-updating shared branches, release timing, and how the dev/main cutover sequences. Bring these as decisions, not faits accomplis.
- **Don't big-bang the 70 branches.** Triage gradually; deleting someone's WIP is hard to undo.
- **`main` has no required checks** — be deliberate about what lands there once it's the trunk; the discipline that protected `dev` (branch-ci) needs re-applying to `main`.
- **The goal is to delete machinery, not add it.** Trunk-based should *remove* the promotion PR, back-merge bot, and ancestry guard. If a step adds complexity, question whether it's fighting the model.

---

## 10. Immediate next action

Get the founder's sequencing call (§5.1): **release `dev`→`main` first (→0.89.0, after reconciling the changeset tangle in §8) then flip the default to `main`** — vs flip now at 0.88.0. Then execute the cutover, leaving branch-triage and robot-simplification as deliberate follow-ups.
