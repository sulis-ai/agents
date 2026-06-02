# Sulis: distribution + deployment design (concrete sketch + migration)

> **Scope:** how `sulis-ai/agents` (the plugin) should be versioned, distributed, and — for the products Sulis *builds* — deployed. Grounded in the verified findings from the 2026-06-02 investigation (see `claude-code-plugin-distribution-brief.md`).
> **Status:** proposal for the founder to choose between. Two target models; one recommendation.

---

## 1. Where you are now (and why it hurts)

```
feature/change branch ──ship──▶ dev (default, integration)
                                  │  /sulis:release-train opens PR
                                  ▼
                                main (release line)
                                  │  release-on-merge robot:
                                  │  bumps plugin.json + marketplace entry + umbrella,
                                  │  assembles CHANGELOG, deletes changesets, tags v<umbrella>
                                  ▼
                                (consumers ??? )
```

**The break:** the Claude Code marketplace reads `marketplace.json` from the repo's **default branch = `dev`**. So:
- Consumers install **`dev`** content (unreleased, churning) — not releases.
- The version bump lands on **`main`**; it never reaches consumers unless back-merged onto `dev`.
- Pinning the plugin source to `main` to fix this **fails over https** (github plugin sources clone via SSH — verified dead).
- Squash-merge `dev→main` diverges the branches; the drift guard (ancestry) then blocks the next change until a force-resync.

**Root cause:** `dev` and `main` are being used to model *both* integration *and* environment/distribution. The two roles conflict. Every symptom this week is a facet of that.

---

## 2. The principle to design toward

**Build once, deploy many.** One immutable artifact (here: the plugin content at a **git tag**), promoted through stages by **pointing channels at it** — never rebuilt, never branch-modelled. **Environments/channels are not branches.** (Branch-per-environment is a named anti-pattern.)

For a **deployed service** the stages are dev→staging→prod servers (same container image, config-only differences). For a **distributed plugin** the stages are **release channels**: `canary → beta → stable`. Sulis is the plugin case.

**Hard constraint that shapes everything below:** https-safe sources are **relative only** (`"./plugins/x"`). A `github`/tag-pinned source needs SSH. Therefore an https-safe *channel* must be **a repo (or default branch) whose content IS that channel's release** — you cannot pin a channel to a tag over https in the current CLI.

---

## 3. Two target models

### Model A — Trunk-based (recommended; convention-default)

Collapse to one trunk. `main` = default = integration = release line.

```
short-lived feature branch ──PR (CI gate)──▶ main (trunk, default)
                                               │  tag a release: v0.X.0
                                               ▼
                          consumers read main (default) = latest release
                          (marketplace.json on main, RELATIVE source — https-safe)
```

- **No long-lived `dev`.** Feature/change branches are short-lived and merge to `main` behind CI gates + your existing change/review discipline.
- **Releases = tags** on `main` (the robot keeps bumping `plugin.json` + assembling CHANGELOG; the tag marks the release).
- **Consumers** install `sulis@sulis-ai-agents` → read `main` (default) → relative source → **the released version, https-safe.** The whole distribution problem disappears because the default branch *is* the release line.
- **Staging/canary** (if/when needed): a `sulis-ai/agents-canary` repo (or `sulis-plugins-canary`) whose default branch tracks pre-release. Most plugins don't need this on day one.

**Pros:** zero new machinery; matches the marketplace tool's assumption *and* the dominant industry convention; kills the dev-resync + stranded-release + SSH problems in one move.
**Cons:** you lose the `dev` integration buffer. Mitigations: CI gates per PR (already have), the change→review→ship discipline (already have), feature flags for risky work, a canary channel later.
**The earlier objection (PR base defaults to `main`) dissolves** — with no `dev`, `main` *is* the correct PR base.

### Model B — Keep `dev`/`main`; move distribution to its own repo

Preserve your current development model untouched; decouple *distribution*.

```
sulis-ai/agents:  feature ─▶ dev ─▶ main   (unchanged; your dev workflow)
                                     │  on release, robot PUBLISHES the released
                                     │  plugin content to ▼
sulis-ai/plugins (default branch = STABLE release line, RELATIVE sources)
                                     │
                          consumers add sulis-ai/plugins ─▶ released version, https-safe
```

