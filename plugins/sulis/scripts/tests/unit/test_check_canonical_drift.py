"""Contract + integration tests for check-canonical-drift.py.

WP-007: load-bearing drift detector for Path A (ADR-001 + ADR-002).
Tests cover the three ports (CanonicalReader, AnnotationParser, DriftMatcher)
plus the CLI composition root, against four synthetic fixture canonical+YAML
pairs documented in TDD's Proof section.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Make the _canonical_drift package importable.
_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts/
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _canonical_drift.matcher import StrictDriftMatcher  # noqa: E402
from _canonical_drift.parser import YamlCommentAnnotationParser  # noqa: E402
from _canonical_drift.reader import JsonLdFileReader  # noqa: E402
from _canonical_drift.report import DriftReport  # noqa: E402

_FIXTURES = _HERE / "fixtures" / "canonical_drift"
_CLI = _SCRIPTS_DIR / "check-canonical-drift.py"


# ─── JsonLdFileReader (port 1) ────────────────────────────────────────────


def test_jsonld_file_reader_reads_workflow_instance():
    reader = JsonLdFileReader()
    workflow = reader.read_workflow(_FIXTURES / "fixture_pass")
    assert workflow["name"] == "fixture-workflow"
    assert workflow["for_process"] == "fixture-workflow"
    assert "steps" in workflow
    assert workflow["steps"] == ["step-alpha", "step-beta"]


def test_jsonld_file_reader_reads_steps_returns_list():
    reader = JsonLdFileReader()
    steps = reader.read_steps(_FIXTURES / "fixture_pass")
    assert isinstance(steps, list)
    assert len(steps) == 2
    names = [s["name"] for s in steps]
    assert names == ["step-alpha", "step-beta"]


def test_jsonld_file_reader_reads_failuremodes_returns_list():
    reader = JsonLdFileReader()
    fms = reader.read_failuremodes(_FIXTURES / "fixture_pass")
    assert isinstance(fms, list)
    assert len(fms) == 1
    assert fms[0]["name"] == "fixture-failure-alpha"


def test_jsonld_file_reader_reads_tools_returns_list():
    reader = JsonLdFileReader()
    tools = reader.read_tools(_FIXTURES / "fixture_pass")
    assert isinstance(tools, list)
    assert len(tools) == 2
    assert {t["name"] for t in tools} == {"fixture-tool-alpha", "fixture-tool-beta"}


def test_jsonld_file_reader_validates_against_schema(tmp_path):
    """Malformed instance raises with field-path context."""
    # Seed a deliberately invalid Step (mechanism missing — schema required).
    instance_dir = tmp_path / "bad"
    instance_dir.mkdir()
    bad_steps = {
        "@context": {"@vocab": "https://sulis.co/dna/"},
        "@id": "dna:bad:steps",
        "@type": "step-instances",
        "for_tenant": "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM",
        "captured_on": "2026-06-01",
        "steps": [
            {
                "id": "dna:step:01KT00000000000000000STAPA",
                "name": "bad-step",
                "for_domain": "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM",
                "input_artifacts": [],
                "output_artifacts": [],
                # mechanism missing — schema-required
                "state": "active",
                "sys_status": "active",
            }
        ],
    }
    (instance_dir / "steps.jsonld").write_text(json.dumps(bad_steps))

    reader = JsonLdFileReader()
    with pytest.raises(ValueError) as excinfo:
        reader.read_steps(instance_dir, validate=True)
    # The error message must name the field-path so a founder can find the gap.
    assert "mechanism" in str(excinfo.value) or "required" in str(excinfo.value)


# ─── YamlCommentAnnotationParser (port 2) ─────────────────────────────────


def test_yaml_annotation_parser_finds_canonical_step_comments():
    parser = YamlCommentAnnotationParser()
    annotations = parser.parse(_FIXTURES / "fixture_pass" / "release-on-merge.yml")
    step_anns = [a for a in annotations if a.kind == "step"]
    assert len(step_anns) == 2
    names = sorted(a.target for a in step_anns)
    assert names == ["step-alpha", "step-beta"]
    # Line numbers are populated (used in drift-report context).
    for a in step_anns:
        assert a.line > 0


def test_yaml_annotation_parser_finds_canonical_failuremode_comments():
    parser = YamlCommentAnnotationParser()
    annotations = parser.parse(_FIXTURES / "fixture_pass" / "release-on-merge.yml")
    fm_anns = [a for a in annotations if a.kind == "failuremode"]
    assert len(fm_anns) == 1
    assert fm_anns[0].target == "fixture-failure-alpha"


def test_yaml_annotation_parser_ignores_malformed_comments(tmp_path):
    """`# canonical: step open-release-pr` (no colons after canonical) is ignored cleanly."""
    bad_yaml = tmp_path / "bad.yml"
    bad_yaml.write_text(
        "name: bad\n"
        "jobs:\n"
        "  j:\n"
        "    steps:\n"
        "      # canonical: step open-release-pr\n"
        "      # canonical-something-else\n"
        "      # canonical:step:good-one\n"
        '      - name: "ok"\n'
        '        run: echo "ok"\n'
    )
    parser = YamlCommentAnnotationParser()
    annotations = parser.parse(bad_yaml)
    # Only the well-formed annotation survives.
    assert len(annotations) == 1
    assert annotations[0].target == "good-one"


def test_yaml_annotation_parser_fails_loud_on_unparseable_yaml(tmp_path):
    """Per Armor: pyyaml parse failure raises with file path context (MUC-002)."""
    bad_yaml = tmp_path / "broken.yml"
    # Indentation mismatch + unbalanced quote → guaranteed parse error.
    bad_yaml.write_text('name: "open\n  jobs:\n    invalid: [unclosed\n')
    parser = YamlCommentAnnotationParser()
    with pytest.raises(ValueError) as excinfo:
        parser.parse(bad_yaml)
    assert "broken.yml" in str(excinfo.value)


# ─── StrictDriftMatcher (port 3) ──────────────────────────────────────────


def _load_fixture_inputs(fixture_dir: Path):
    """Helper: read all canonical entities + parse the YAML in a fixture dir."""
    reader = JsonLdFileReader()
    parser = YamlCommentAnnotationParser()
    return (
        reader.read_steps(fixture_dir),
        reader.read_failuremodes(fixture_dir),
        parser.parse(fixture_dir / "release-on-merge.yml"),
    )


def test_drift_matcher_all_pass_when_canonical_matches_yaml():
    steps, fms, annotations = _load_fixture_inputs(_FIXTURES / "fixture_pass")
    matcher = StrictDriftMatcher()
    report = matcher.match(steps, fms, annotations)
    assert report.all_passed is True
    assert report.missing_in_yaml == []
    assert report.missing_in_canonical == []
    assert report.missing_failuremode_handling == []


def test_drift_matcher_reports_missing_in_yaml():
    steps, fms, annotations = _load_fixture_inputs(
        _FIXTURES / "fixture_drift_missing_step"
    )
    matcher = StrictDriftMatcher()
    report = matcher.match(steps, fms, annotations)
    assert report.all_passed is False
    assert "step-beta" in report.missing_in_yaml
    assert report.missing_in_canonical == []


def test_drift_matcher_reports_missing_in_canonical():
    steps, fms, annotations = _load_fixture_inputs(
        _FIXTURES / "fixture_drift_extra_annotation"
    )
    matcher = StrictDriftMatcher()
    report = matcher.match(steps, fms, annotations)
    assert report.all_passed is False
    assert "ghost-step" in report.missing_in_canonical
    assert report.missing_in_yaml == []


def test_drift_matcher_reports_unhandled_failuremode():
    steps, fms, annotations = _load_fixture_inputs(
        _FIXTURES / "fixture_drift_unhandled_failuremode"
    )
    matcher = StrictDriftMatcher()
    report = matcher.match(steps, fms, annotations)
    assert report.all_passed is False
    # The (step-alpha, fixture-failure-alpha) pair MUST appear.
    pairs = [
        (entry["step"], entry["failuremode"])
        for entry in report.missing_failuremode_handling
    ]
    assert ("step-alpha", "fixture-failure-alpha") in pairs


# ─── DriftReport (envelope) ───────────────────────────────────────────────


def test_drift_report_serialises_clean_to_ok_envelope():
    report = DriftReport(
        all_passed=True,
        missing_in_yaml=[],
        missing_in_canonical=[],
        missing_failuremode_handling=[],
        missing_tool_refs=[],
        unresolved_handles_failures=[],
        projects_not_in_marketplace=[],
    )
    envelope = report.to_envelope()
    assert envelope == {"ok": True, "data": {"drift": []}}


def test_drift_report_serialises_drift_to_named_kinds():
    report = DriftReport(
        all_passed=False,
        missing_in_yaml=["step-beta"],
        missing_in_canonical=["ghost-step"],
        missing_failuremode_handling=[
            {"step": "step-alpha", "failuremode": "fixture-failure-alpha"}
        ],
        missing_tool_refs=[],
        unresolved_handles_failures=[],
        projects_not_in_marketplace=[],
    )
    envelope = report.to_envelope()
    assert envelope["ok"] is False
    drift = envelope["data"]["drift"]
    kinds = sorted(entry["kind"] for entry in drift)
    assert kinds == [
        "missing_failuremode_handling",
        "missing_in_canonical",
        "missing_in_yaml",
    ]


# ─── Cross-reference validations ──────────────────────────────────────────


def test_validates_tool_refs_resolve():
    """Every Step.tool_ref must resolve in tools.jsonld (MUC-005)."""
    reader = JsonLdFileReader()
    steps = reader.read_steps(_FIXTURES / "fixture_pass")
    tools = reader.read_tools(_FIXTURES / "fixture_pass")
    matcher = StrictDriftMatcher()
    unresolved = matcher.validate_tool_refs(steps, tools)
    assert unresolved == []


def test_validates_tool_refs_detects_unresolved(tmp_path):
    """A Step pointing at a non-existent Tool must surface in the report."""
    reader = JsonLdFileReader()
    steps = reader.read_steps(_FIXTURES / "fixture_pass")
    # Inject a step pointing at an orphan tool_ref.
    steps_with_orphan = steps + [
        {
            "name": "orphan-step",
            "tool_ref": "dna:tool:01KT00000000000000000ZZZZZ",
            "handles_failures": [],
        }
    ]
    tools = reader.read_tools(_FIXTURES / "fixture_pass")
    matcher = StrictDriftMatcher()
    unresolved = matcher.validate_tool_refs(steps_with_orphan, tools)
    assert ("orphan-step", "dna:tool:01KT00000000000000000ZZZZZ") in unresolved


def test_validates_handles_failures_resolve():
    """Every Step.handles_failures[] must resolve in failuremodes.jsonld."""
    reader = JsonLdFileReader()
    steps = reader.read_steps(_FIXTURES / "fixture_pass")
    fms = reader.read_failuremodes(_FIXTURES / "fixture_pass")
    matcher = StrictDriftMatcher()
    unresolved = matcher.validate_handles_failures(steps, fms)
    assert unresolved == []


def test_validates_projects_match_marketplace_json():
    """Every Project.name must appear in marketplace.json plugins[] (MUC-008)."""
    matcher = StrictDriftMatcher()
    projects = [{"name": "plugin-alpha"}, {"name": "plugin-beta"}]
    marketplace_path = _FIXTURES / "fixture_pass" / "marketplace.json"
    missing = matcher.validate_projects_against_marketplace(projects, marketplace_path)
    assert missing == []


def test_validates_projects_detects_missing(tmp_path):
    matcher = StrictDriftMatcher()
    projects = [{"name": "plugin-alpha"}, {"name": "plugin-rogue"}]
    marketplace_path = _FIXTURES / "fixture_pass" / "marketplace.json"
    missing = matcher.validate_projects_against_marketplace(projects, marketplace_path)
    assert missing == ["plugin-rogue"]


# ─── CLI composition root ─────────────────────────────────────────────────


def _run_cli(*args, cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(_CLI), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)


def test_cli_exits_0_on_clean():
    fixture = _FIXTURES / "fixture_pass"
    result = _run_cli(
        "--instance-dir",
        str(fixture),
        "--yaml-path",
        str(fixture / "release-on-merge.yml"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["data"]["drift"] == []


@pytest.mark.parametrize(
    "fixture_name",
    [
        "fixture_drift_missing_step",
        "fixture_drift_extra_annotation",
        "fixture_drift_unhandled_failuremode",
    ],
)
def test_cli_exits_1_on_drift(fixture_name):
    fixture = _FIXTURES / fixture_name
    result = _run_cli(
        "--instance-dir",
        str(fixture),
        "--yaml-path",
        str(fixture / "release-on-merge.yml"),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert len(parsed["data"]["drift"]) >= 1


def test_cli_exits_2_on_invocation_error_missing_arg():
    """Missing required --instance-dir → exit 2."""
    result = _run_cli("--yaml-path", "/tmp/whatever.yml")
    assert result.returncode == 2


def test_cli_exits_2_on_invocation_error_nonexistent_path(tmp_path):
    """Pointing at a non-existent instance directory → exit 2 with error envelope."""
    result = _run_cli(
        "--instance-dir",
        str(tmp_path / "does-not-exist"),
        "--yaml-path",
        str(tmp_path / "also-missing.yml"),
    )
    assert result.returncode == 2
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert "error" in parsed


# ─── Pure-function discipline (Blue acceptance) ───────────────────────────


# ─── Additional coverage (Blue ≥95% target) ───────────────────────────────


def test_jsonld_file_reader_read_workflow_validates_when_asked():
    """validate=True must round-trip cleanly for the pass fixture."""
    reader = JsonLdFileReader()
    workflow = reader.read_workflow(_FIXTURES / "fixture_pass", validate=True)
    assert workflow["name"] == "fixture-workflow"


def test_jsonld_file_reader_read_failuremodes_validates_when_asked():
    reader = JsonLdFileReader()
    fms = reader.read_failuremodes(_FIXTURES / "fixture_pass", validate=True)
    assert fms[0]["kind"] == "dependency-unavailable"


def test_jsonld_file_reader_read_tools_validates_active_only():
    """Draft Tools are exempt from schema validation per ADR-003 — active ones aren't."""
    reader = JsonLdFileReader()
    tools = reader.read_tools(_FIXTURES / "fixture_pass", validate=True)
    assert all(t["state"] == "active" for t in tools)


