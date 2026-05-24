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

# Tool wrapper run() convention. Every _lib/tools/{tool}.py exposes a
# canonical run() function (mirrors sea:probe runners pattern). Renaming
# would break the consumer-side wrapper protocol documented in REFERENCE.md.
naming-clarity::plugins/sulis/_lib/tools/curl_probe.py::39: tool-wrapper run() convention
naming-clarity::plugins/sulis/_lib/tools/gitleaks.py::25: tool-wrapper run() convention
naming-clarity::plugins/sulis/_lib/tools/hadolint.py::25: tool-wrapper run() convention
naming-clarity::plugins/sulis/_lib/tools/jscpd.py::33: tool-wrapper run() convention
naming-clarity::plugins/sulis/_lib/tools/lizard.py::28: tool-wrapper run() convention
naming-clarity::plugins/sulis/_lib/tools/semgrep.py::30: tool-wrapper run() convention
naming-clarity::plugins/sulis/_lib/tools/testssl.py::26: tool-wrapper run() convention
