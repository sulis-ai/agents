# Recon — harden-plan-work-listready-gate

Stage 0 completed at: 2026-06-08T21:40:08Z

This marker file's existence indicates that `/sulis:recon` has been run
for this change. Sulis's stage-inference uses this file to distinguish
"post-recon" from "pre-spawn stub only".

## Findings (focused harden — known files)
- Real consumer: `wpx-index list-ready` (cmd_list_ready) keys on status=='pending' + deps done; errors when no parseable WP table.
- Current gate: `wpx-index lint` (cmd_lint → validate_wp_index_header) checks HEADER SHAPE only. Blind to status-vocab variant (#222: canonical header + status 'ready'/'blocked' passes lint but list-ready returns empty).
- Wiring: plan-work SKILL.md Step 9.5 (~L467-482) runs `wpx-index lint`; non-zero exit = decompose NOT done. Round-trip wired into lint enforces for free.
- Tests: plugins/sulis/scripts/tests/unit/ — reuse fixtures from test_wpx_index_status_vocab.py, test_wpx_index_columns.py, test_wpx_index_multitable.py.
- Open design choice (defer to design): extend `lint` vs new `verify`/`round-trip` subcommand. Handoff leans extend-lint.
