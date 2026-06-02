"""WP-001 — `--scope <entity-file>` mode for check-canonical-drift.py.

The discover-project verifier (`_discovery/verifier.py`) invokes the drift
detector scoped to ONE just-minted Project entity:

    check-canonical-drift.py --scope <entity> \\
        --cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref

Before this WP, `check-canonical-drift.py` had no `--scope` flag — argparse
marked `--instance-dir` / `--yaml-path` as `required=True`, so every verifier
invocation exited 2 (`the following arguments are required`), the verifier
read non-zero as drift, and every consumer-repo mint was rolled back.

These are REAL-subprocess tests (the gap that let the broken `--scope` call
ship was the *absence* of a real-subprocess test). They invoke the CLI as an
actual subprocess and assert on the exit code + JSON envelope.

The `--scope` mode:

- reads a Project bag (``{"projects": [ {Project}, ... ]}``) — the shape the
  discover-project mint writes;
- schema-validates each contained Project against the vendored
  ``plugins/sulis/brain/compiled/foundation/project.schema.json``;
- applies the cross-tenant-ref allowlist from
  ``--cross-tenant-refs-allowed-for`` (a ``release_workflow_ref`` pointing at
  the marketplace tenant's Workflow is NOT drift when allowlisted);
- exits 0 (clean) / 1 (drift) / 2 (invocation error) preserving the existing
  exit-code + ``{"ok": bool, ...}`` envelope contract;
- does NOT require ``--instance-dir`` / ``--yaml-path`` (modes coexist).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# The marketplace release-train Workflow ULID — the cross-tenant ref a
# consumer Project's release_workflow_ref legitimately points at (ADR-002).
_MARKETPLACE_RELEASE_WORKFLOW_ULID = "dna:workflow:01KT0RTRA1NWFW00000000000A"

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts
_CLI = _SCRIPTS_DIR / "check-canonical-drift.py"


def _valid_tenant_ulid() -> str:
    """Derive a schema-valid consumer-tenant ULID via the real deriver."""
    sys.path.insert(0, str(_SCRIPTS_DIR))
    from _discovery.tenant import Sha256CrockfordTenantDeriver

    return Sha256CrockfordTenantDeriver().derive_consumer_tenant("acme/consumer")


def _valid_project() -> dict:
    """A schema-valid minted-shape Project (mirrors _compose_entity output)."""
    return {
        "id": "dna:project:01KT00000000000000000CTPRJ",
        "sys_status": "active",
        "name": "fixture-consumer-project",
        "belongs_to_tenant": _valid_tenant_ulid(),
        "type": "library",
        "source": json.dumps(
            {"repo": "acme/consumer", "path": ".", "primary_branch": "main"}
        ),
        "version_files": ["package.json"],
        "branch_policy": "trunk",
        "belongs_to_product_ref": "acme-product",
        "depends_on": [],
        "consumed_by": [],
        "release_workflow_ref": _MARKETPLACE_RELEASE_WORKFLOW_ULID,
        "description": "A fixture consumer project for the --scope tests.",
        "state": "active",
        "valid_from": "2026-06-01T00:00:00Z",
        "confidence": 1.0,
    }


def _write_bag(tmp_path: Path, project: dict, name: str = "entity.jsonld") -> Path:
    """Write a Project-instances bag (the discover-project mint shape)."""
    bag = {
        "@context": {
            "@vocab": "https://sulis.co/dna/",
            "dna": "https://sulis.co/dna/",
        },
        "@id": "dna:fixture:scope-test",
        "@type": "project-instances",
        "for_tenant": project["belongs_to_tenant"],
        "captured_on": "2026-06-01",
        "projects": [project],
    }
    p = tmp_path / name
    p.write_text(json.dumps(bag, indent=2), encoding="utf-8")
    return p


def _run_scope(entity_path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--scope",
            str(entity_path),
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ─── Red tests ──────────────────────────────────────────────────────────────


def test_scope_valid_entity_exits_zero(tmp_path):
    """`--scope <valid-entity>` exits 0 with envelope ok=True.

    The valid entity's release_workflow_ref points at the marketplace Workflow
    ULID (allowlisted). Fails today: argparse rejects --scope → exit 2.
    """
    entity = _write_bag(tmp_path, _valid_project())

    result = _run_scope(
        entity, "--cross-tenant-refs-allowed-for", "release_workflow_ref"
    )

    assert result.returncode == 0, (
        f"--scope valid entity should exit 0; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True


def test_scope_drifted_entity_exits_nonzero(tmp_path):
    """`--scope <drifted-entity>` exits non-zero with a structured failure.

    The drifted entity is a Project missing the `version_files` required field
    (per project.schema.json). Fails today: exit 2 for the wrong reason
    (unrecognised --scope), not the structured drift reason.
    """
    drifted = _valid_project()
    del drifted["version_files"]  # schema-required → schema-invalid → drift
    entity = _write_bag(tmp_path, drifted)

    result = _run_scope(
        entity, "--cross-tenant-refs-allowed-for", "release_workflow_ref"
    )

    assert result.returncode != 0, (
        f"--scope drifted entity should exit non-zero; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    # The failure MUST be the STRUCTURED DRIFT reason — a populated
    # data.drift list — not the invocation-error envelope. Today the broken
    # code exits 2 (argparse: unrecognised --scope) with an {"error": ...}
    # envelope and NO data.drift, so this assertion fails for the right
    # reason in RED.
    assert "data" in envelope, (
        f"drift must surface the structured envelope, not an invocation error; "
        f"got {envelope!r}"
    )
    assert envelope["data"]["drift"], (
        f"drift list must be non-empty for a schema-invalid entity; got {envelope!r}"
    )


def test_scope_does_not_require_instance_dir_or_yaml_path(tmp_path):
    """`--scope <valid>` with NO --instance-dir / --yaml-path exits 0 (not 2).

    Pins the "modes coexist" contract: the requiredness of --instance-dir /
    --yaml-path moves to a post-parse check so --scope can run standalone.
    Fails today: argparse demands --instance-dir + --yaml-path → exit 2.
    """
    entity = _write_bag(tmp_path, _valid_project())

    # Deliberately omit --instance-dir AND --yaml-path.
    result = _run_scope(
        entity, "--cross-tenant-refs-allowed-for", "release_workflow_ref"
    )

    assert result.returncode == 0, (
        f"--scope must not require --instance-dir/--yaml-path; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True
