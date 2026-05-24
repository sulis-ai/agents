# check-readability per-project allowlist — agents marketplace

Format: `signature: reason` where signature is `{heuristic}::{file}::{line}`.
Lines starting with `#` are comments.

# Module-level entry-point convention. orchestrator.py has a top-level
# run() that's the conventional entry-point for sea:probe's orchestration.
# interactivity.js's update() and init() are the corresponding JS
# conventions. Renaming would break the long-standing pattern.
naming-clarity::plugins/sea/skills/probe/scripts/probe/orchestrator.py::334: probe orchestrator entry-point convention
naming-clarity::plugins/sea/skills/probe/scripts/probe/render_templates/interactivity.js::85: interactivity.js JS entry convention
naming-clarity::plugins/sea/skills/probe/scripts/probe/render_templates/interactivity.js::107: interactivity.js JS entry convention

# _wpxlib.py kitchen-sink: documented in sulis-execution's HD-008.
# Per-HD architectural analysis concluded the structural alternative
# wasn't worth the cost at current scale. Allowlist for the marketplace
# itself; founders' projects see their own findings unfiltered.
# Revisit if the file grows beyond 4000 LOC.
kitchen-sink-file::plugins/sulis-execution/scripts/_wpxlib.py::0: HD-008 design choice — revisit at 4000 LOC
