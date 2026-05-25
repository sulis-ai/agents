# check-readability per-project allowlist — agents marketplace

Format: `signature: reason` where signature is `{heuristic}::{file}::{line}`.
Lines starting with `#` are comments.

# Module-level entry-point convention. orchestrator.py has a top-level
# run() that's the conventional entry-point for sea:probe's orchestration.
# interactivity.js's update() and init() are the corresponding JS
# conventions. Renaming would break the long-standing pattern.
naming-clarity::plugins/sulis/skills/analyse-codebase/scripts/probe/orchestrator.py::334: probe orchestrator entry-point convention
naming-clarity::plugins/sulis/skills/analyse-codebase/scripts/probe/render_templates/interactivity.js::85: interactivity.js JS entry convention
naming-clarity::plugins/sulis/skills/analyse-codebase/scripts/probe/render_templates/interactivity.js::107: interactivity.js JS entry convention

# _wpxlib.py kitchen-sink: documented in sulis-execution's HD-008.
# Per-HD architectural analysis concluded the structural alternative
# wasn't worth the cost at current scale. Allowlist for the marketplace
# itself; founders' projects see their own findings unfiltered.
# Revisit if the file grows beyond 4000 LOC.
kitchen-sink-file::plugins/sulis/scripts/_wpxlib.py::0: HD-008 design choice — revisit at 4000 LOC

# CCN findings inside _wpxlib.py: downstream of the HD-008 kitchen-sink
# choice. The kitchen-sink shape concentrates branchy parsing/dispatch
# logic in a few hot functions; per-function CCN over the lizard
# threshold (15) is expected at the current shape. Revisit during the
# v2 refactor that splits _wpxlib.py.
cyclomatic-complexity::plugins/sulis/scripts/_wpxlib.py::383: HD-008 — _has_branch_ci_trigger CCN expected in kitchen-sink
cyclomatic-complexity::plugins/sulis/scripts/_wpxlib.py::1100: HD-008 — parse_index_md CCN expected in kitchen-sink
cyclomatic-complexity::plugins/sulis/scripts/_wpxlib.py::1378: HD-008 — find_eligible_branches CCN expected in kitchen-sink
cyclomatic-complexity::plugins/sulis/scripts/_wpxlib.py::2346: HD-008 — read_train_run_record CCN expected in kitchen-sink
cyclomatic-complexity::plugins/sulis/scripts/_wpxlib.py::2675: HD-008 — find_wp_merge_sha CCN expected in kitchen-sink

# CCN finding inside the executor integration testbed. read_latest_train_record
# is a parser similar to the _wpxlib.py parsers above; same justification —
# CCN expected at current shape, will be split when the testbed grows.
cyclomatic-complexity::plugins/sulis/scripts/tests/integration/testbed.py::546: testbed parser CCN expected at current shape

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
