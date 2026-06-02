# Recon — fix-discover-verify-scope

Stage 0 completed at: 2026-06-02T13:26:07Z

This marker file's existence indicates that `/sulis:recon` has been run
for this change. The spawned Sulis's stage-inference uses this file to
distinguish "post-recon" from "pre-spawn stub only".

## Findings (Stage 0)

Three bugs confirmed and located:

1. **Missing --scope mode.** `_discovery/verifier.py` invokes
   `check-canonical-drift.py --scope <entity> --cross-tenant-refs-allowed-for ...`
   but `check-canonical-drift.py` argparse has NO `--scope` flag (only
   --instance-dir [required], --yaml-path [required], --marketplace-json,
   --validate-schemas, --cross-tenant-refs-allowed-for). Every verifier
   subprocess call fails exit 2 → drift "fails" → mint rolled back.
   FIX: add a `--scope <entity-file>` mode that schema-validates one
   entity + applies the cross-tenant-ref allowlist WITHOUT requiring
   --yaml-path / --instance-dir.

2. **cwd-relative detector path.** `verifier.py:58`
   `_DEFAULT_DRIFT_DETECTOR = Path("plugins/sulis/scripts/check-canonical-drift.py")`
   is relative to cwd; in a consumer repo cwd is not the sulis repo root,
   so it won't resolve. FIX: resolve relative to `__file__`.

3. **Wrong primary_branch.** `_discovery/inspector.py:181` uses
   `git branch --show-current` (the checked-out branch), recording e.g.
   a feature branch as primary_branch instead of the repo default (main).
   FIX: resolve the repo default branch (origin/HEAD), fall back to main.

## Test gap that let this ship

No real-subprocess `--scope` test and no consumer-repo regression test.
Both required (TDD-first) per the change intent.

## Touched files

- plugins/sulis/scripts/check-canonical-drift.py (add --scope mode)
- plugins/sulis/scripts/_discovery/verifier.py (resolve detector path via __file__)
- plugins/sulis/scripts/_discovery/inspector.py (repo-default branch)
- tests: consumer-repo regression + real-subprocess --scope

Arrival check: ok=true (RC-06/RC-08 advisory warnings only, non-blocking).
No context index exists for this repo (.context/*/INDEX.md absent).
