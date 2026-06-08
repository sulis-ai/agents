"""Tests for the `for_project` emitter wiring (WP-016, ADR-007).

The v2.2.0 schema (already re-vendored by WP-002's superset) carries an
optional `for_project` ref — a `dna:project:<ulid>` recording which Project
(release-unit / repo) a run operated in. This WP wires the EMITTER half:

  - `compose_lifecyclerun` gains an optional `for_project` param; the field is
    emitted only when provided (so the `unevaluatedProperties: false` schema
    stays clean), and a non-`dna:project:` value is rejected;
  - `emit_change_started_event` resolves the current repo's Project ULID from
    `<repo_root>/.sulis/projects/*.jsonld` and sets `for_project` — or, when no
    Project resolves (meta-run, pre-Project repo), OMITS the field and still
    emits successfully (graceful degradation, ADR-007 §4).

`for_project` is a plain ref modelled exactly like the live
`Workflow.for_project` — NOT a `prov_constraints` edge.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from _brain_emit_helper import _resolve_project_ulid, emit_change_started_event
from _lifecyclerun_emission import compose_lifecyclerun


_STEP = "dna:step:01KT61X5ST01CHANGESTART00A"
_PROJECT = "dna:project:01KT1WPR0JECT0000000000000"

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_VENDORED = (
    _SCRIPTS_DIR.parent
    / "brain"
    / "compiled"
    / "product-development"
    / "lifecyclerun.schema.json"
)


def _schema() -> dict:
    return json.loads(_VENDORED.read_text())


def _write_project_bag(repo_root: Path, project_id: str) -> None:
    """Stage a `.sulis/projects/<slug>.jsonld` bag in `repo_root`, mirroring the
    minter's output shape (a `project-instances` doc with a `projects` array)."""
    projects_dir = repo_root / ".sulis" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    (projects_dir / "thisrepo.jsonld").write_text(
        json.dumps(
            {
                "@context": {"@vocab": "https://sulis.co/dna/", "dna": "https://sulis.co/dna/"},
                "@id": "dna:thisrepo:projects",
                "@type": "project-instances",
                "for_tenant": "dna:tenant:0FX5FX5FX5FX5FX5FX5FX5FX5F",
                "projects": [
                    {
                        "id": project_id,
                        "sys_status": "active",
                        "name": "thisrepo",
                        "belongs_to_tenant": "dna:tenant:0FX5FX5FX5FX5FX5FX5FX5FX5F",
                        "state": "active",
                    }
                ],
            },
            indent=2,
        )
    )


# ─── compose_lifecyclerun(for_project=...) ──────────────────────────────


class TestComposeForProject:
    def test_compose_emits_for_project_when_provided(self) -> None:
        r = compose_lifecyclerun(step=_STEP, outcome="completed", for_project=_PROJECT)
        assert r["for_project"] == _PROJECT
        # still validates against the vendored v2.2.0 schema
        jsonschema.validate(instance=r, schema=_schema())

    def test_compose_omits_for_project_when_none(self) -> None:
        r = compose_lifecyclerun(step=_STEP, outcome="completed", for_project=None)
        assert "for_project" not in r
        jsonschema.validate(instance=r, schema=_schema())

    def test_compose_rejects_non_project_ref(self) -> None:
        with pytest.raises(ValueError, match="for_project"):
            compose_lifecyclerun(
                step=_STEP, outcome="completed", for_project="dna:tenant:0FX5FX5FX5FX5FX5FX5FX5FX5F"
            )

    def test_for_project_shape_pattern_matches_workflow(self) -> None:
        """The accepted for_project pattern equals the live Workflow.for_project
        precedent (foundation v0.5.0) — convention reuse (EP-03)."""
        workflow_schema = json.loads(
            (_SCRIPTS_DIR.parent / "brain" / "compiled" / "foundation" / "workflow.schema.json").read_text()
        )
        wf_pattern = workflow_schema["properties"]["for_project"]["pattern"]
        lr_pattern = _schema()["properties"]["for_project"]["pattern"]
        assert lr_pattern == wf_pattern
        # And a valid dna:project ref matches that pattern.
        assert re.match(wf_pattern, _PROJECT)


# ─── _resolve_project_ulid (the .sulis/projects reader) ─────────────────


class TestResolveProjectUlid:
    def test_resolves_active_project(self, tmp_path: Path) -> None:
        _write_project_bag(tmp_path, _PROJECT)
        assert _resolve_project_ulid(tmp_path) == _PROJECT

    def test_no_projects_dir_returns_none(self, tmp_path: Path) -> None:
        assert _resolve_project_ulid(tmp_path) is None

    def test_malformed_bag_is_skipped(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / ".sulis" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "broken.jsonld").write_text("{not valid json")
        assert _resolve_project_ulid(tmp_path) is None

    def test_bag_without_projects_array_is_skipped(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / ".sulis" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "noarr.jsonld").write_text(json.dumps({"projects": "not-a-list"}))
        assert _resolve_project_ulid(tmp_path) is None

    def test_non_active_project_is_skipped(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / ".sulis" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "stale.jsonld").write_text(
            json.dumps(
                {"projects": [
                    "not-a-dict",
                    {"id": _PROJECT, "sys_status": "deprecated"},
                ]}
            )
        )
        assert _resolve_project_ulid(tmp_path) is None

    def test_invalid_ref_is_skipped(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / ".sulis" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "badref.jsonld").write_text(
            json.dumps({"projects": [{"id": "not-a-project-ref", "sys_status": "active"}]})
        )
        assert _resolve_project_ulid(tmp_path) is None


# ─── emit_change_started_event Project resolution ───────────────────────


class TestChangeStartForProject:
    def test_change_start_run_carries_for_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        _write_project_bag(tmp_path, _PROJECT)
        result = emit_change_started_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="fix-login-bug", primitive="fix",
        )
        assert result is not None
        assert result["for_project"] == _PROJECT
        # the persisted instance validates against v2.2.0
        jsonschema.validate(instance=result, schema=_schema())

    def test_change_start_omits_for_project_when_no_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No .sulis/projects bag at all → graceful omission, emit still succeeds.
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))
        result = emit_change_started_event(
            tmp_path, change_id="01ABC", handle="CH-01ABC",
            slug="meta-run", primitive="fix",
        )
        assert result is not None
        assert "for_project" not in result
        jsonschema.validate(instance=result, schema=_schema())
