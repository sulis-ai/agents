"""Client classes for the sulis-execution SDK.

Per agent-consumable SDK spec v0.2.0 Part 5: ship BOTH a sync
(`SulisExecution`) and an async (`AsyncSulisExecution`) client from the
same module.

The resource tree is built lazily — each resource is a cached property
that wraps a shared transport. Each resource module (pipeline.py in
Phase 0; train.py, index.py, ... in Phase 2) contains the actual method
implementations.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Optional

from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.resources.pipeline import (
    AsyncPipelineResource,
    PipelineResource,
)


class SulisExecution:
    """Sync client.

    Usage:

        from sulis_execution import SulisExecution

        client = SulisExecution(repo_root='.', project='my-project')
        result = client.pipeline.run(
            wp='WP-001',
            branch='feat/wp-001-x',
            dev_sha_at_creation='abc123',
            deploy_workflow='Deploy to Dev',
        )
    """

    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        project: str,
        timeout_seconds: float = 5400.0,
        wpx_dir: Optional[str | Path] = None,
    ) -> None:
        self._config = TransportConfig(
            repo_root=Path(repo_root).resolve(),
            project=project,
            timeout_seconds=timeout_seconds,
            wpx_dir=Path(wpx_dir).resolve() if wpx_dir else None,
        )
        self._transport = SubprocessTransport(self._config)

    @cached_property
    def pipeline(self) -> PipelineResource:
        return PipelineResource(self._transport, self._config)


class AsyncSulisExecution:
    """Async client.

    Same shape as SulisExecution; methods return awaitables.

    Usage:

        from sulis_execution import AsyncSulisExecution

        client = AsyncSulisExecution(repo_root='.', project='my-project')
        result = await client.pipeline.run(
            wp='WP-001',
            branch='feat/wp-001-x',
            dev_sha_at_creation='abc123',
            deploy_workflow='Deploy to Dev',
        )
    """

    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        project: str,
        timeout_seconds: float = 5400.0,
        wpx_dir: Optional[str | Path] = None,
    ) -> None:
        self._config = TransportConfig(
            repo_root=Path(repo_root).resolve(),
            project=project,
            timeout_seconds=timeout_seconds,
            wpx_dir=Path(wpx_dir).resolve() if wpx_dir else None,
        )
        self._transport = AsyncSubprocessTransport(self._config)

    @cached_property
    def pipeline(self) -> AsyncPipelineResource:
        return AsyncPipelineResource(self._transport, self._config)
