"""Phase 0 pilot tests — exercise the end-to-end loop on wpx-pipeline run.

What's verified:
- Client construction with repo_root + project
- pipeline.run() invokes the right binary with the right argv
- Stdout JSON envelope is parsed into a typed Pydantic PipelineResult
- Successful outcome ("success") returns cleanly
- Blocker outcome ("blocker") returns as a normal result (NOT an exception)
- Exit code 1 with ok:false raises ExpectedError
- Exit code 2 raises InternalError
- Missing binary raises BinaryNotFoundError
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sulis_execution import (
    AsyncSulisExecution,
    BinaryNotFoundError,
    ExpectedError,
    InternalError,
    PipelineResult,
    SulisExecution,
)


def _success_envelope() -> dict:
    """A wpx-pipeline-shaped success envelope."""
    return {
        "ok": True,
        "data": {
            "result": {
                "wp": "WP-001",
                "outcome": "success",
                "merge_sha": "abc123def456",
                "deploy_url": "https://staging.example.com",
                "deploy_workflow_run": "12345",
                "health_status": "healthy",
                "health_url": "https://staging.example.com/health",
                "smoke_verdict": "PASS",
                "blocker_reason": None,
                "ci_poll_skipped": False,
                "merge_already_complete": False,
                "started_at": "2026-05-21T12:00:00Z",
                "completed_at": "2026-05-21T12:30:00Z",
            }
        },
    }


def _blocker_envelope() -> dict:
    """A wpx-pipeline-shaped blocker envelope (operation ran but reported a deterministic failure)."""
    return {
        "ok": True,
        "data": {
            "result": {
                "wp": "WP-001",
                "outcome": "blocker",
                "merge_sha": None,
                "deploy_url": None,
                "deploy_workflow_run": None,
                "health_status": None,
                "health_url": None,
                "smoke_verdict": None,
                "blocker_reason": "CI checks failed after 3 rebase attempts",
                "ci_poll_skipped": False,
                "merge_already_complete": False,
                "started_at": "2026-05-21T12:00:00Z",
                "completed_at": "2026-05-21T12:15:00Z",
            }
        },
    }


# ─── Happy path ───────────────────────────────────────────────────────


def test_pipeline_run_success_returns_typed_result(
    make_fake_binary, fake_wpx_dir, tmp_repo_root
):
    make_fake_binary(
        "wpx-pipeline", stdout_payload=_success_envelope(), exit_code=0
    )

    client = SulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )
    result = client.pipeline.run(
        wp="WP-001",
        branch="feat/wp-001-x",
        dev_sha_at_creation="abc123de",
        deploy_workflow="Deploy to Dev",
    )

    assert isinstance(result, PipelineResult)
    assert result.wp == "WP-001"
    assert result.outcome == "success"
    assert result.merge_sha == "abc123def456"
    assert result.health_status == "healthy"
    assert result.smoke_verdict == "PASS"
    assert isinstance(result.started_at, datetime)


# ─── Blocker is NOT an exception ──────────────────────────────────────


def test_pipeline_run_blocker_returns_result_not_exception(
    make_fake_binary, fake_wpx_dir, tmp_repo_root
):
    """The big v0.2.0 contract: outcome=blocker is a successful result."""
    make_fake_binary(
        "wpx-pipeline",
        stdout_payload=_blocker_envelope(),
        exit_code=1,  # blocker uses exit 1 with ok:true
    )

    client = SulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )
    result = client.pipeline.run(
        wp="WP-001",
        branch="feat/wp-001-x",
        dev_sha_at_creation="abc123de",
        deploy_workflow="Deploy to Dev",
    )

    # Crucial: no exception raised
    assert isinstance(result, PipelineResult)
    assert result.outcome == "blocker"
    assert result.blocker_reason == "CI checks failed after 3 rebase attempts"
    assert result.merge_sha is None


# ─── ExpectedError on validation failure ──────────────────────────────


def test_pipeline_run_expected_error_when_cli_rejects_input(
    make_fake_binary, fake_wpx_dir, tmp_repo_root
):
    """Exit 1 + ok:false → ExpectedError."""
    make_fake_binary(
        "wpx-pipeline",
        stdout_payload={
            "ok": False,
            "error": "WP-001 not found in INDEX.md",
            "context": {"code": "wp_not_found", "wp": "WP-001"},
        },
        exit_code=1,
    )

    client = SulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )

    with pytest.raises(ExpectedError) as excinfo:
        client.pipeline.run(
            wp="WP-001",
            branch="feat/wp-001-x",
            dev_sha_at_creation="abc123de",
            deploy_workflow="Deploy to Dev",
        )

    err = excinfo.value
    assert err.category == "expected"
    assert "WP-001 not found" in err.message
    assert err.code == "wp_not_found"
    assert err.transport_code == 1
    assert err.correlation_id is not None  # Always populated


# ─── InternalError on crash ───────────────────────────────────────────


def test_pipeline_run_internal_error_on_crash(
    make_fake_binary, fake_wpx_dir, tmp_repo_root
):
    """Exit 2 → InternalError, with the traceback captured."""
    make_fake_binary(
        "wpx-pipeline",
        stdout_payload="",
        stderr_payload="Traceback (most recent call last):\n  File \"...\", line 1, in <module>\n    raise RuntimeError('boom')\nRuntimeError: boom\n",
        exit_code=2,
    )

    client = SulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )

    with pytest.raises(InternalError) as excinfo:
        client.pipeline.run(
            wp="WP-001",
            branch="feat/wp-001-x",
            dev_sha_at_creation="abc123de",
            deploy_workflow="Deploy to Dev",
        )

    err = excinfo.value
    assert err.category == "internal"
    assert "RuntimeError: boom" in err.message
    assert err.transport_code == 2


# ─── ProtocolError on missing binary ──────────────────────────────────


def test_pipeline_run_protocol_error_when_binary_missing(
    fake_wpx_dir, tmp_repo_root
):
    """Empty wpx_dir → BinaryNotFoundError (subclass of ProtocolError)."""
    # Deliberately do not create the fake binary
    client = SulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )

    with pytest.raises(BinaryNotFoundError) as excinfo:
        client.pipeline.run(
            wp="WP-001",
            branch="feat/wp-001-x",
            dev_sha_at_creation="abc123de",
            deploy_workflow="Deploy to Dev",
        )

    err = excinfo.value
    assert err.category == "protocol"
    assert "wpx-pipeline" in err.message


# ─── Async client mirrors sync behaviour ──────────────────────────────


async def test_async_pipeline_run_success(
    make_fake_binary, fake_wpx_dir, tmp_repo_root
):
    make_fake_binary(
        "wpx-pipeline", stdout_payload=_success_envelope(), exit_code=0
    )

    client = AsyncSulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )
    result = await client.pipeline.run(
        wp="WP-001",
        branch="feat/wp-001-x",
        dev_sha_at_creation="abc123de",
        deploy_workflow="Deploy to Dev",
    )

    assert isinstance(result, PipelineResult)
    assert result.outcome == "success"


# ─── Argv construction (regression on the transport layer) ────────────


def test_pipeline_run_passes_all_args_to_cli(
    fake_wpx_dir, tmp_repo_root, tmp_path
):
    """Verify the transport builds the right argv when optional args are passed.

    We use a fake binary that writes its argv to a file (since stderr is
    captured by subprocess.run and not visible to pytest's capfd), then
    we assert the file's contents.
    """
    argv_dump = tmp_path / "argv.txt"
    binary = fake_wpx_dir / "wpx-pipeline"
    import stat as _stat
    import sys
    binary.write_text(
        f"#!{sys.executable}\n"
        "import sys, json\n"
        f"open({str(argv_dump)!r}, 'w').write(' '.join(sys.argv))\n"
        "sys.stdout.write(json.dumps({\n"
        "    'ok': True,\n"
        "    'data': {'result': {\n"
        "        'wp': 'WP-001',\n"
        "        'outcome': 'success',\n"
        "        'started_at': '2026-05-21T12:00:00Z',\n"
        "        'completed_at': '2026-05-21T12:30:00Z',\n"
        "    }}\n"
        "}))\n"
        "sys.exit(0)\n"
    )
    binary.chmod(
        binary.stat().st_mode | _stat.S_IEXEC | _stat.S_IXGRP | _stat.S_IXOTH
    )

    client = SulisExecution(
        repo_root=tmp_repo_root, project="test-project", wpx_dir=fake_wpx_dir
    )
    client.pipeline.run(
        wp="WP-001",
        branch="feat/wp-001-x",
        dev_sha_at_creation="abc123def",
        deploy_workflow="Deploy to Dev",
        staging_url="https://staging.example.com",
        smoke_cmd="curl -sf https://staging.example.com/health",
        skip_ci_poll=True,
        base_branch="change/create-introduce-payments",
    )

    argv_line = argv_dump.read_text()
    # snake_case → kebab-case
    assert "--wp" in argv_line and "WP-001" in argv_line
    assert "--branch" in argv_line and "feat/wp-001-x" in argv_line
    assert "--dev-sha-at-creation" in argv_line
    assert "--deploy-workflow" in argv_line
    assert "--staging-url" in argv_line
    assert "--smoke-cmd" in argv_line
    assert "--skip-ci-poll" in argv_line
    assert "--base-branch" in argv_line
    assert "change/create-introduce-payments" in argv_line
    # 'subcommand' is just the second arg after the binary
    assert " run " in argv_line or argv_line.endswith(" run")
