# Fixture: gh-stubs

Placeholder. Canned `gh pr list` responses used by WP-009 to simulate the "back-integrate PR open" vs "no PR open" branches of `drift_check.sh`'s error message composition. See `.architecture/auto-back-merge-on-release/work-packages/WP-009-drift-check-test-suite.md`.

Stubs land here as JSON files; WP-009's harness prepends a `gh` shim to `PATH` that reads these files and exits 0 with the canned response.
