"""Structural assertion: branch-ci.yml wires the routing coverage gate (WP-008).

Per ADR-005 the coverage gate (`sulis-route check`, built in WP-007) is wired
into the **existing** `branch-ci.yml` as a single step — not a new workflow.
The step must:

  * exist, named "routing coverage gate";
  * invoke `python3 plugins/sulis/scripts/sulis-route check --repo-root .`
    (the exit-1-on-failure contract is what blocks merge);
  * sit **after** the lint step and **before** the `unit tests` step (ADR-005:
    a fast structural check, adjacent to lint, surfaces a coverage break
    before the slower test step).

CI YAML is not unit-testable the way Python is, so this is a structural
assertion over the workflow text rather than an executed gate. PyYAML is not
available stdlib-only, so the parse is a deliberately boring line-scan: find
the `- name:` step boundaries and the ordered list of step names, plus the
literal `run:` invocation line (WP-008 DoD: a string search for the exact
`sulis-route check` invocation is acceptable and boring).

This test FAILS RED against the pre-edit tree (the step does not yet exist),
and PASSES once the step is added to branch-ci.yml in the specified position.

Stdlib + pytest only, Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "branch-ci.yml"

_GATE_STEP_NAME = "routing coverage gate"
_LINT_STEP_PREFIX = "lint"  # the lint step name starts with "lint —"
_UNIT_TESTS_STEP_NAME = "unit tests"
_GATE_INVOCATION = "python3 plugins/sulis/scripts/sulis-route check --repo-root ."


def _step_names_in_order() -> list[str]:
    """Ordered list of step names from the single `branch-ci` job.

    Boring line-scan: a step name line looks like `      - name: <value>`
    (optionally `- name:` already begun by the list dash). We capture the
    text after `name:` for every such line, preserving file order.
    """
    names: list[str] = []
    for raw in _WORKFLOW.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("- name:"):
            names.append(stripped[len("- name:"):].strip())
        elif stripped.startswith("name:") and raw.lstrip().startswith("name:"):
            # `name:` lines that are part of a step block (indented), not the
            # top-level workflow `name: branch-ci` (column 0). Guard on indent.
            if raw[0] in (" ", "\t"):
                names.append(stripped[len("name:"):].strip())
    return names


def test_workflow_exists():
    """Guard: branch-ci.yml resolves to a real file in the live tree."""
    assert _WORKFLOW.is_file(), f"missing workflow {_WORKFLOW}"


def test_gate_step_present():
    """The `routing coverage gate` step exists in the workflow.

    Fails RED before the edit (the step is absent).
    """
    names = _step_names_in_order()
    assert _GATE_STEP_NAME in names, (
        f"step '{_GATE_STEP_NAME}' missing from branch-ci.yml steps: {names}"
    )


def test_gate_invokes_sulis_route_check():
    """The gate runs the exact `sulis-route check --repo-root .` invocation.

    The exit-1-on-failure contract of that command is what fails the step and
    blocks merge (ADR-005). Fails RED before the edit.
    """
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert _GATE_INVOCATION in text, (
        f"branch-ci.yml does not invoke '{_GATE_INVOCATION}'"
    )


def test_gate_positioned_after_lint_before_unit_tests():
    """The gate sits after the lint step and before the `unit tests` step.

    ADR-005: a fast structural check adjacent to lint, surfacing a coverage
    break before the slower unit-test step. Fails RED before the edit (the
    gate step is absent, so its index can't be located).
    """
    names = _step_names_in_order()

    lint_idx = next(
        (i for i, n in enumerate(names) if n.startswith(_LINT_STEP_PREFIX)),
        None,
    )
    assert lint_idx is not None, f"no lint step found in {names}"

    unit_idx = next(
        (i for i, n in enumerate(names) if n == _UNIT_TESTS_STEP_NAME),
        None,
    )
    assert unit_idx is not None, f"no '{_UNIT_TESTS_STEP_NAME}' step found in {names}"

    gate_idx = next(
        (i for i, n in enumerate(names) if n == _GATE_STEP_NAME),
        None,
    )
    assert gate_idx is not None, (
        f"step '{_GATE_STEP_NAME}' missing from steps: {names}"
    )

    assert lint_idx < gate_idx < unit_idx, (
        f"'{_GATE_STEP_NAME}' (index {gate_idx}) must sit after lint "
        f"(index {lint_idx}) and before '{_UNIT_TESTS_STEP_NAME}' "
        f"(index {unit_idx}). Order: {names}"
    )
