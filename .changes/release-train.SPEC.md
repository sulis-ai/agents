---
founder_facing: false
status: SPEC — Option B chosen by founder; tier-L, decomposed below
---
# Spec — changeset-based release-train (Option B)

**Change:** create · release-train
**Closes:** [#66](https://github.com/sulis-ai/agents/issues/66) (ship flow doesn't mandate the version bump)
**Inspiration:** honest-claude `.claude/skills/{release-train,contribute}` + `.github/workflows/release-on-merge.yml` + `.changesets/`.

## Root cause + the fix

`/sulis:change ship` couples *integration* (land on dev) with *release*
(bump + changelog + tag) and leaves the release half to agent discipline →
features ship unlabelled (#52/#59/#53) and concurrent changes bumping the
same version collide (#64 vs #52). **Fix: decouple them.** Each change writes
a *changeset* (intent, no version); a release-train batches the accumulated
changesets into one bot-driven, deterministic version bump on merge to main.

## Option B (founder-chosen): dev→main PR + release-on-merge GHA

Releases go through a reviewed `dev→main` PR; a GitHub Action does the bump +
tag + changeset-deletion as `github-actions[bot]` on merge. More robust than
a local script (CI-gated, bot-attributed, single authority) — needs main
branch protection configured to let the bot push the bump commit.

## The 7 pieces (→ WP decomposition)

**WP-1 — Changeset data model + helper (keystone, TDD).**
- `.changesets/README.md` — the YAML contract: `change_id`, `primitive`,
  `tier` (patch|minor|major), `touches_plugin` (bool), `summary`, `created_at`.
- `_changeset.py`: `tier_for_primitive(primitive) -> tier|None` (fix/chore/
  refactor/docs→patch; feat/create/extend/compose/reuse/strangle/wrap/
  harden/instrument→minor; any breaking→major; admin/docs-only→None=no
  changeset), `write_changeset(...)`, `read_changesets(dir)`,
  `cumulative_tier(changesets)` (max), `next_version(current, tier)`,
  triple-key filename (`{primitive}-{slug}-{datetimeZ}.yaml`, collision-proof).
- Unit tests for every function (this is the deterministic core).

**WP-2 — `/sulis:change ship` writes a changeset (replaces manual bump).**
- New mandated ship step (sibling of 4.6 capture-lessons): write the
  changeset before the merge. **Remove the manual version bump** from the ship
  flow — the GHA owns it now. Skip the changeset for admin/docs-only changes
  (tier=None), mirroring honest's decision table.

**WP-3 — `release-on-merge.yml` GHA (the bump authority).**
- Trigger: push to `main`. Read `.changesets/*.yaml`; if none → "nothing to
  release", exit 0. Else compute cumulative tier → next version; bump
  `plugin.json` + `marketplace.json` (sulis entry + metadata.version);
  **assemble the CHANGELOG entry** from changeset summaries; `git rm` consumed
  changesets; commit as `github-actions[bot]`; tag `v<marketplace-version>`;
  push (commit + tag). Post-bump verification: re-read both files, fail if
  either didn't move. VERSION_DRIFT guard: abort if plugin.json ≠ marketplace
  sulis entry before bumping.

**WP-4 — `/sulis:release-train` skill (new).**
- On-demand. Reads `.changesets/*.yaml` + `origin/main..origin/dev`.
  Computes cumulative tier + expected version; drafts the release PR body +
  CHANGELOG preview; opens the `dev→main` PR via `gh pr create`. Read-only on
  origin (no commits/edits) — the only side effect is the PR. `--dry-run`
  (default-first-pass), `--draft`. "No changesets is valid" (admin-only
  release). Aborts on VERSION_DRIFT + on an existing open release PR.

**WP-5 — `version-check.yml` CI guard (enforcement).**
- On `change/*` branch / the dev→main PR: assert a plugin-affecting diff
  (`plugins/sulis/**`) carries ≥1 new `.changesets/*.yaml`. This is what makes
  "every plugin change is labelled" *structural*. **Advisory first** (warn,
  exit 0) for one release cycle, then promote to a required check — see
  bootstrapping.

**WP-6 — main branch protection (config, founder-gated step).**
- Configure `main`: require the `dev→main` PR + required status checks;
  `enforce_admins: false` so `github-actions[bot]` (admin token) can push the
  bump commit + tag. (honest's GHA pushes back as the bot — same shape.)
  Documented + applied via `gh api`; record the exact config in the change.

**WP-7 — standards + docs + retire manual bump.**
- git-workflow-standard: the release ceremony is now changeset-per-change →
  release-train → GHA bump. Update `/sulis:change` ship docs + lifecycle to
  remove manual-bump expectations. Cross-link #66.

## Bootstrapping sequence (MUST — avoids self-lockout)

1. Ship WP-1+WP-2+WP-3 first (changeset writer + GHA) so changes START
   producing changesets and the bump authority exists — BEFORE any
   enforcement.
2. Ship WP-4 (release-train skill) — now releases can be cut from changesets.
3. Ship WP-5 **advisory** (warn-only) so in-flight branches without
   changesets don't break; promote to a **required** check only after the
   flow is reliably producing changesets (next cycle).
4. WP-6 (main protection) lands with WP-3 so the bot can push; verify the bot
   can actually push the bump before relying on it (test on a throwaway).
5. This change itself ships through the OLD flow (manual bump, last time);
   the NEXT release uses the train.

## Sub-decisions (resolved)

- **Tier from primitive** (not hand-set) — deterministic, removes a judgment
  call. Map in `_changeset.py`; overridable via an explicit `tier:` in the
  changeset for the rare exception.
- **CHANGELOG auto-assembled** from changeset summaries (we do better than
  honest's deferred per-feature changelog).
- **Tag = `v<marketplace-version>`** (matches existing convention v1.xyz.0).
- **One changeset per change** (not per-file); triple-key filename handles
  parallel changes (the #64-vs-#52 conflict class, gone).

## How we'll know it's done

- A change ships writing a changeset, no version touched; dev accumulates them.
- `/sulis:release-train` opens a dev→main PR with the right cumulative
  version + an assembled CHANGELOG entry.
- Merging that PR → the GHA bumps both files, assembles CHANGELOG, deletes
  changesets, tags, pushes — verified green on a real cut.
- version-check guards plugin diffs (advisory → required).
- `_changeset.py` fully unit-tested; full suite green; review gate PASS.

## What to avoid

- Do NOT enforce version-check as a required check before the writer is live
  + producing changesets (self-lockout).
- Do NOT let the GHA bump without the VERSION_DRIFT + post-bump verification
  guards.
- Do NOT keep the manual per-change bump anywhere once WP-3 is live (two
  authorities = drift).

## References

- honest-claude `.claude/skills/release-train/SKILL.md`,
  `.changesets/README.md`, `.github/workflows/release-on-merge.yml`,
  `version-check.yml`.
- #66 (closes), #52/#59/#53 (the symptom), #64-vs-#52 (the conflict class),
  #41/L-08 (hoist-shared-primitive — the changeset model generalises it).