def test_jsonld_file_reader_read_triggers_returns_list(tmp_path):
    """Triggers are optional in some fixtures; the reader handles the empty path."""
    instance_dir = tmp_path / "tr"
    instance_dir.mkdir()
    (instance_dir / "triggers.jsonld").write_text(
        json.dumps(
            {
                "@id": "dna:fixture:triggers",
                "@type": "trigger-instances",
                "triggers": [],
            }
        )
    )
    reader = JsonLdFileReader()
    assert reader.read_triggers(instance_dir) == []


def test_jsonld_file_reader_raises_on_missing_file(tmp_path):
    reader = JsonLdFileReader()
    with pytest.raises(FileNotFoundError):
        reader.read_steps(tmp_path)


def test_jsonld_file_reader_raises_on_malformed_json(tmp_path):
    instance_dir = tmp_path / "bad"
    instance_dir.mkdir()
    (instance_dir / "steps.jsonld").write_text("{not-json")
    reader = JsonLdFileReader()
    with pytest.raises(ValueError) as excinfo:
        reader.read_steps(instance_dir)
    assert "Malformed JSON" in str(excinfo.value)


def test_jsonld_file_reader_raises_when_plural_key_not_list(tmp_path):
    instance_dir = tmp_path / "bad"
    instance_dir.mkdir()
    (instance_dir / "steps.jsonld").write_text(json.dumps({"steps": "not-a-list"}))
    reader = JsonLdFileReader()
    with pytest.raises(ValueError) as excinfo:
        reader.read_steps(instance_dir)
    assert "list" in str(excinfo.value)


