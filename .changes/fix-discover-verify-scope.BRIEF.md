# Brief — fix the discover-project verify gate (CH-01KT48)

> Full root-cause hand-off from the session that diagnosed this. Fix the ROOT
> CAUSE, TDD-first. Bug hit live in a consumer repo (the Capsule platform repo):
> `/sulis:discover-project` rolls back **every** mint, on dev and 0.87.0.

## Three bugs (verified — don't re-derive, confirm then fix)

**Bug 1 — verifier calls a checker mode that doesn't exist.**
`plugins/sulis/scripts/_discovery/verifier.py` (`_invoke_drift_detector`) runs:
```
python3 <detector> --scope <entity-file> --cross-tenant-refs-allowed-for <refs>
```
But `plugins/sulis/scripts/check-canonical-drift.py` has **no `--scope`** — only
`--instance-dir` + `--yaml-path` (both *required*, release-train drift), plus
`--marketplace-json`, `--validate-schemas`, `--cross-tenant-refs-allowed-for`.
argparse rejects `--scope` → exit 2 ("required: --instance-dir, --yaml-path") →
verify treats it as drift → mint rolls back. The "WP-009 `--scope` extension"
the verifier expects was specified but never built. (The verifier's own
race-guard only catches an unrecognised `--cross-tenant-refs-allowed-for`, which
dev's checker *does* accept — so it falls straight through to rollback.)

**Bug 2 — detector path is cwd-relative.**
`_DEFAULT_DRIFT_DETECTOR = Path("plugins/sulis/scripts/check-canonical-drift.py")`
only resolves inside the marketplace repo; in a consumer repo it doesn't exist.
Existing tests masked it by running inside the marketplace repo.

**Bug 3 (milder, separate) — wrong primary_branch.**
discover mint (`_discovery/__init__.py` detect/compose) records `primary_branch`
as the *checked-out* branch (e.g. a feature branch) instead of the repo default
(`main`).

## The fix (root-cause)

1. **Add `--scope <entity-file>` to `check-canonical-drift.py`.** Validates ONE
   entity: reuse the checker's existing schema-validation machinery + apply the
   cross-tenant-ref allowlist. In `--scope` mode, `--instance-dir`/`--yaml-path`
   are NOT required (release-train-only). Exit 0 clean / 1 violation / 2
   invocation. This matches the verifier's existing call exactly → no verifier
   logic change beyond Bug 2.
2. **Bug 2:** resolve `_DEFAULT_DRIFT_DETECTOR` relative to `__file__`
   (`Path(__file__).resolve().parent.parent / "check-canonical-drift.py"` — the
   checker ships alongside the verifier).
3. **Bug 3:** default `primary_branch` to the repo default branch (resolve via
   `git symbolic-ref refs/remotes/origin/HEAD` → fall back to `main`), keep
   overridable.

## TDD discipline (MUST — this is what let it ship)

- Failing tests first, each fix.
- **Close the test gap:** (a) a REAL-subprocess test invoking the actual
  `check-canonical-drift.py --scope <fixture-entity>` (no mocking) — exit 0 on a
  valid entity, exit 1 on a cross-tenant-ref violation; (b) a consumer-repo
  regression test (cwd = a non-marketplace temp dir) proving the detector still
  resolves + runs; (c) primary_branch defaults to the default branch.
- Full unit suite green (`cd plugins/sulis/scripts && uv run pytest tests/unit/ -q`;
  baseline 1650 pass / 9 skip) + `python3 -m compileall -q plugins/sulis/scripts`.

## Done = shipped to dev

This is a real bug fix — once green, ship it to `dev` via the normal change ship
(`/sulis:change ship`), so the next release unblocks discover-project for
consumers. Commits end with:
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

Also captured as task #64 in the originating session.
