"""End-to-end CLI tests for `sulis-validate-servicespec` — exercises the
JSON envelope contract callers (the rubric agent) rely on.
"""

from __future__ import annotations

import yaml
from pathlib import Path


def _lovable_manifest_text() -> str:
    return yaml.safe_dump({
        "name": "decision-service",
        "version": "1.0.0",
        "operations": [
            {
                "name": "create_decision",
                "description": "Create a new Decision entity.",
                "permission": "decisions.entities:create",
                "binding": {
                    "host": "{platform_host}",
                    "basePath": "/api/v1",
                    "method": "POST",
                    "auth": "bearer",
                },
                "user_guide": {
                    "whenToUse": "When a non-trivial choice is recorded.",
                    "prerequisites": ["caller authenticated"],
                    "nextSteps": ["GET /api/v1/decisions/{id}"],
                },
            },
        ],
        "errors": {
            "VALIDATION_ERROR": {
                "httpStatus": 400,
                "user_action": "Check required fields.",
                "developer_action": "Use /api/v1/services/validate.",
                "retryable": False,
            },
        },
        "entities": [{"id": "dna:entity:decision"}],
    })


def _bad_manifest_text() -> str:
    return yaml.safe_dump({
        "name": "bad-service",
        "operations": [
            {
                "name": "bad_op",
                # description, user_guide, binding, permission all missing
            },
        ],
    })


class TestSulisValidateServiceSpecCli:
    def test_lovable_manifest_returns_pass_via_cli(
        self, tmp_path: Path, run_tool
    ) -> None:
        path = tmp_path / "spec.yaml"
        path.write_text(_lovable_manifest_text())

        result = run_tool("sulis-validate-servicespec", "--from-manifest", str(path))

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}, "
            f"stderr={result.stderr!r}"
        )
        assert result.data["verdict"] in ("PASS", "PASS-WITH-RATIONALE")
        assert result.data["summary"]["must_failures"] == 0

    def test_failing_manifest_returns_fail_envelope(
        self, tmp_path: Path, run_tool
    ) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text(_bad_manifest_text())

        result = run_tool("sulis-validate-servicespec", "--from-manifest", str(path))

        assert not result.ok, "expected ok=false for a bad manifest"
        assert result.data["verdict"] == "FAIL"
        assert result.data["summary"]["must_failures"] > 0
        assert result.returncode == 1

        # Every issue has the expected structured shape.
        for issue in result.data["issues"]:
            assert set(issue.keys()) == {
                "check_id", "severity", "message", "location"
            }
            assert issue["severity"] in ("MUST", "SHOULD", "MAY")

    def test_missing_manifest_path_returns_error_envelope(
        self, tmp_path: Path, run_tool
    ) -> None:
        result = run_tool(
            "sulis-validate-servicespec",
            "--from-manifest", str(tmp_path / "does-not-exist.yaml"),
        )

        assert not result.ok
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_custom_schemas_dir_is_respected(
        self, tmp_path: Path, run_tool
    ) -> None:
        path = tmp_path / "spec.yaml"
        path.write_text(_lovable_manifest_text())

        # Point at an empty dir — the `dna:entity:decision` ref no longer
        # resolves and 7.11 must fire.
        empty = tmp_path / "empty-brain-compiled"
        empty.mkdir()

        result = run_tool(
            "sulis-validate-servicespec",
            "--from-manifest", str(path),
            "--schemas-dir", str(empty),
        )

        assert not result.ok, "expected ok=false when entity refs don't resolve"
        check_ids = [i["check_id"] for i in result.data["issues"]]
        assert "7.11" in check_ids
