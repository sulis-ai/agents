# Code Review (batch gate): WP-002 + WP-003 + WP-004 — writer + Action + skill

> **Timestamp:** 2026-05-28T191515Z
> **Target:** train-2026-05-28T185209Z (batch_size=3); merge `e858389` on `change/create-release-train`; batch diff `4c1cbf69..e858389`
> **Outcome:** Don't merge yet — two cross-WP / load-time defects the per-WP reviews could not see.

## At a glance

The three pieces compose mathematically (an end-to-end seam test produced the correct `minor → plugin 0.78.0 / metadata 1.123.0 / tag v1.123.0`), and ten safety checks on the high-blast-radius Action passed. But the batch-composition gate found two real defects each per-WP review missed — exactly the class it exists to catch:

1. **The ship step never actually writes a changeset** (critical) — the producer would crash on every ship, leaving `dev` empty: the #66 invisibility surviving silently.
2. **The Action's loop-guard won't load** (high) — risks the bot's own release commit re-triggering the workflow.

Both are one-line fixes. Remediation queued before any ship.

## What to fix

### Must fix — `plugins/sulis/skills/change/SKILL.md` step 4.7 (and the WP-002 spec)

The new ship step calls `_changeset.write_changeset('.changesets', …)` — passing a plain string where the function needs a path object (it immediately calls `.mkdir()`). Running the snippet raises `AttributeError: 'str' object has no attribute 'mkdir'`. The producer never writes a changeset → `dev` accumulates none → the release train has nothing to release. The seam test passed only because it called the module with a real `Path`; the ship snippet itself was never executed by the per-WP review. The WP-002 spec (`work-packages/WP-002-ship-writes-changeset.md:94`) carries the same string literal, so the spec needs the same correction.

**Fix:** harden the keystone to accept `str | Path` (coerce `Path(changesets_dir)` at entry of `write_changeset` + `read_changesets`, with a test proving a `str` arg works) so this class can't recur at any call site; and/or correct the snippet to pass `Path('.changesets')` + `from pathlib import Path`. Verify by executing the corrected snippet end-to-end.

### Strongly recommend fixing — `.github/workflows/release-on-merge.yml:36`

The loop-guard expression uses a double-quoted string literal inside `${{ }}`:
`if: '${{ !startsWith(github.event.head_commit.message, "release: sulis") }}'`. GitHub Actions expressions accept single-quoted literals only — this fails at expression evaluation (YAML lint passes, so it slips through). If the guard fails to evaluate, the bot's own `release: sulis …` commit could re-trigger the one workflow that pushes to `main` and tags. The prefix logic is otherwise correct (`release: sulis` is an exact prefix of the step-9 commit message).

**Fix:** single-quote the literal: `${{ !startsWith(github.event.head_commit.message, 'release: sulis') }}`. Verify with actionlint, or a documented manual check of the expression.

## Technical detail

### Verdict
`Block` per CR-06 — one CRITICAL in the diff (producer crashes; train mechanism broken). Handled as forward remediation (WP-009), not revert: the WPs stay on the isolated change branch and are fixed before the change ships (nothing reached `main`).

### Findings
| id | severity | lens | file:line | summary |
|---|---|---|---|---|
| CR-BATCH-01 | critical | composition (quality) | plugins/sulis/skills/change/SKILL.md:488-489 + WP-002 spec:94 | `write_changeset('.changesets', …)` passes str; `.mkdir()` raises AttributeError; producer never writes a changeset. |
| CR-BATCH-02 | high | infra (load-time) | .github/workflows/release-on-merge.yml:36 | loop-guard uses double-quoted literal inside `${{ }}`; GHA rejects at expression eval; bot push could re-trigger. |

### Clean (10 checks)
Contract coherence (WP-004 calls match signatures); single-source bump (WP-003 calls `_changeset.py`, no bash re-implementation); last-wins `tier:` read via the module; VERSION_DRIFT guard before bump; post-bump verification (re-reads all three, exit 1 on mismatch); nothing-to-release exits 0; three-value jq paths correct (plugin .version, marketplace sulis-entry .version, marketplace .metadata.version) + tag from metadata + CHANGELOG header from plugin version; `permissions: contents: write` minimal + default GITHUB_TOKEN, no token echo; `git rm .changesets/*.yaml` preserves README.md; explicit named staging (no `git add -A`).

### Methodology — CR-08
- [✓] CR-01 baseline on merged tip e858389: full changeset suite 50 passed; release-on-merge.yml YAML valid; nothing broke.
- [✓] CR-02 cross-WP composition reviewed (focused composition + infra-security lens against the batch diff) — the per-WP reviews covered each WP in isolation; this gate covered the seam + load-time.
- [✓] End-to-end seam test: 3 changesets (fix=patch, create=minor, delete=minor) → cumulative minor → 0.78.0 / 1.123.0 / v1.123.0; injection guard holds.
- [✓] CR-06 verdict computed: Block (1 critical). Forward-remediation disposition (WP-009).

### Cross-reference
Per-WP reviews: PR-feat-wp-002-…184433Z (PASS — missed the str/Path call-site bug), PR-feat-wp-003-…184751Z (approve-with-fixes — missed the expression-quoting), PR-feat-wp-004-…184815Z (PASS).