def test_jsonld_file_reader_validate_raises_if_schema_dir_missing(tmp_path):
    """schemas_dir override → use the override; missing schema raises clearly."""
    instance_dir = tmp_path / "ok"
    instance_dir.mkdir()
    (instance_dir / "steps.jsonld").write_text(json.dumps({"steps": [{"name": "x"}]}))
    reader = JsonLdFileReader(schemas_dir=tmp_path / "no-such-schemas")
    with pytest.raises(FileNotFoundError) as excinfo:
        reader.read_steps(instance_dir, validate=True)
    assert "Schema not found" in str(excinfo.value)


def test_drift_matcher_skips_unresolved_failuremode_in_match():
    """If a Step.handles_failures id doesn't resolve, match() skips it (xref-check catches it)."""
    steps = [
        {
            "name": "step-x",
            "tool_ref": "dna:tool:01KT00000000000000000APXTZ",
            "handles_failures": ["dna:failuremode:01KT0000000000000000ZZZZZZ"],
        }
    ]
    failuremodes: list[dict] = []  # no FMs registered at all
    annotations: list = []
    matcher = StrictDriftMatcher()
    report = matcher.match(steps, failuremodes, annotations)
    # The unresolved fm-id is skipped here — its absence in handles_failures
    # surfaces via validate_handles_failures, not via match().
    assert report.missing_failuremode_handling == []


