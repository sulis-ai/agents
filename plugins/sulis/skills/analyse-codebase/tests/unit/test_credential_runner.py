"""Unit tests for Phase 1.17 — Credential Scanning runner.

Privacy contract (MUST): hashes only, never plaintext values. The runner
relies on detect-secrets' SHA-1 hashing and must propagate ONLY the hash.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from probe.models import CredentialFinding, RepoInput
from probe.runners.credential_runner import (
    CredentialRunner,
    _load_baseline,
    _parse_scan_output,
)


def _input(root: Path) -> RepoInput:
    return RepoInput(
        repo_root=str(root),
        project="test",
        extra_excludes=(),
        output_dir=str(root),
        workspaces=(),
    )


# ─── Parser tests (no external tool needed) ───────────────────────────────


def test_parse_scan_output_extracts_findings():
    """Synthetic detect-secrets JSON → CredentialFinding list."""
    raw = json.dumps({
        "version": "1.5.0",
        "results": {
            "src/leaked.py": [
                {
                    "type": "AWS Access Key",
                    "filename": "src/leaked.py",
                    "hashed_secret": "abc123def4567890abcdef1234567890abcdef12",
                    "is_verified": False,
                    "line_number": 1,
                },
            ],
        },
    })
    findings = _parse_scan_output(raw, baseline_hashes=set())
    assert len(findings) == 1
    f = findings[0]
    assert f.secret_type == "AWS Access Key"
    assert f.file == "src/leaked.py"
    assert f.line == 1
    assert f.hashed_secret == "abc123def4567890abcdef1234567890abcdef12"
    assert f.is_known is False


def test_parse_scan_output_marks_known_from_baseline():
    raw = json.dumps({
        "results": {
            "src/leaked.py": [
                {
                    "type": "AWS Access Key",
                    "hashed_secret": "knownhash000",
                    "line_number": 1,
                },
                {
                    "type": "Private Key",
                    "hashed_secret": "newhash999",
                    "line_number": 5,
                },
            ],
        },
    })
    baseline = {("src/leaked.py", "knownhash000")}
    findings = _parse_scan_output(raw, baseline_hashes=baseline)
    by_hash = {f.hashed_secret: f for f in findings}
    assert by_hash["knownhash000"].is_known is True
    assert by_hash["newhash999"].is_known is False


def test_load_baseline_returns_file_hash_pairs(tmp_path: Path):
    baseline = tmp_path / ".secrets.baseline"
    baseline.write_text(json.dumps({
        "results": {
            "src/a.py": [{"hashed_secret": "h1"}, {"hashed_secret": "h2"}],
            "src/b.py": [{"hashed_secret": "h3"}],
        },
    }))
    pairs = _load_baseline(baseline)
    assert ("src/a.py", "h1") in pairs
    assert ("src/a.py", "h2") in pairs
    assert ("src/b.py", "h3") in pairs


def test_load_baseline_handles_corrupt_file(tmp_path: Path):
    baseline = tmp_path / ".secrets.baseline"
    baseline.write_text("not json")
    pairs = _load_baseline(baseline)
    assert pairs == set()


# ─── PRIVACY CONTRACT (CRITICAL) ──────────────────────────────────────────


def test_credential_finding_never_contains_value():
    """The dataclass schema must have NO field for plaintext.

    If a future refactor adds a 'secret' or 'value' field to CredentialFinding,
    this test fails — forcing reviewer attention to the privacy contract.
    """
    fields = {f.name for f in CredentialFinding.__dataclass_fields__.values()}
    forbidden = {"secret", "value", "plaintext", "raw_secret", "password"}
    assert fields.isdisjoint(forbidden), (
        f"CredentialFinding must not store plaintext secrets. "
        f"Forbidden fields found: {fields & forbidden}"
    )


def test_parser_never_propagates_secret_field_from_input():
    """If detect-secrets ever included a 'secret' field, the parser must ignore it.

    Defence-in-depth: a buggy detect-secrets version that surfaces plaintext
    should still produce hash-only output through our runner.
    """
    raw = json.dumps({
        "results": {
            "leak.py": [
                {
                    "type": "AWS Access Key",
                    "hashed_secret": "abc",
                    "line_number": 1,
                    "secret": "AKIA-PLAINTEXT-LEAKED-HERE",   # poisoned input
                },
            ],
        },
    })
    findings = _parse_scan_output(raw, baseline_hashes=set())
    serialised = json.dumps([f.__dict__ for f in findings])
    assert "AKIA-PLAINTEXT-LEAKED-HERE" not in serialised
    assert "PLAINTEXT" not in serialised


# ─── Graceful skip when tool absent ───────────────────────────────────────


def test_runner_skips_when_detect_secrets_missing(tmp_path: Path, monkeypatch):
    """When detect-secrets is not on PATH, the runner returns skipped=True."""
    monkeypatch.setattr(shutil, "which", lambda _t: None)
    result = CredentialRunner().run_repo(_input(tmp_path))
    assert result.payload["skipped"] is True
    assert result.payload["skip_reason"] is not None
    assert "pipx install detect-secrets" in result.payload["skip_reason"]
    assert result.payload["findings"] == []


# ─── End-to-end (skipped unless detect-secrets installed) ─────────────────


def _has_detect_secrets() -> bool:
    return shutil.which("detect-secrets") is not None


@pytest.mark.skipif(
    not _has_detect_secrets(),
    reason="detect-secrets not installed; install via pipx for this test",
)
def test_runner_end_to_end_finds_aws_key(tmp_path: Path):
    """With detect-secrets installed: a planted AWS key is detected by hash."""
    src = tmp_path / "src"
    src.mkdir()
    # Random-looking AWS key that is NOT the AWS docs EXAMPLE value (which
    # would be filtered by the EXCLUDE_LINES_RE).
    (src / "leak.py").write_text(
        'AWS_ACCESS_KEY = "AKIA1234567890ABCDEF"\n'
    )
    # detect-secrets requires git context for baseline-mode operations
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    result = CredentialRunner().run_repo(_input(tmp_path))
    assert result.payload["skipped"] is False
    assert len(result.payload["findings"]) >= 1
    types = result.payload["by_type"].keys()
    assert any("AWS" in t for t in types)
    # Privacy contract: no plaintext key in serialised payload
    serialised = json.dumps(result.payload)
    assert "AKIA1234567890ABCDEF" not in serialised


@pytest.mark.skipif(
    not _has_detect_secrets(),
    reason="detect-secrets not installed",
)
def test_runner_respects_baseline(tmp_path: Path):
    """A finding present in .secrets.baseline is marked is_known=True."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "leak.py").write_text(
        'AWS_ACCESS_KEY = "AKIA9999999999ABCDEF"\n'
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)

    # First pass: scan with no baseline to learn the hash.
    first = CredentialRunner().run_repo(_input(tmp_path))
    assert first.payload["findings"], "expected at least one finding"
    known_hash = first.payload["findings"][0]["hashed_secret"]
    known_file = first.payload["findings"][0]["file"]

    # Write a baseline that acknowledges this finding.
    (tmp_path / ".secrets.baseline").write_text(json.dumps({
        "version": "1.5.0",
        "results": {
            known_file: [{
                "type": first.payload["findings"][0]["secret_type"],
                "hashed_secret": known_hash,
                "is_verified": False,
                "line_number": first.payload["findings"][0]["line"],
            }],
        },
    }))

    second = CredentialRunner().run_repo(_input(tmp_path))
    by_hash = {f["hashed_secret"]: f for f in second.payload["findings"]}
    assert by_hash[known_hash]["is_known"] is True
