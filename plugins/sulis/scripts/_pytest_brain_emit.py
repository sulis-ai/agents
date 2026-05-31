"""pytest plugin — emit TestRun + TestResult entities to the brain.

Phase B of the verification-DoD wiring. Tests claim what they verify via
`@pytest.mark.verifies("FR-001", "NFR-003", ...)`; on pytest invocation
this plugin emits one TestRun (the event of running) and one TestResult
per (test, requirements-set, type) tuple with outcome pass/fail/skip.

Activation — opt-in by design. Default off so the marketplace's existing
tests (which don't yet carry @verifies markers) don't slow down without
explicit configuration:

  - CLI: `pytest --brain-emit --brain-srd /path/to/SRD.md`
  - Env: `SULIS_BRAIN_EMIT_TESTS=1 SULIS_BRAIN_SRD=/path/to/SRD.md pytest`

Required when active: `--brain-srd` (path to SRD.md). The FR/NFR id
string in the marker is resolved to `dna:requirement:<ulid>` using the
SAME deterministic seed Requirement-emission uses
(`f"requirement:{srd_path}:{fr_id}"`), so a marker for FR-001 produces the
exact ULID Requirement-emission produced when it ingested the SRD.

Marker:
    @pytest.mark.verifies("FR-001")
    def test_login_flow(): ...

    @pytest.mark.verifies("FR-001", "FR-002")
    def test_combined(): ...

    @pytest.mark.verifies("FR-001", type="integration")  # override type
    def test_e2e(): ...

`type` defaults to `unit`. Allowed values per the schema:
unit / integration / e2e / contract / security.

Loading: activate with `pytest -p _pytest_brain_emit ...` (the plugin
module sits on sys.path because the marketplace's tests/conftest.py
inserts the scripts directory). For downstream projects, add the same
`-p _pytest_brain_emit` to their `addopts`.

Determinism: every TestResult ID is derived from
`(of_run, sorted-verifies, type)` — outcome doesn't bind the ID. A re-run
of the same test claiming the same requirements with a flipped outcome
updates the SAME TestResult record in place. That's the right model for a
self-correcting test-of-record: the brain reflects the LATEST verdict,
not an append-only history.

Failure policy: every emission path catches exceptions and prints a
warning. A brain failure must NEVER fail the pytest session — the
emission is a side-effect of the run, not its purpose.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

# These imports are deferred-tolerant: if the brain machinery isn't
# installed/vendored, the plugin auto-disables itself in
# `pytest_configure` rather than raising at import.
try:
    from _entity_adapter_local import LocalFileEntityAdapter
    from _entity_repository import EntityValidationError
    from _requirement_emission import _deterministic_ulid_from
    from _testresult_emission import emit_testresult
    from _testrun_emission import emit_testrun
    _BRAIN_AVAILABLE = True
except Exception:
    _BRAIN_AVAILABLE = False


_VALID_TEST_TYPES = {"unit", "integration", "e2e", "contract", "security"}
_PYTEST_OUTCOME_TO_BRAIN = {"passed": "pass", "failed": "fail", "skipped": "skip"}


# ─── Plugin registration + options ─────────────────────────────────────


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("brain-emit", "Sulis brain entity emission")
    group.addoption(
        "--brain-emit",
        action="store_true",
        default=False,
        help="Emit TestRun + TestResult entities to .brain/instances/",
    )
    group.addoption(
        "--brain-srd",
        action="store",
        default=None,
        help="Path to SRD.md (required when --brain-emit; "
             "used to resolve FR-NN markers to dna:requirement:<ulid>)",
    )
    group.addoption(
        "--brain-base-dir",
        action="store",
        default=None,
        help="Path to .brain/instances/ (default: inferred from --brain-srd)",
    )
    group.addoption(
        "--brain-domain",
        action="store",
        default="product-development",
        help="Entity-schema domain (default: product-development)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the `verifies` marker; resolve activation + config."""
    config.addinivalue_line(
        "markers",
        "verifies(*fr_ids, type='unit'): declare which FR/NFR ids this test "
        "verifies. type ∈ {unit, integration, e2e, contract, security}.",
    )

    # Resolve activation: CLI flag OR env var.
    cli_emit: bool = config.getoption("--brain-emit") or False
    env_emit = os.environ.get("SULIS_BRAIN_EMIT_TESTS", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    active = bool(cli_emit) or env_emit
    config.stash[_STATE_KEY] = _State(active=active)

    if not active:
        return  # opted out — plugin no-ops

    if not _BRAIN_AVAILABLE:
        # Brain machinery couldn't be imported (downstream consumer without
        # jsonschema / vendored schemas). Disable + warn; don't crash.
        config.stash[_STATE_KEY].active = False
        config.stash[_STATE_KEY].disabled_reason = (
            "brain machinery unavailable (jsonschema / schemas not present)"
        )
        return

    srd = (
        config.getoption("--brain-srd")
        or os.environ.get("SULIS_BRAIN_SRD")
    )
    if not srd:
        raise pytest.UsageError(
            "--brain-emit requires --brain-srd <path-to-SRD.md> "
            "(or SULIS_BRAIN_SRD env var)"
        )
    srd_path = Path(srd).resolve()
    if not srd_path.exists():
        raise pytest.UsageError(f"--brain-srd path not found: {srd_path}")

    base_dir_opt = (
        config.getoption("--brain-base-dir")
        or os.environ.get("SULIS_BRAIN_BASE_DIR")
    )
    base_dir = Path(base_dir_opt).resolve() if base_dir_opt else _infer_base_dir(srd_path)

    state = config.stash[_STATE_KEY]
    state.srd_path = srd_path
    state.base_dir = base_dir
    state.domain = config.getoption("--brain-domain")


# ─── Session start: emit the TestRun ───────────────────────────────────


def pytest_sessionstart(session: pytest.Session) -> None:
    state = session.config.stash.get(_STATE_KEY, None)
    if state is None or not state.active:
        return

    try:
        adapter = LocalFileEntityAdapter(base_dir=state.base_dir, domain=state.domain)
        ran_at = datetime.now(timezone.utc).isoformat()
        run = emit_testrun(repo=adapter, ran_at=ran_at, harness="pytest")
        state.testrun_id = run["id"]
        state.adapter = adapter
    except (EntityValidationError, ValueError, OSError) as exc:
        state.active = False
        state.disabled_reason = f"TestRun emission failed: {exc}"


# ─── Per-test report: collect (test, requirements, outcome, type) ──────


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Capture the `verifies` marker WITH ARGS on the test item.

    This is the load-bearing hook for marker-arg access: `pytest_runtest_
    logreport` receives a TestReport which has the marker NAMES but not
    their args. `pytest_runtest_makereport` runs while the item is still
    in scope, so we resolve the marker here and attach the data to the
    report object via `report.brain_verifies`.
    """
    outcome = yield  # let pytest build the TestReport
    report: pytest.TestReport = outcome.get_result()

    if report.when != "call":
        return  # only the test body matters; setup/teardown reports skipped

    marker = item.get_closest_marker("verifies")
    if marker is None:
        return
    fr_ids = [str(a) for a in marker.args if a]
    test_type = marker.kwargs.get("type", "unit")
    # Attach to the report so logreport can read it.
    setattr(report, "brain_verifies", (fr_ids, test_type))


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Stage collected outcomes; the emission happens at session-finish."""
    # `pytest_runtest_logreport` doesn't have config in scope. Use the
    # global session stash via a module-level reference we set in
    # `pytest_collection_modifyitems`.
    state = _state_ref.get("state")
    if state is None or not state.active:
        return
    if report.when != "call":
        return
    if not hasattr(report, "brain_verifies"):
        return

    fr_ids, test_type = report.brain_verifies
    if not fr_ids:
        return
    if test_type not in _VALID_TEST_TYPES:
        print(
            f"\n[brain-emit] {report.nodeid}: invalid @verifies(type={test_type!r}) — "
            f"not in {sorted(_VALID_TEST_TYPES)}; skipping result\n"
        )
        return
    outcome = _PYTEST_OUTCOME_TO_BRAIN.get(report.outcome)
    if outcome is None:
        return  # xfail / unknown — skip cleanly

    state.pending_results.append({
        "node_id": report.nodeid,
        "fr_ids": fr_ids,
        "type": test_type,
        "outcome": outcome,
    })


def pytest_collection_modifyitems(session: pytest.Session, items: list[pytest.Item]) -> None:
    """Cache the state in a module-level ref so `pytest_runtest_logreport`
    (which has no session in scope) can find it."""
    state = session.config.stash.get(_STATE_KEY, None)
    if state is not None:
        _state_ref["state"] = state


# ─── Session finish: emit TestResults + report ──────────────────────────


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    state = session.config.stash.get(_STATE_KEY, None)
    if state is None:
        return
    if not state.active:
        if state.disabled_reason:
            print(f"\n[brain-emit] disabled: {state.disabled_reason}\n")
        return
    if not state.testrun_id or not state.adapter:
        return

    emitted = 0
    failed = 0
    for r in state.pending_results:
        verifies_refs = [
            _fr_to_requirement_id(state.srd_path, fr) for fr in r["fr_ids"]
        ]
        try:
            emit_testresult(
                repo=state.adapter, of_run=state.testrun_id,
                verifies=verifies_refs, type=r["type"], outcome=r["outcome"],
                evidence=r["node_id"],
            )
            emitted += 1
        except (EntityValidationError, ValueError) as exc:
            failed += 1
            print(
                f"\n[brain-emit] failed for {r['node_id']}: {exc}\n"
            )

    print(
        f"\n[brain-emit] TestRun={state.testrun_id} "
        f"TestResults emitted={emitted} failed={failed} "
        f"untagged-tests-skipped={'n/a' if not state.pending_results else 'see report'}\n"
    )


# ─── Internals ─────────────────────────────────────────────────────────


class _State:
    """Per-session plugin state. Stashed on `config.stash` to avoid module
    globals + survive pytest's parallel-runner scenarios."""

    def __init__(self, *, active: bool) -> None:
        self.active = active
        self.disabled_reason: str | None = None
        self.srd_path: Path | None = None
        self.base_dir: Path | None = None
        self.domain: str = "product-development"
        self.testrun_id: str | None = None
        self.adapter = None  # LocalFileEntityAdapter | None
        self.pending_results: list[dict] = []


_STATE_KEY = pytest.StashKey["_State"]()

# Module-level ref so `pytest_runtest_logreport` (no session arg) can
# reach the stash. Populated in `pytest_collection_modifyitems`.
_state_ref: dict[str, _State] = {}


def _infer_base_dir(srd_path: Path) -> Path:
    """Infer `.brain/instances/` from an SRD path.

    Convention: SRD lives at `<repo-root>/.specifications/<project>/SRD.md`.
    The brain store lives at `<repo-root>/.brain/instances/`. Walk up.
    """
    parts = srd_path.parts
    try:
        spec_idx = parts.index(".specifications")
        repo_root = Path(*parts[:spec_idx])
        return repo_root / ".brain" / "instances"
    except ValueError:
        # Not in .specifications/ — fall back to CWD/.brain/instances
        return Path.cwd() / ".brain" / "instances"


def _fr_to_requirement_id(srd_path: Path, fr_id: str) -> str:
    """Resolve `FR-NN` / `NFR-NN` → `dna:requirement:<ulid>` using the same
    seed Requirement-emission uses (`req:{srd_path}:{fr_id}`).
    """
    return (
        "dna:requirement:"
        + _deterministic_ulid_from(f"requirement:{srd_path}:{fr_id}")
    )