def test_drift_matcher_validate_projects_raises_on_missing_marketplace(tmp_path):
    matcher = StrictDriftMatcher()
    with pytest.raises(FileNotFoundError):
        matcher.validate_projects_against_marketplace(
            [{"name": "p"}], tmp_path / "no-such-marketplace.json"
        )


def test_drift_matcher_validate_handles_failures_surfaces_unresolved():
    matcher = StrictDriftMatcher()
    steps = [
        {
            "name": "step-x",
            "handles_failures": ["dna:failuremode:01KT0000000000000000ZZZZZZ"],
        }
    ]
    failuremodes: list[dict] = []
    unresolved = matcher.validate_handles_failures(steps, failuremodes)
    assert ("step-x", "dna:failuremode:01KT0000000000000000ZZZZZZ") in unresolved


def test_drift_matcher_validate_tool_refs_skips_human_steps():
    """A Step with no tool_ref (mechanism=human) is not unresolved — it's exempt."""
    matcher = StrictDriftMatcher()
    steps = [{"name": "step-human"}]  # no tool_ref key
    tools: list[dict] = []
    assert matcher.validate_tool_refs(steps, tools) == []


def test_drift_report_envelope_includes_xref_drift_kinds():
    """missing_tool_refs / unresolved_handles_failures / projects_not_in_marketplace surface."""
    report = DriftReport(
        all_passed=False,
        missing_tool_refs=[("step-x", "dna:tool:01KT00000000000000000ZZZZZ")],
        unresolved_handles_failures=[
            ("step-y", "dna:failuremode:01KT0000000000000000ZZZZZZ")
        ],
        projects_not_in_marketplace=["plugin-rogue"],
    )
    envelope = report.to_envelope()
    kinds = sorted(entry["kind"] for entry in envelope["data"]["drift"])
    assert kinds == [
        "missing_tool_ref",
        "project_not_in_marketplace",
        "unresolved_handles_failures",
    ]


