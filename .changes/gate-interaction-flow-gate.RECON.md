# Recon — gate-interaction-flow-gate

Stage 0 completed at: 2026-06-04T15:22:47Z

This marker file's existence indicates that `/sulis:recon` has been run
for this change. The spawned Sulis's stage-inference uses this file to
distinguish "post-recon" from "pre-spawn stub only".

## What recon found

The change has a working twin already in the codebase: the **visual-contract
done-gate**. Mirror it.

Touch-points located:
1. Done-gate enforcement — `plugins/sulis/scripts/wpx-index` (cmd_flip_status,
   _enforce_visual_contract_signoff_on_done ~L380-458) + `_wpxlib.py`
   (is_visual_contract_wp, visual_contract_signed_off ~L463-497). Runtime gate
   fires at the moment a WP flips to done.
2. contract_type — string field in WP frontmatter; today 'visual' is the only
   gated value (`_wpxlib.py` ~L465-548). Add 'interaction'.
3. WP decomposition rule — `references/standards/WORK_PACKAGE_STANDARD.md`
   WP-08.5 (~L190-232) + `CONTRACT_FIRST_STANDARD.md` CF-05/CF-07. Amend to
   place interaction contracts in the decomposition.
4. Spike target — `.architecture/cockpit-contract-preview/` WP-005 is the
   Sulis-internal visual-contract precedent; the live "clinics-scheme card"
   is the founder-facing flow to prove the gate on.

Pattern to mirror: add a new gate predicate (e.g. interaction_flow_exercised)
analogous to visual_contract_signed_off — blocks done until the flow is run
end-to-end over stub adapters (agent-observed or human-attested).

Stub-adapter precedent: `plugins/sulis/scripts/tests/fixtures/drift_check/gh-stubs/`
(PATH-shim + canned JSON responses).
