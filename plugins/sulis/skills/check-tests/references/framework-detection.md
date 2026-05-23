# Test Framework Detection

How `scripts/regression.py` decides which test framework a project uses.
Detection signals + commands + result-parsing notes per framework.

## Detection precedence

When multiple frameworks are present, the script asks the founder which
to use (or accepts `--framework` override). Default ordering:

1. **pytest** (most common in this marketplace's projects)
2. **vitest** (modern; explicit config usually present)
3. **jest** (most common in JS/TS projects)
4. **go test** (Go default)
5. **rspec** (Ruby)
6. **mocha** (legacy JS; fallback when explicit config present)
7. **unittest** (Python stdlib; only if no pytest config)

## Per-framework signals + commands

### pytest

**Detect:**
- `pyproject.toml` containing `[tool.pytest.ini_options]` OR `pytest` in `[tool.poetry.dev-dependencies]` / `[project.optional-dependencies.test]`
- `pytest.ini` exists
- `setup.cfg` containing `[tool:pytest]`
- `conftest.py` at project root or any `tests/` subdirectory

**Cached results:**
- `.pytest_cache/v/cache/lastfailed` (JSON dict of failing tests from last run)
- `test-results.xml` (JUnit XML if `--junit-xml` was used)
- `pytest_cache/v/cache/nodeids` (all known test node IDs)

**Run command:**
```bash
pytest --tb=no --quiet --no-header [--maxfail=N] [paths...]
```

For JSON output via `pytest-json-report` plugin (if installed):
```bash
pytest --json-report --json-report-file=.pytest_cache/results.json
```

**Result parsing:** stdout line-by-line (PASSED/FAILED indicators + node IDs), OR JSON envelope if json-report plugin present.

**Test signature format:** `{file}::{class_name}::{test_name}` (class optional for module-level tests).

### vitest

**Detect:**
- `package.json` containing `"vitest"` in dependencies/devDependencies
- `vitest.config.{js,ts,mjs}` exists

**Cached results:**
- `node_modules/.vitest/results.json` (if vitest cache enabled)

**Run command:**
```bash
npx vitest run --reporter=json
```

**Result parsing:** JSON envelope (vitest's native JSON reporter).

**Test signature format:** `{file}::{describe-path}::{test_name}`.

### jest

**Detect:**
- `package.json` with `"jest"` in dependencies/devDependencies
- `jest.config.{js,ts,mjs,json}` exists
- `package.json` containing `"jest": { ... }` configuration block

**Cached results:**
- `jest-results.json` if `--json` was used previously
- `coverage/coverage-summary.json` (presence-of-run signal, not pass/fail)

**Run command:**
```bash
npx jest --json --silent
```

**Result parsing:** JSON envelope (jest's native JSON reporter).

**Test signature format:** `{file}::{describe-path}::{test_name}`.

### go test

**Detect:**
- Any `*_test.go` file in the project tree (search with `find` capped at depth 5)
- `go.mod` at project root

**Cached results:** Go does NOT cache test results in a parseable way by default — cache is opaque.

**Run command:**
```bash
go test -json ./...
```

**Result parsing:** JSON stream (one JSON object per event). Filter by `Action: "pass"|"fail"`; combine by `Package` + `Test`.

**Test signature format:** `{package}::{test_function}` (subtests via `t.Run` get appended).

### rspec

**Detect:**
- `Gemfile` containing `"rspec"`
- `.rspec` file present
- `spec/spec_helper.rb` exists

**Cached results:** rspec does NOT cache by default; needs `--format json` + redirect.

**Run command:**
```bash
bundle exec rspec --format json
```

**Result parsing:** JSON envelope (rspec's `json` formatter).

**Test signature format:** `{file}::{description-path}`.

### mocha

**Detect:**
- `package.json` with `"mocha"` in dependencies/devDependencies
- `.mocharc.{js,json,yml}` exists
- `package.json` `"scripts.test"` referencing `mocha`

**Cached results:** mocha does NOT cache by default.

**Run command:**
```bash
npx mocha --reporter json
```

**Result parsing:** JSON envelope (mocha's `json` reporter).

**Test signature format:** `{file}::{describe-path}::{test_name}`.

### unittest (Python stdlib)

**Detect:**
- `test_*.py` files containing `unittest.TestCase` subclasses
- No pytest config present
- (low-priority — pytest can run unittest tests, so prefer pytest detection)

**Run command:**
```bash
python -m unittest discover -v
```

**Result parsing:** stdout pattern matching ("ok"/"FAIL" suffixes).

**Test signature format:** `{module}::{class_name}::{test_method}`.

## Multi-framework projects

In a monorepo with both Python and JS tests, detection finds both. v1
behaviour: prompt the founder for which to run, OR run both and report
under separate sections of the verdict.

`--framework <name>` flag overrides detection. `--all-frameworks` runs
every detected framework (slow but comprehensive).

## Adding a new framework

To extend support for a framework not listed here:

1. Add a `Framework` dataclass entry in `scripts/regression.py`
   (`KNOWN_FRAMEWORKS` list) with detection signals, run command,
   and parser function reference.
2. Add a parser function that takes the run-command stdout/stderr and
   produces `list[TestResult]` (signature, status, file).
3. Update this document with the new framework's section.
4. Add the framework name to the multi-framework prompt in
   `scripts/regression.py:resolve_framework()`.

No core logic changes needed; the framework-handling is registry-driven
(same pattern as code-health's tier-registry).

## Cached-vs-fresh decision tree

When the script starts:

```
1. If --no-cache: run fresh.
2. Else if cached results found AND not stale (< 5 min old): use cache.
3. Else if cached results found AND --use-stale: use cache anyway; flag in output.
4. Else if --run: run fresh.
5. Else: report "tests detected but not run; pass --run."
```

Staleness threshold is configurable via `--cache-max-age N` (seconds).

## Known limits in v1

- **Per-file PR-scope filtering** is best-effort. pytest supports
  `pytest <file>` directly; jest supports `--testPathPattern`; go test
  supports `go test ./<pkg>`. Other frameworks may fall back to running
  the whole suite even in PR-scope mode.
- **Parameterized tests** generate one signature per parameter set.
  Renaming a parameter changes the signature; this can spuriously appear
  as "newly-added" + "newly-removed." Documented as a known limit;
  founders can `--update-baseline` to reset.
- **Conditionally-skipped tests** (e.g., skipped on Windows) appear as
  newly-added/newly-removed across platforms. Same workaround.
