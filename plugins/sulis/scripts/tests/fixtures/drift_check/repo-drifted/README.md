# Fixture: repo-drifted

Placeholder. The fixture clone where `origin/dev` is behind `origin/main` (drift, with no open back-integrate PR) lands here in WP-009. See `.architecture/auto-back-merge-on-release/work-packages/WP-009-drift-check-test-suite.md`.

Expected `drift_check.sh` behaviour against this fixture: exit 1, stderr line starting `drift_check: dev is behind main, and no back-integrate PR is open.` followed by the UC-005 recovery procedure.
