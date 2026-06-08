"""WP-007 — `--lifecycle-steps-parity` mode for check-canonical-drift.py.

Path A requires the canonical lifecycle-steps instances (WP-001) and the
re-vendored `lifecyclerun` schema (WP-002) to stay in lock-step. This WP
EXTENDS the existing drift detector (reused, not rebuilt — Reuse before
build) with a new checked set: the lifecycle-steps canonical.

The parity assertion has two surfaces:

- **canonical Step coverage** — `instances/lifecycle-steps/steps.jsonld`
  MUST carry the three canonical Step ULIDs pinned in the requirements
  document (`change-started`, `change-shipped`,
  `unclassified-lifecycle-step`). A missing or extra Step ULID is drift.
- **schema regression guard** — the `lifecyclerun` schema MUST NOT carry a
  `step_name` property. DR-009 swapped the required `step_name` string for a
  `step` ref (v1.0.0 → v2.0.0); a `step_name` reappearing in the schema is a
  regression that re-forks the vendored schema from canonical.

These are REAL-subprocess tests: they invoke the CLI as an actual subprocess
and assert on the exit code + JSON envelope, the same discipline the
`--scope` tests use (the gap that lets a broken CLI mode ship is the
*absence* of a real-subprocess test).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts
_CLI = _SCRIPTS_DIR / "check-canonical-drift.py"

# The committed canonical lifecycle-steps instance dir + the re-vendored
# lifecyclerun schema, resolved relative to this test file (works from any cwd).
_REPO_ROOT = _SCRIPTS_DIR.parent.parent.parent  # → repo root
_LIFECYCLE_STEPS_DIR = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "lifecycle-steps"
)
_LIFECYCLERUN_SCHEMA = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _run_parity(instance_dir: Path, schema_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--lifecycle-steps-parity",
            "--instance-dir",
            str(instance_dir),
            "--schema-path",
            str(schema_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ─── Red tests ──────────────────────────────────────────────────────────────


def test_conformance_exits_zero():
    """The committed canonical + schema conform → detector exits 0.

    Fails today: `--lifecycle-steps-parity` is an unrecognised flag, so
    argparse exits 2.
    """
    result = _run_parity(_LIFECYCLE_STEPS_DIR, _LIFECYCLERUN_SCHEMA)

    assert result.returncode == 0, (
        f"committed canonical + schema should exit 0; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True


def test_missing_step_ulid_fails(tmp_path):
    """Dropping a canonical Step → non-zero with structured drift.

    Copies the committed canonical, removes the `change-shipped` Step, and
    points the detector at the mutated copy. A missing canonical Step ULID is
    drift. Fails today: unrecognised flag → exit 2 for the wrong reason.
    """
    mutated_dir = tmp_path / "lifecycle-steps"
    mutated_dir.mkdir()
    src = json.loads((_LIFECYCLE_STEPS_DIR / "steps.jsonld").read_text())
    src["steps"] = [s for s in src["steps"] if s["name"] != "change-shipped"]
    (mutated_dir / "steps.jsonld").write_text(json.dumps(src, indent=2))

    result = _run_parity(mutated_dir, _LIFECYCLERUN_SCHEMA)

    assert result.returncode != 0, (
        f"a missing canonical Step should exit non-zero; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    # The failure MUST be the STRUCTURED drift reason — a populated
    # data.drift surface naming the missing Step — not an invocation error.
    assert "data" in envelope, (
        f"drift must surface the structured envelope, not an invocation error; "
        f"got {envelope!r}"
    )
    assert envelope["data"]["drift"], (
        f"drift list must be non-empty for a missing Step; got {envelope!r}"
    )


def test_schema_step_name_regression_fails(tmp_path):
    """A `step_name` property reappearing in the schema → non-zero.

    Copies the committed schema, re-introduces a `step_name` property (the
    DR-009 regression the swap to `step` removed), and points the detector at
    the mutated copy. Fails today: unrecognised flag → exit 2.
    """
    # Copy the canonical instance dir verbatim (Steps are conformant) so the
    # ONLY drift surface exercised is the schema regression.
    conformant_dir = tmp_path / "lifecycle-steps"
    conformant_dir.mkdir()
    shutil.copy(_LIFECYCLE_STEPS_DIR / "steps.jsonld", conformant_dir / "steps.jsonld")

    schema = json.loads(_LIFECYCLERUN_SCHEMA.read_text())
    # Re-introduce the dropped field — the exact regression the guard catches.
    schema["properties"]["step_name"] = {"type": "string"}
    mutated_schema = tmp_path / "lifecyclerun.schema.json"
    mutated_schema.write_text(json.dumps(schema, indent=2))

    result = _run_parity(conformant_dir, mutated_schema)

    assert result.returncode != 0, (
        f"a resurrected step_name property should exit non-zero; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert "data" in envelope, (
        f"schema regression must surface the structured envelope; got {envelope!r}"
    )
    assert envelope["data"]["drift"], (
        f"drift list must be non-empty for a step_name regression; got {envelope!r}"
    )


def test_extra_step_ulid_fails(tmp_path):
    """An extra Step ULID not in the pinned set → non-zero with drift.

    Parity is bidirectional: the canonical may not carry a Step the pinned
    inventory doesn't recognise either. Adding an unrecognised Step ULID is
    drift just as dropping one is.
    """
    mutated_dir = tmp_path / "lifecycle-steps"
    mutated_dir.mkdir()
    src = json.loads((_LIFECYCLE_STEPS_DIR / "steps.jsonld").read_text())
    extra = dict(src["steps"][0])
    extra["id"] = "dna:step:01KT61X5ST04UNRECOGN1ZED0A"
    extra["name"] = "unrecognised-step"
    src["steps"] = [*src["steps"], extra]
    (mutated_dir / "steps.jsonld").write_text(json.dumps(src, indent=2))

    result = _run_parity(mutated_dir, _LIFECYCLERUN_SCHEMA)

    assert result.returncode != 0, (
        f"an extra canonical Step should exit non-zero; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert any(
        d["kind"] == "step_ulid_mismatch" and d.get("direction") == "extra_in_canonical"
        for d in envelope["data"]["drift"]
    ), f"expected an extra_in_canonical drift entry; got {envelope!r}"


def test_parity_requires_schema_path_exits_two():
    """`--lifecycle-steps-parity` with no --schema-path → invocation error (exit 2).

    Pins the requiredness contract: the parity mode needs both --instance-dir
    and --schema-path; omitting one is an invocation error, not silent drift.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--lifecycle-steps-parity",
            "--instance-dir",
            str(_LIFECYCLE_STEPS_DIR),
            # --schema-path deliberately omitted
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2, (
        f"missing --schema-path should exit 2; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert "error" in envelope