- `sulis-ai/plugins` (you already have it registered) becomes the **consumer-facing marketplace**. Its default branch holds the **released** plugin at a relative path → https-safe.
- The release robot gains one step: after the `main` bump + tag, **sync the released `plugins/sulis` tree into `sulis-ai/plugins`** (the "promote artifact to the stable channel" step).
- **Channels** = repos/default-branches: `sulis-ai/plugins` (stable), optionally `sulis-ai/plugins@canary-repo` (canary).

**Pros:** keeps `dev`/`main`; distribution can never again collide with your branching; clean channel story.
**Cons:** a second repo + a publish step in the robot; two places to reason about.

---

## 4. Recommendation

**Go Model A (trunk-based) unless you have a concrete reason the `dev` buffer earns its keep.** It's the boring, dominant convention; it needs no new infrastructure; and it makes the marketplace's "read the default branch" behaviour *correct by construction*. The `dev`/`main` split is the thing generating the friction, and for a plugin (not a high-QPS service) the buffer it buys is thin against the cost you've seen this week.

**Choose Model B if** keeping `dev` as an integration/staging buffer is genuinely valuable to how you work — then pay for a distribution repo to get clean, https-safe releases without touching that workflow.

This is a founder-owned call (how the team works + release-cadence risk appetite), which is why I'm putting both in front of you rather than just picking.

---

## 5. Migration path

### If Model A (trunk-based)
1. **Deliver 0.88.0 first** (one-time): bring `main`'s bump onto `dev` so nothing is stranded during the switch (the force-resync), OR skip straight to step 2 if you switch the default immediately.
2. **Set `main` as the repo default branch** (GitHub settings). PRs now base on `main`.
3. **Re-home in-flight `change/*` branches** onto `main` (rebase/retarget). Retire `dev` once drained.
4. **Simplify the release robot:** tag-on-release stays; drop the `dev→main` promotion PR + back-merge machinery (no longer needed — there's one line). The drift guard becomes moot.
5. **`/plugin marketplace update` + reinstall** to confirm consumers resolve the released version from `main`.
6. Update README/docs: install instructions unchanged (`sulis@sulis-ai-agents`), now serving releases.

### If Model B (separate distribution repo)
1. **Deliver 0.88.0** (force-resync `dev`) so today's release isn't stranded in the interim.
2. **Seed `sulis-ai/plugins`:** default branch = stable; commit `marketplace.json` (relative source) + the released `plugins/sulis` tree at 0.88.0.
3. **Add a publish step** to `release-on-merge.yml`: after the `main` bump + tag, copy `plugins/sulis` → `sulis-ai/plugins` default branch (a deterministic sync; tag it there too).
4. **Cut consumers over:** docs say install from `sulis-ai/plugins`; deprecate installing `sulis@sulis-ai-agents` directly (it stays the dev source).
5. Optional later: a canary distribution repo/branch.

---

## 6. The other half: deploying the *products* Sulis builds

For the actual services Sulis builds for founders (real dev/staging/prod servers), apply build-once-deploy-many directly:
- CI builds **one container image per `main` commit**, tagged `@<sha>`.
- Auto-deploy that image to **dev**; promote the **same image** to **staging** (gate: smoke/integration), then **prod** (gate: approval).
- Environments differ by **config/secrets only** — never a rebuild, never a `staging`/`prod` branch.
- This is already what the Sulis pipeline gestures at (deploy-to-dev, staging URL, smoke test, post-deploy verification) — the discipline is: *same artifact across all three.*

---

## 7. What this supersedes

Adopting either model retires the open patch-level decisions:
- The `dev` force-resync becomes either a one-time migration step (A) or interim delivery (B), not a recurring chore.
- "Option A vs C" from the distribution discussion is settled: **C (pin source ref) is dead (SSH); the real choice is trunk-based (A here) vs separate-repo (B here).**
- The auto-back-merge bot, the squash/ancestry drift guard, and the back-merge friction are **only needed in Model B** (and not at all in Model A).

---

## Provenance
Built on the verified findings in `claude-code-plugin-distribution-brief.md` (version resolution, SSH clone behaviour, #23551, #35752) and the build-once-deploy-many / branch-per-environment-anti-pattern conventions ([Octopus](https://octopus.com/blog/stop-using-branches-deploying-different-gitops-environments), [Build Once Deploy Many](https://medium.com/@aslam.develop912/build-once-deploy-many-the-core-ci-cd-principle-youre-probably-missing-d9fcdc34a854)).
