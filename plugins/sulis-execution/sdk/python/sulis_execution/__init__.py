"""sulis-execution — typed Python SDK for the sulis-execution plugin's CLI tools.

Per the agent-consumable SDK spec at
plugins/sulis-execution/docs/research/agent-consumable-sdk-spec.md (v0.2.0).

Transport: subprocess (v0.2.0 Part 4.3) — the SDK spawns the underlying
CLI binaries (wpx-pipeline, wpx-train, …) and reads structured JSON from
stdout, mapping exit codes 0/1/2 to outcome categories per v0.2.0 Part 3.

For LLM-direct invocation, see the sibling sulis-execution-mcp package.

Usage:

    from sulis_execution import SulisExecution

    client = SulisExecution(repo_root='.', project='my-project')
    result = client.pipeline.run(
        wp='WP-001',
        branch='feat/wp-001-introduce-payments',
        dev_sha_at_creation='abc123def',
        deploy_workflow='Deploy to Dev',
    )
    if result.outcome == 'blocker':
        print(f'Blocker: {result.blocker_reason}')
"""
from __future__ import annotations

from sulis_execution._client import SulisExecution, AsyncSulisExecution
from sulis_execution.errors import (
    SulisExecutionError,
    ProtocolError,
    ExpectedError,
    InternalError,
    # Domain extensions
    BinaryNotFoundError,
    InvalidArgumentError,
    UnexpectedOutputError,
)
from sulis_execution.types import PipelineResult

__version__ = "0.1.0"

__all__ = [
    "SulisExecution",
    "AsyncSulisExecution",
    "SulisExecutionError",
    "ProtocolError",
    "ExpectedError",
    "InternalError",
    "BinaryNotFoundError",
    "InvalidArgumentError",
    "UnexpectedOutputError",
    "PipelineResult",
    "__version__",
]
