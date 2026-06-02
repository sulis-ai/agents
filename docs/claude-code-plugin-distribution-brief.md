# Brief: distributing Claude Code plugins (for a plugin-creating agent)

> **Audience:** an agent whose job is creating and shipping Claude Code plugins + marketplaces.
> **Status:** empirically verified on 2026-06-02 against the live Claude Code CLI. Where a claim was tested, it says **[verified]**. Treat web/blog summaries of this topic with suspicion — several were wrong (noted inline).
> **Why this exists:** we lost half a day to a plausible-but-false mental model of how versions resolve and how sources clone. Read this before designing any distribution mechanism.

---

## TL;DR — the rules that actually hold

1. **Version comes from the plugin's own `plugin.json` on the source ref — NOT the marketplace catalog's `version` field.** [verified: a catalog `version: 9.9.9` was ignored; the client installed the source `plugin.json`'s `1.0.0`.] The catalog `version` field is cosmetic for resolution.
2. **The marketplace catalog (`marketplace.json`) is read from the repo's DEFAULT branch.** You cannot currently register a marketplace pinned to a non-default branch ([open feature request #23551](https://github.com/anthropics/claude-code/issues/23551)).
3. **Relative plugin sources (`"./plugins/x"`) resolve INSIDE the marketplace's own clone and need no extra network/auth.** This is the safe default.
4. **`github`-typed *plugin* sources clone over SSH (`git@github.com`) and FAIL for https-only consumers** — even for public repos. [verified: install/update failed `Permission denied (publickey)` on a machine with no SSH keys.] The marketplace *itself* clones over https, so this is an inconsistency, not a rule you can rely on.
5. **The `{source: "git", url: "https://…"}` source type is NOT supported** by the current CLI ("source type your Claude Code version does not support"). [verified.]
6. **Corollary of 2+4+5:** there is currently **no way to pin a plugin to a non-default ref over https.** If you need consumers on a release line that isn't the default branch, you must make a **separate repo whose default branch IS the release line**, with **relative** sources.
7. **`/plugin update` does not refresh the marketplace clone first** ([open bug #35752](https://github.com/anthropics/claude-code/issues/35752)). Always `/plugin marketplace update <name>` before `/plugin update <plugin>`, or the client reports "already at latest" against a stale catalog.

---

## The source schema (what fields exist)

A plugin entry in `marketplace.json` `plugins[]`:

```jsonc
{
  "name": "myplugin",
  "source": "./plugins/myplugin",     // relative — RECOMMENDED (https-safe, no extra clone)
  "version": "1.2.3",                  // COSMETIC for resolution; the source plugin.json wins
  "description": "…"
}
```

Source forms:
| `source` form | Clones via | https-safe? | Subpath? | Notes |
|---|---|---|---|---|
| `"./path"` (relative) | resolves in the marketplace's own clone | ✅ yes | n/a | **Default. Use this.** |
| `{source: github, repo, ref, path}` | **SSH** (`git@github.com`) | ❌ **no** — needs SSH key | ✅ `path` works [verified accepted] | Pins to a ref/tag/sha, but SSH-only in practice. Avoid for public-consumer plugins. |
| `{source: git, url: https://…}` | — | — | — | **Unsupported** by current CLI. |

`ref` (branch/tag) and `sha` (commit) pin the fetched ref for github sources; `sha` is the deterministic choice — but all of this is moot if it clones over SSH and your consumers are https-only.

---

## The default-branch trap (the thing that bit us)

Consumers install from the repo's **default branch**. If your default branch is also your **integration branch** (where feature branches merge — e.g. `dev`), then:

- Consumers track unreleased, mid-sprint content.
- Version bumps that land on a *release* branch (e.g. `main`) **never reach consumers** unless that bump is brought back onto the default branch.

This is a role conflict: one branch can't cleanly be both "where work integrates" and "what users install."

### How to resolve it (pick one)

| Option | How | https-safe? | Cost |
|---|---|---|---|
| **A. Separate distribution repo** | A repo whose **default branch is the release line**; lists plugins with **relative** sources; release process publishes the released plugin content there. Consumers add *that* marketplace. | ✅ | New repo + a publish step on release |
| **B. Back-merge to the integration branch** | Keep one repo; after a release bumps the release branch, merge the bump back onto the default/integration branch so its `plugin.json` carries the released version. | ✅ | Consumers still track the integration branch's content between releases |
| **C. ~~Pin plugin source to the release ref~~** | ~~`{source: github, ref: main}`~~ | ❌ **SSH-only — rejected** | Looks cheapest; isn't viable over https |

**Recommendation for a public, https-consumer plugin:** Option **A** if you want consumers to receive *only released* versions; Option **B** if tracking the integration branch is acceptable. Do **not** reach for C — it reads as the obvious cheap fix and fails on the SSH clone.

---

## Release/versioning model that works with the above

- **`plugin.json` `version` is the source of truth** for what installs. Bump it on release.
- Keep the marketplace catalog `version` field roughly in step for human readability, but know it doesn't gate resolution.
- If a separate distribution repo (Option A) is used, the release step must update the plugin content + `plugin.json` on that repo's default branch.
- Tag releases with immutable tags if you ever want `sha`/`ref` pinning later (and if/when https github sources become available).

---

## Gotchas checklist (paste into any distribution design review)

- [ ] Is the marketplace's **default branch** a release line, or an integration branch? (If integration → consumers get unreleased content.)
- [ ] Are all plugin sources **relative**? (If any are `github`-typed → SSH clone → breaks https-only consumers.)
- [ ] Does the release process actually land the new `plugin.json` version on the **branch consumers read**?
- [ ] Are you relying on the catalog `version` field to drive updates? (It doesn't — `plugin.json` does.)
- [ ] Have you documented that consumers must `/plugin marketplace update` before `/plugin update` (bug #35752)?
- [ ] Is the repo public AND do you assume consumers have SSH? (Public ≠ SSH-cloneable without a key.)

---

## Open upstream issues to track

- [#23551](https://github.com/anthropics/claude-code/issues/23551) — can't pin a marketplace registration to a non-default branch (open feature request). If resolved, a release-branch-as-catalog in one repo becomes possible.
- [#35752](https://github.com/anthropics/claude-code/issues/35752) — `/plugin update` doesn't pull the marketplace clone (stale "already at latest").
- **(File this one)** — `github`-typed plugin sources clone over SSH while marketplace sources use https; they should honour https for public repos. Until fixed, non-default-ref pinning over https is impossible.

---

## Provenance

Every **[verified]** claim was tested live against the `claude plugin` CLI on 2026-06-02 using throwaway local marketplaces with deliberately-conflicting version fields and source types, plus a real https-only machine. The web/blog sources on this topic (including a widely-cited "the catalog version field drives updates" claim) were **contradicted** by direct testing — prefer this brief.
