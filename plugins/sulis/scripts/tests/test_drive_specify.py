"""Behavioural tests for the drive-specify fixture harness (WP-001).

KIND = methodology: the behavioural test drives the specify stage on a fixture
and asserts the produced artifact. These tests invoke `_drive_specify.py` as a
CLI subprocess — the same entrypoint the SC-01/02/03/05/15/16/18 scenarios use
as their first step — and assert on the document it writes.

The driver is deterministic (NFR-04): same fixture + depth ⇒ identical output.
`--depth` is an explicit input; the driver never consults the founder proposal
flow (it stays non-interactive). The driver reuses the real specify path
(`_specify_classifier`); it does not re-implement document emission.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent
_DRIVER = _SCRIPTS_DIR / "_drive_specify.py"


def _run_driver(
    *, fixture: str, depth: str, out: Path
) -> subprocess.CompletedProcess[str]:
    """Invoke the driver CLI as a subprocess. Returns the completed process."""
    return subprocess.run(
        [
            sys.executable,
            str(_DRIVER),
            "--fixture",
            fixture,
            "--depth",
            depth,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_drive_specify_emits_document_at_lite(tmp_path: Path) -> None:
    """Driving the sample-user-facing fixture at lite writes a document at --out.

    Asserts the happy path: a real specify drive on a known fixture produces a
    file at the requested output path and exits 0.
    """
    out = tmp_path / "design.md"

    proc = _run_driver(fixture="sample-user-facing", depth="lite", out=out)

    assert proc.returncode == 0, (
        f"driver exited non-zero: rc={proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert out.exists(), "driver did not write a document at --out"
    assert out.read_text(encoding="utf-8").strip(), "driver wrote an empty document"


def test_drive_specify_deterministic_same_fixture_same_depth(tmp_path: Path) -> None:
    """Two runs with the same fixture + depth produce a byte-identical document.

    NFR-04: the harness is deterministic. Re-running the same fixture at the
    same depth must yield the same section set — no timestamps, no random IDs,
    no environment-dependent content in the produced artifact.
    """
    out_a = tmp_path / "run-a.md"
    out_b = tmp_path / "run-b.md"

    proc_a = _run_driver(fixture="sample-user-facing", depth="standard", out=out_a)
    proc_b = _run_driver(fixture="sample-user-facing", depth="standard", out=out_b)

    assert proc_a.returncode == 0, f"run A failed: {proc_a.stderr}"
    assert proc_b.returncode == 0, f"run B failed: {proc_b.stderr}"

    content_a = out_a.read_text(encoding="utf-8")
    content_b = out_b.read_text(encoding="utf-8")
    assert content_a == content_b, (
        "driver is not deterministic — two runs of the same fixture + depth "
        "produced different documents (NFR-04 violation)"
    )


def test_drive_specify_nonzero_on_stage_failure(tmp_path: Path) -> None:
    """A broken / unknown fixture causes the driver to exit non-zero.

    A stage failure (here: a fixture that does not exist) must surface as a
    non-zero exit so the scenarios that invoke the driver fail loudly rather
    than silently producing a half-document.
    """
    assert _DRIVER.exists(), (
        "driver module is missing — this test must exercise the driver's own "
        "stage-failure path, not a Python file-not-found"
    )
    out = tmp_path / "should-not-exist.md"

    proc = _run_driver(
        fixture="no-such-fixture-deliberately-broken", depth="lite", out=out
    )

    assert proc.returncode != 0, (
        "driver exited 0 on a broken fixture; expected a non-zero stage failure"
    )
    # The failure must come from the driver recognising an unknown fixture —
    # the error names the fixture, not a Python tracebacked import error.
    assert "no-such-fixture-deliberately-broken" in proc.stderr, (
        f"driver did not surface the unknown-fixture name in its error:\n{proc.stderr}"
    )
    assert not out.exists(), "driver wrote an output document despite a stage failure"


@pytest.mark.parametrize(
    "fixture",
    ["sample-user-facing", "no-dependencies", "sample-tool-surface"],
)
def test_drive_specify_ships_named_fixtures(fixture: str, tmp_path: Path) -> None:
    """All three named fixtures the WP ships are drivable.

    Guards the fixture set the downstream scenarios depend on: sample-user-facing
    (surface heuristic fires), no-dependencies (drives the n/a-marking path for
    SC-03), and sample-tool-surface (tool operations, for SC-18).
    """
    out = tmp_path / f"{fixture}.md"

    proc = _run_driver(fixture=fixture, depth="deep", out=out)

    assert proc.returncode == 0, (
        f"fixture {fixture!r} not drivable: rc={proc.returncode}\nstderr={proc.stderr}"
    )
    assert out.exists(), f"fixture {fixture!r} produced no document"


# ─── In-process unit tests (importable surface + defensive branches) ────────
#
# These import the driver directly (conftest puts the scripts dir on sys.path)
# so the defensive branches the CLI's `choices=` guard makes unreachable via
# subprocess are still covered, and the SC-03 / SC-18 content paths are
# asserted at the section level.

import _drive_specify as drive_specify  # noqa: E402  (after sys.path setup)


def test_load_fixture_unknown_raises() -> None:
    """An unknown fixture name raises DriveSpecifyError naming the fixture."""
    with pytest.raises(drive_specify.DriveSpecifyError, match="unknown fixture"):
        drive_specify.load_fixture("definitely-not-a-fixture")


def test_load_fixture_malformed_manifest_raises(tmp_path, monkeypatch) -> None:
    """A manifest that is valid JSON but not an object raises a stage failure."""
    bad_dir = tmp_path / "methodology" / "bad-shape"
    bad_dir.mkdir(parents=True)
    (bad_dir / "manifest.json").write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(drive_specify, "_FIXTURES_DIR", tmp_path / "methodology")

    with pytest.raises(drive_specify.DriveSpecifyError, match="must be a JSON object"):
        drive_specify.load_fixture("bad-shape")


def test_run_specify_stage_unknown_depth_raises() -> None:
    """An unknown depth raises — the defensive guard the CLI's choices= shadows."""
    manifest = drive_specify.FixtureManifest(
        slug="x",
        primitive="fix",
        intent="i",
        paths=[],
        dependencies=[],
        tool_operations=[],
    )
    with pytest.raises(drive_specify.DriveSpecifyError, match="unknown depth"):
        drive_specify.run_specify_stage(manifest, "gigantic")


