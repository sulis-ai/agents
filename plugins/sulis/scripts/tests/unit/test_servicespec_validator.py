"""Tests for `_servicespec_validator.py` — the Lovable Test mechanical checks
(Decompose Validation Rubric Phase 7).

The Lovable Test bar: an AI agent must be able to build a working integration
against the manifest with no human docs. These tests pin every check that
contributes to that bar — per-operation completeness, per-error completeness,
entity-ref resolution against the marketplace's vendored compiled schemas,
binding completeness, permission namespacing.

A real `decision.schema.json` is already vendored at
`plugins/sulis/brain/compiled/product-development/` from CH-01KSWB, so the
entity-resolution checks (7.11) exercise a genuine compiled artifact, not a
fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from _servicespec_validator import (
    Issue,
    compute_verdict,
    validate_servicespec,
    validate_servicespec_file,
)


# ─── helpers ──────────────────────────────────────────────────────────────


def _lovable_manifest() -> dict:
    """A ServiceSpec manifest that passes every Lovable Test check.

    Built minimally — one operation, one error, one resolvable entity — so a
    targeted mutation isolates the corresponding check.
    """
    return {
        "name": "decision-service",
        "version": "1.0.0",
        "description": "Manages design Decisions.",
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
                    "whenToUse": "When a non-trivial choice has been made.",
                    "prerequisites": ["caller authenticated"],
                    "nextSteps": ["GET /api/v1/decisions/{id}"],
                },
            },
        ],
        "errors": {
            "VALIDATION_ERROR": {
                "httpStatus": 400,
                "user_action": "Check required fields.",
                "developer_action": "Call /api/v1/services/validate first.",
                "retryable": False,
            },
        },
        "entities": [
            # decision.schema.json is vendored from CH-01KSWB
            {"id": "dna:entity:decision"},
        ],
    }


def _issue_ids(issues: list[Issue]) -> list[str]:
    return [i.check_id for i in issues]


# ─── happy path ───────────────────────────────────────────────────────────


class TestLovableManifestPasses:
    def test_returns_no_issues_for_a_lovable_manifest(self) -> None:
        issues = validate_servicespec(_lovable_manifest())
        must_issues = [i for i in issues if i.severity == "MUST"]
        assert must_issues == [], f"unexpected MUST issues: {must_issues}"

    def test_verdict_is_pass_for_a_lovable_manifest(self) -> None:
        verdict = compute_verdict(validate_servicespec(_lovable_manifest()))
        assert verdict in ("PASS", "PASS-WITH-RATIONALE")


# ─── per-operation checks (7.03..7.06, 7.12, 7.13) ────────────────────────


class TestOperationsChecks:
    def test_no_operations_at_all_fails_7_03(self) -> None:
        m = _lovable_manifest()
        m["operations"] = []
        issues = validate_servicespec(m)
        assert "7.03" in _issue_ids(issues)
        assert compute_verdict(issues) == "FAIL"

    def test_operation_missing_description_fails_7_04(self) -> None:
        m = _lovable_manifest()
        del m["operations"][0]["description"]
        issues = validate_servicespec(m)
        assert "7.04" in _issue_ids(issues)

    def test_operation_missing_user_guide_fails_7_05(self) -> None:
        m = _lovable_manifest()
        del m["operations"][0]["user_guide"]
        issues = validate_servicespec(m)
        ids = _issue_ids(issues)
        # 7.05 must fire (whenToUse missing), MUST severity
        names = [i for i in issues if i.check_id == "7.05"]
        assert names and all(i.severity == "MUST" for i in names)

    def test_operation_missing_prerequisites_is_should_not_must_7_06(self) -> None:
        m = _lovable_manifest()
        del m["operations"][0]["user_guide"]["prerequisites"]
        issues = validate_servicespec(m)
        prereq_issues = [i for i in issues if i.check_id == "7.06"]
        assert any(i.severity == "SHOULD" for i in prereq_issues)
        # And no MUST from this single deletion alone
        assert not any(i.severity == "MUST" for i in prereq_issues)

    def test_operation_missing_binding_fails_7_12(self) -> None:
        m = _lovable_manifest()
        del m["operations"][0]["binding"]
        issues = validate_servicespec(m)
        assert "7.12" in _issue_ids(issues)

    def test_operation_binding_missing_host_fails_7_12_named(self) -> None:
        m = _lovable_manifest()
        del m["operations"][0]["binding"]["host"]
        issues = validate_servicespec(m)
        host_issues = [
            i for i in issues if i.check_id == "7.12" and "host" in i.message
        ]
        assert host_issues, f"expected a 7.12 issue naming `host`, got {issues}"

    def test_operation_with_bare_permission_name_fails_7_13(self) -> None:
        m = _lovable_manifest()
        m["operations"][0]["permission"] = "create"  # no namespace, no colon
        issues = validate_servicespec(m)
        assert "7.13" in _issue_ids(issues)

    def test_operation_with_namespaced_permission_passes_7_13(self) -> None:
        m = _lovable_manifest()
        m["operations"][0]["permission"] = "decisions.entities:create"
        issues = validate_servicespec(m)
        assert "7.13" not in _issue_ids(issues)


# ─── per-error checks (7.07..7.10) ────────────────────────────────────────


class TestErrorCatalogChecks:
    def test_error_missing_httpStatus_fails_7_07(self) -> None:
        m = _lovable_manifest()
        del m["errors"]["VALIDATION_ERROR"]["httpStatus"]
        issues = validate_servicespec(m)
        assert "7.07" in _issue_ids(issues)

    def test_error_httpStatus_must_be_int_7_07(self) -> None:
        m = _lovable_manifest()
        m["errors"]["VALIDATION_ERROR"]["httpStatus"] = "400"  # str, not int
        issues = validate_servicespec(m)
        assert "7.07" in _issue_ids(issues)

    def test_error_missing_user_action_fails_7_08(self) -> None:
        m = _lovable_manifest()
        del m["errors"]["VALIDATION_ERROR"]["user_action"]
        issues = validate_servicespec(m)
        assert "7.08" in _issue_ids(issues)

    def test_error_missing_developer_action_fails_7_09(self) -> None:
        m = _lovable_manifest()
        del m["errors"]["VALIDATION_ERROR"]["developer_action"]
        issues = validate_servicespec(m)
        assert "7.09" in _issue_ids(issues)

    def test_error_missing_retryable_is_should_not_must_7_10(self) -> None:
        m = _lovable_manifest()
        del m["errors"]["VALIDATION_ERROR"]["retryable"]
        issues = validate_servicespec(m)
        retry_issues = [i for i in issues if i.check_id == "7.10"]
        assert retry_issues
        assert all(i.severity == "SHOULD" for i in retry_issues)


# ─── entity-reference resolution (7.11) ───────────────────────────────────


class TestEntityReferenceResolution:
    def test_resolvable_entity_passes_7_11(self) -> None:
        # decision.schema.json is vendored from CH-01KSWB — must resolve.
        m = _lovable_manifest()
        m["entities"] = [{"id": "dna:entity:decision"}]
        issues = validate_servicespec(m)
        assert "7.11" not in _issue_ids(issues)

    def test_unresolvable_entity_fails_7_11(self) -> None:
        m = _lovable_manifest()
        m["entities"] = [{"id": "dna:entity:nonexistent_xyz_widget"}]
        issues = validate_servicespec(m)
        assert "7.11" in _issue_ids(issues)

    def test_malformed_entity_id_fails_7_11(self) -> None:
        m = _lovable_manifest()
        m["entities"] = [{"id": "not-a-dna-entity-id"}]
        issues = validate_servicespec(m)
        assert "7.11" in _issue_ids(issues)

    def test_bare_string_entity_id_is_accepted(self) -> None:
        m = _lovable_manifest()
        m["entities"] = ["dna:entity:decision"]
        issues = validate_servicespec(m)
        assert "7.11" not in _issue_ids(issues)


# ─── verdict ──────────────────────────────────────────────────────────────


class TestComputeVerdict:
    def test_no_issues_is_pass(self) -> None:
        assert compute_verdict([]) == "PASS"

    def test_only_should_failures_is_pass_with_rationale(self) -> None:
        issues = [Issue("7.10", "SHOULD", "test", "loc")]
        assert compute_verdict(issues) == "PASS-WITH-RATIONALE"

    def test_any_must_failure_is_fail(self) -> None:
        issues = [Issue("7.04", "MUST", "test", "loc")]
        assert compute_verdict(issues) == "FAIL"

    def test_mixed_severities_with_a_must_still_fails(self) -> None:
        issues = [
            Issue("7.04", "MUST", "test", "loc"),
            Issue("7.06", "SHOULD", "test", "loc"),
            Issue("7.14", "MAY", "test", "loc"),
        ]
        assert compute_verdict(issues) == "FAIL"


# ─── file I/O (7.02) ──────────────────────────────────────────────────────


class TestValidateServiceSpecFile:
    def test_file_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "spec.yaml"
        path.write_text(yaml.safe_dump(_lovable_manifest()))

        issues = validate_servicespec_file(path)

        must_issues = [i for i in issues if i.severity == "MUST"]
        assert must_issues == [], f"unexpected MUST issues: {must_issues}"

    def test_malformed_yaml_fails_7_02(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("operations: [unbalanced {{{\n")

        issues = validate_servicespec_file(path)

        assert "7.02" in _issue_ids(issues)

    def test_non_object_root_fails_7_02(self, tmp_path: Path) -> None:
        path = tmp_path / "list-at-root.yaml"
        path.write_text("- not\n- a\n- mapping\n")

        issues = validate_servicespec_file(path)

        assert "7.02" in _issue_ids(issues)


# ─── tolerant variants (casing of user_action / userAction etc.) ──────────


class TestCasingTolerance:
    def test_camelCase_userAction_passes(self) -> None:
        m = _lovable_manifest()
        m["errors"]["VALIDATION_ERROR"]["userAction"] = m["errors"][
            "VALIDATION_ERROR"
        ].pop("user_action")
        issues = validate_servicespec(m)
        assert "7.08" not in _issue_ids(issues)

    def test_camelCase_developerAction_passes(self) -> None:
        m = _lovable_manifest()
        m["errors"]["VALIDATION_ERROR"]["developerAction"] = m["errors"][
            "VALIDATION_ERROR"
        ].pop("developer_action")
        issues = validate_servicespec(m)
        assert "7.09" not in _issue_ids(issues)

    def test_camelCase_userGuide_passes(self) -> None:
        m = _lovable_manifest()
        m["operations"][0]["userGuide"] = m["operations"][0].pop("user_guide")
        issues = validate_servicespec(m)
        assert "7.05" not in _issue_ids(issues)