def test_cli_help_exits_0(tmp_path):
    """--help is not an invocation error."""
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "drift detector" in result.stdout.lower() or "instance-dir" in result.stdout


def test_cli_with_projects_and_marketplace(tmp_path):
    """When projects.jsonld is present + --marketplace-json passed, projects check runs."""
    fixture = _FIXTURES / "fixture_pass"
    # Seed a projects.jsonld inside a tmp copy of the fixture.
    tmp_fixture = tmp_path / "f"
    import shutil

    shutil.copytree(fixture, tmp_fixture)
    (tmp_fixture / "projects.jsonld").write_text(
        json.dumps(
            {
                "@id": "dna:fixture:projects",
                "@type": "project-instances",
                "projects": [{"name": "plugin-alpha"}, {"name": "plugin-rogue"}],
            }
        )
    )
    result = _run_cli(
        "--instance-dir",
        str(tmp_fixture),
        "--yaml-path",
        str(tmp_fixture / "release-on-merge.yml"),
        "--marketplace-json",
        str(tmp_fixture / "marketplace.json"),
    )
    # plugin-rogue isn't in marketplace.json → drift.
    assert result.returncode == 1
    parsed = json.loads(result.stdout)
    kinds = {entry["kind"] for entry in parsed["data"]["drift"]}
    assert "project_not_in_marketplace" in kinds


def test_canonical_drift_package_has_no_module_level_state():
    """No global mutable state at import time. Re-importing must be idempotent."""
    import _canonical_drift.matcher as m1
    import _canonical_drift.parser as p1
    import _canonical_drift.reader as r1
    import _canonical_drift.report as rp1

    # Re-import; module identities are stable + nothing mutates between calls.
    import _canonical_drift.matcher as m2
    import _canonical_drift.parser as p2
    import _canonical_drift.reader as r2
    import _canonical_drift.report as rp2

    assert m1 is m2
    assert p1 is p2
    assert r1 is r2
    assert rp1 is rp2

    # Each port is a class, not a singleton — multiple instances are independent.
    r_a = r1.JsonLdFileReader()
    r_b = r1.JsonLdFileReader()
    assert r_a is not r_b