def test_no_dependencies_fixture_marks_section_na(tmp_path: Path) -> None:
    """SC-03 path: a fixture with no dependencies marks the dependency section n/a."""
    out = tmp_path / "doc.md"
    drive_specify.drive(fixture="no-dependencies", depth="lite", out=out)
    body = out.read_text(encoding="utf-8")
    assert "n/a — this fixture declares no dependencies." in body


def test_tool_surface_fixture_renders_contract_operations(tmp_path: Path) -> None:
    """SC-18 path: a tool-surface fixture renders its operations in the contract."""
    out = tmp_path / "doc.md"
    drive_specify.drive(fixture="sample-tool-surface", depth="deep", out=out)
    body = out.read_text(encoding="utf-8")
    assert "`export_report`" in body
    assert "Interface contract — tool operations:" in body


def test_document_carries_full_canonical_section_set(tmp_path: Path) -> None:
    """The produced document carries all ten canonical sections (ADR-002)."""
    out = tmp_path / "doc.md"
    drive_specify.drive(fixture="sample-user-facing", depth="standard", out=out)
    body = out.read_text(encoding="utf-8")
    for number, title in drive_specify._SECTIONS:
        assert f"## {number}. {title}" in body, f"missing §{number} {title}"


def test_main_returns_zero_on_success(tmp_path: Path) -> None:
    """main() returns 0 and writes the document on a good drive."""
    out = tmp_path / "doc.md"
    rc = drive_specify.main(
        ["--fixture", "sample-user-facing", "--depth", "lite", "--out", str(out)]
    )
    assert rc == 0
    assert out.exists()


def test_main_returns_one_on_stage_failure(tmp_path: Path) -> None:
    """main() returns 1 (not a traceback) when the fixture is unknown."""
    out = tmp_path / "doc.md"
    rc = drive_specify.main(["--fixture", "nope", "--depth", "lite", "--out", str(out)])
    assert rc == 1
    assert not out.exists()
