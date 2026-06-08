# Recon — feat-live-origin-stamping

Stage 0 completed at: 2026-06-07T18:46:03Z

This marker indicates `/sulis:recon` has run for this change. Sulis's
stage-inference uses this file to distinguish "post-recon" from
"pre-spawn stub only".

## Key finding
The origin-stamping FOUNDATION this change builds on lives ONLY on branch
`change/create-autonomous-delivery-environment` (ADE epic, PR #216 shows
MERGED) and is ABSENT from `main` (this worktree's base, 860b6df).

Missing-from-main source the live-stamping piece depends on:
- plugins/sulis/scripts/_origin_stamp.py  (the write-path stamper)
- apps/cockpit/server/ports/OriginAttribution.ts
- apps/cockpit/server/adapters/{Recorded,Inferred,Composite}OriginAttribution.ts
- apps/cockpit/server/routes/origin.ts + lib/readOrigin.ts + lib/originAttribution/*
- apps/cockpit/client/src/components/Origin* + api/useOrigin.ts

Branch arithmetic: `main..ADE` = 54 commits; `ADE..main` = 0.
=> the ADE branch is a strict superset of main. The dev->main repoint
(#176/#177) appears to have NOT carried the ADE epic across to main.

This must be resolved (base the work on the ADE foundation, or land #216
on main first) before the live-stamping piece can be specified/built.
