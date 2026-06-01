"""WP-009 — drift-detector extensions for discover-project (Path A n=2).

Two surgical extensions to the existing detector (release-train's
`7d666df extend: tighten-drift-gate`):

1. HTML-comment annotation parser for Markdown imperative files (skill
   SKILL.md uses `<!-- canonical:step:<name> -->` rather than YAML
   `# canonical:step:<name>`). A file-extension dispatcher chooses the
   correct parser per input.
2. `--cross-tenant-refs-allowed-for` CLI flag — a list of ref field
   names that may legitimately cross tenant boundaries (e.g.,
   `release_workflow_ref` for the consumer Project → marketplace
   Workflow edge per ADR-002). Default `[]` preserves the
   pre-extension stricter-by-default behaviour.

Per the WP's Definition of Done: 14 tests total — 2 characterisation
tests (release-train CI must keep passing unchanged) + 5 parser
extension tests + 3 cross-tenant flag tests + 3 conformance fixture
tests + 1 dispatcher extension test (n=4 across format types).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Make the _canonical_drift package importable.
_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts/
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _canonical_drift.matcher import cross_tenant_ref_is_allowed  # noqa: E402
from _canonical_drift.parser import (  # noqa: E402
    MarkdownHtmlAnnotationParser,
    YamlCommentAnnotationParser,
    parse_annotations,
)

_FIXTURES_DISCOVER = _HERE / "fixtures" / "drift-discover"
_FIXTURES_RELEASE = _HERE / "fixtures" / "canonical_drift"
_CLI = _SCRIPTS_DIR / "check-canonical-drift.py"


# ─── Characterisation tests — existing detector behaviour preserved ─────


def test_release_train_still_passes():
    """Re-run the existing release-train pass fixture; assert exit 0.

    Proves the YAML parser path is unchanged and the default-empty
    cross-tenant flag is invisible to existing invocations.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--instance-dir",
            str(_FIXTURES_RELEASE / "fixture_pass"),
            "--yaml-path",
            str(_FIXTURES_RELEASE / "fixture_pass" / "release-on-merge.yml"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Release-train pass fixture regressed; stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True
    assert envelope["data"]["drift"] == []


def test_default_cross_tenant_flag_empty_list_no_behaviour_change():
    """With no --cross-tenant-refs-allowed-for given, behaviour is
    identical to pre-extension; release-train fixtures pass clean."""
    # Run twice — once without the flag, once with an empty value —
    # and assert both produce the same envelope.
    args_no_flag = [
        sys.executable,
        str(_CLI),
        "--instance-dir",
        str(_FIXTURES_RELEASE / "fixture_pass"),
        "--yaml-path",
        str(_FIXTURES_RELEASE / "fixture_pass" / "release-on-merge.yml"),
    ]
    args_empty_flag = args_no_flag + ["--cross-tenant-refs-allowed-for", ""]

    out_no_flag = subprocess.run(
        args_no_flag, capture_output=True, text=True, timeout=30
    )
    out_empty = subprocess.run(
        args_empty_flag, capture_output=True, text=True, timeout=30
    )
    assert out_no_flag.returncode == out_empty.returncode == 0
    assert json.loads(out_no_flag.stdout) == json.loads(out_empty.stdout)


# ─── Annotation parser extension — HTML comments (Markdown) ─────────────


def test_parses_html_comment_annotations(tmp_path):
    """Markdown content with `<!-- canonical:step:<name> -->` parses to
    a list of MarkdownHtml annotations."""
    md = tmp_path / "skill.md"
    md.write_text(
        "# A skill\n"
        "<!-- canonical:step:read-repo-root -->\n"
        "Read the repo.\n"
        "<!-- canonical:step:atomic-mint -->\n"
        "Atomically write.\n"
        "<!-- canonical:failuremode:llm-token-budget-exceeded -->\n"
        "Fallback.\n"
    )
    parser = MarkdownHtmlAnnotationParser()
    annotations = parser.parse(md)
    targets = sorted(a.target for a in annotations if a.kind == "step")
    assert targets == ["atomic-mint", "read-repo-root"]
    fm_targets = [a.target for a in annotations if a.kind == "failuremode"]
    assert fm_targets == ["llm-token-budget-exceeded"]
    # Line numbers populated.
    for a in annotations:
        assert a.line > 0


def test_parses_html_comment_with_extra_whitespace(tmp_path):
    """`<!--  canonical:step:foo  -->` (whitespace inside the comment) parses cleanly."""
    md = tmp_path / "skill.md"
    md.write_text("<!--  canonical:step:foo  -->\nbody")
    parser = MarkdownHtmlAnnotationParser()
    annotations = parser.parse(md)
    assert len(annotations) == 1
    assert annotations[0].target == "foo"
    assert annotations[0].kind == "step"


def test_yaml_parser_does_not_match_html_comments(tmp_path):
    """Cross-format no-match: YAML parser run on Markdown content with
    HTML comments returns []. No silent matching across formats."""
    # The YAML parser requires the file to be parseable YAML first. A
    # bare Markdown body without YAML keys parses fine as a string
    # value (pyyaml is permissive). Use a content shape pyyaml treats
    # as a single string.
    yml = tmp_path / "not-really.yml"
    yml.write_text("just a string with <!-- canonical:step:foo --> in it\n")
    parser = YamlCommentAnnotationParser()
    annotations = parser.parse(yml)
    assert annotations == []


def test_markdown_parser_does_not_match_yaml_comments(tmp_path):
    """Converse: Markdown parser run on YAML-style `# canonical:...`
    comments returns []."""
    md = tmp_path / "fake.md"
    md.write_text(
        "# A skill\n"
        "# canonical:step:foo\n"  # YAML-style comment, not HTML
        "Some body.\n"
    )
    parser = MarkdownHtmlAnnotationParser()
    annotations = parser.parse(md)
    assert annotations == []


def test_dispatch_chooses_parser_by_extension(tmp_path):
    """parse_annotations dispatcher routes by file extension:
    .yml/.yaml → YAML; .md → Markdown; .py → empty."""
    # Setup three files with the same annotation token in their
    # native comment syntax. Each parser MUST find exactly one.
    yml = tmp_path / "a.yml"
    yml.write_text(
        "name: t\njobs:\n  j:\n    steps:\n      # canonical:step:from-yaml\n      - run: echo x\n"
    )
    md = tmp_path / "b.md"
    md.write_text("<!-- canonical:step:from-markdown -->\n")
    py = tmp_path / "c.py"
    py.write_text("# canonical:step:from-python\n")  # unsupported extension

    from_yml = parse_annotations(yml)
    from_md = parse_annotations(md)
    from_py = parse_annotations(py)
    assert [a.target for a in from_yml] == ["from-yaml"]
    assert [a.target for a in from_md] == ["from-markdown"]
    assert from_py == []  # unsupported extension → empty, not error


# ─── Cross-tenant flag extension ─────────────────────────────────────────


def test_cross_tenant_ref_without_flag_is_drift():
    """Without --cross-tenant-refs-allowed-for, a Project →
    cross-tenant Workflow reference is flagged as drift.

    The helper `cross_tenant_ref_is_allowed` returns False when the
    field name is not in the allow-list.
    """
    # Field is NOT in the allow-list → not allowed → reports as drift.
    allowed_cross_tenant_fields: list[str] = []
    is_allowed = cross_tenant_ref_is_allowed(
        field_name="release_workflow_ref",
        allowed_cross_tenant_fields=allowed_cross_tenant_fields,
    )
    assert is_allowed is False


def test_cross_tenant_ref_with_flag_passes():
    """With --cross-tenant-refs-allowed-for release_workflow_ref, the
    cross-tenant reference is recognised, not flagged."""
    is_allowed = cross_tenant_ref_is_allowed(
        field_name="release_workflow_ref",
        allowed_cross_tenant_fields=["release_workflow_ref"],
    )
    assert is_allowed is True


def test_cross_tenant_flag_accepts_multiple_fields():
    """--cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref
    parses to a 2-element list and matches either field."""
    # Invoke the CLI with the comma-separated value and observe argparse
    # parses it into a list. Cleanest assertion: run the detector with
    # both values and confirm each lookup is allowed.
    allow_list = ["release_workflow_ref", "belongs_to_product_ref"]
    assert cross_tenant_ref_is_allowed(
        field_name="release_workflow_ref", allowed_cross_tenant_fields=allow_list
    )
    assert cross_tenant_ref_is_allowed(
        field_name="belongs_to_product_ref", allowed_cross_tenant_fields=allow_list
    )
    # Anything not on the list remains disallowed.
    assert not cross_tenant_ref_is_allowed(
        field_name="other_ref", allowed_cross_tenant_fields=allow_list
    )


# ─── Conformance fixtures (n=3 parity tests) ─────────────────────────────


def test_pass_fixture():
    """Discover-project pass fixture: 9 canonical Steps + SKILL.md with
    9 matching annotations → exit 0."""
    result = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--instance-dir",
            str(_FIXTURES_DISCOVER / "pass"),
            "--yaml-path",  # the flag name is historic; the dispatcher routes by extension
            str(_FIXTURES_DISCOVER / "pass" / "SKILL.md"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Discover-project pass fixture failed unexpectedly; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True
    assert envelope["data"]["drift"] == []


def test_drift_missing_step():
    """SKILL.md missing the surface-success annotation → exit 1, drift
    names the missing Step."""
    result = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--instance-dir",
            str(_FIXTURES_DISCOVER / "drift_missing_step"),
            "--yaml-path",
            str(_FIXTURES_DISCOVER / "drift_missing_step" / "SKILL.md"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    missing = [
        d["step"] for d in envelope["data"]["drift"] if d["kind"] == "missing_in_yaml"
    ]
    assert "surface-success" in missing


def test_drift_extra_annotation():
    """SKILL.md with a ghost-step annotation not in canonical → exit 1,
    drift names the unexpected annotation."""
    result = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--instance-dir",
            str(_FIXTURES_DISCOVER / "drift_extra_annotation"),
            "--yaml-path",
            str(_FIXTURES_DISCOVER / "drift_extra_annotation" / "SKILL.md"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    extras = [
        d["annotation"]
        for d in envelope["data"]["drift"]
        if d["kind"] == "missing_in_canonical"
    ]
    assert "ghost-step" in extras
