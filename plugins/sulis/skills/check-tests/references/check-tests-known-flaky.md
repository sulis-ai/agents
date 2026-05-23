# Known-Flaky Tests — Marketplace-shared list

Tests known to be flaky across the marketplace. The regression detector
suppresses these from the regression report (they show up under the
"Flaky tests (suppressed)" footer instead).

Per-project allow-lists override + extend this file at
`.checkup/{project}/known-flaky.md`.

## Format

One test-signature per line. Lines starting with `#` are comments.
Signatures match the framework's native format:

- pytest: `path/to/test_file.py::ClassName::test_method` (class optional)
- jest/vitest: `path/to/test.spec.ts::describe-block::test name`
- go: `package.path::TestFunction`
- rspec: `path/to/spec_file.rb::description-path`

## Known flaky (marketplace-wide)

# wpx-train concurrency test — see sulis-execution v0.10.6 release notes
plugins/sulis-execution/scripts/tests/unit/test_wpx_train_state_machine.py::test_train_lock_second_acquisition_raises

## How to add a flaky test

1. Verify the test is genuinely flaky (passes most of the time; fails
   sporadically with the same code).
2. Either fix it (preferred) OR add its signature here with a comment
   explaining why fixing is deferred.
3. Comment should reference: the underlying bug (if known), why it's
   flaky (timing? concurrency? environment?), and when it's planned
   to be fixed.

## When to REMOVE a flaky test from this list

- Bug fixed → remove. The regression detector will then correctly
  surface any future flips of that test as real regressions.
- Test deleted → remove. Stale entries pollute the suppression list.
- Reclassified (e.g., flakiness was actually a real bug discovered
  later) → remove.

## Why not auto-detect flakiness

The detector could in principle observe "this test flips status across
N runs" and auto-suppress. v1 chooses explicit allow-list because:

1. Auto-detection has false positives (a test fixed today flips from
   failing to passing — that's a fix, not flakiness)
2. Explicit list creates social pressure to actually fix flaky tests
   (vs silently tolerating)
3. Signature-stable: a tester knows exactly what's suppressed by
   reading this file

Future v2 could add `--detect-flaky-over N runs` as opt-in alongside
the allow-list.
