"""Client classes for the sulis-execution SDK.

Per agent-consumable SDK spec v0.2.0 Part 5: ship BOTH a sync
(`SulisExecution`) and an async (`AsyncSulisExecution`) client from
the same module.

The resource tree is built lazily — each resource is a cached property
that wraps a shared transport. Each resource module contains the actual
method implementations.

Resources (10): pipeline, train, index, journal, blocker, findings,
                work_package, worktree, lifecycle, change.
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
from sulis_execution.resources.blocker import AsyncBlockerResource, BlockerResource
from sulis_execution.resources.change import AsyncChangeResource, ChangeResource
from sulis_execution.resources.findings import (
    AsyncFindingsResource,
    FindingsResource,
)
from sulis_execution.resources.index import AsyncIndexResource, IndexResource
from sulis_execution.resources.journal import AsyncJournalResource, JournalResource
from sulis_execution.resources.pipeline import (
    AsyncPipelineResource,
    PipelineResource,
)
from sulis_execution.resources.lifecycle import (
    AsyncLifecycleResource,
    LifecycleResource,
)
from sulis_execution.resources.train import AsyncTrainResource, TrainResource
from sulis_execution.resources.worktree import (
    AsyncWorktreeResource,
    WorktreeResource,
)
from sulis_execution.resources.work_package import (
    AsyncWorkPackageResource,
    WorkPackageResource,
)


class SulisExecution:
    """Sync client for the sulis-execution CLI surface.

    Usage:

        from sulis_execution import SulisExecution

        client = SulisExecution(repo_root='.', project='my-project')

        # Pipeline (one operation: run)
        result = client.pipeline.run(wp='WP-001', branch='feat/wp-001-x', ...)

        # Train (6 operations)
        eligibility = client.train.queue_list()
        client.train.queue_add(wp='WP-001')

        # Index (7 operations)
        client.index.flip_status(wp='WP-001', to='done', expected='in_progress')

        # Journal (10 operations)
        client.journal.init(wp='WP-001')

        # Blocker, Findings, WP, Worktree, Step12 — see resource modules.

        # Change (5 operations — project-independent)
        client.change.start(slug='introduce-payments', primitive='create')
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

    @cached_property
    def train(self) -> TrainResource:
        return TrainResource(self._transport, self._config)

    @cached_property
    def index(self) -> IndexResource:
        return IndexResource(self._transport, self._config)

    @cached_property
    def journal(self) -> JournalResource:
        return JournalResource(self._transport, self._config)

    @cached_property
    def blocker(self) -> BlockerResource:
        return BlockerResource(self._transport, self._config)

    @cached_property
    def findings(self) -> FindingsResource:
        return FindingsResource(self._transport, self._config)

    @cached_property
    def work_package(self) -> WorkPackageResource:
        return WorkPackageResource(self._transport, self._config)

    @cached_property
    def worktree(self) -> WorktreeResource:
        return WorktreeResource(self._transport, self._config)

    @cached_property
    def lifecycle(self) -> LifecycleResource:
        return LifecycleResource(self._transport, self._config)

    @cached_property
    def change(self) -> ChangeResource:
        return ChangeResource(self._transport, self._config)


class AsyncSulisExecution:
    """Async client. Same resource tree; methods return awaitables."""

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

    @cached_property
    def train(self) -> AsyncTrainResource:
        return AsyncTrainResource(self._transport, self._config)

    @cached_property
    def index(self) -> AsyncIndexResource:
        return AsyncIndexResource(self._transport, self._config)

    @cached_property
    def journal(self) -> AsyncJournalResource:
        return AsyncJournalResource(self._transport, self._config)

    @cached_property
    def blocker(self) -> AsyncBlockerResource:
        return AsyncBlockerResource(self._transport, self._config)

    @cached_property
    def findings(self) -> AsyncFindingsResource:
        return AsyncFindingsResource(self._transport, self._config)

    @cached_property
    def work_package(self) -> AsyncWorkPackageResource:
        return AsyncWorkPackageResource(self._transport, self._config)

    @cached_property
    def worktree(self) -> AsyncWorktreeResource:
        return AsyncWorktreeResource(self._transport, self._config)

    @cached_property
    def lifecycle(self) -> AsyncLifecycleResource:
        return AsyncLifecycleResource(self._transport, self._config)

    @cached_property
    def change(self) -> AsyncChangeResource:
        return AsyncChangeResource(self._transport, self._config)
