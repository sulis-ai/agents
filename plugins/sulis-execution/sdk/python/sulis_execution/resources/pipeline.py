"""Pipeline resource — wraps `wpx-pipeline run`.

Per the OpenAPI schema, this resource has one operation: `run`.
"""
from __future__ import annotations

from typing import Optional

from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import PipelineResult


def _build_pipeline_params(
    *,
    wp: str,
    branch: str,
    project: str,
    dev_sha_at_creation: str,
    deploy_workflow: str,
    repo_root: Optional[str] = None,
    repo: Optional[str] = None,
    worktree_path: Optional[str] = None,
    staging_url: Optional[str] = None,
    health_path: Optional[str] = None,
    smoke_cmd: Optional[str] = None,
    ci_poll_interval: Optional[int] = None,
    deploy_poll_interval: Optional[int] = None,
    skip_ci_poll: bool = False,
    base_branch: Optional[str] = None,
) -> dict:
    """Build the kwargs dict the transport converts to argv."""
    params = {
        "wp": wp,
        "branch": branch,
        "project": project,
        "dev_sha_at_creation": dev_sha_at_creation,
        "deploy_workflow": deploy_workflow,
        "repo_root": repo_root,
        "repo": repo,
        "worktree_path": worktree_path,
        "staging_url": staging_url,
        "health_path": health_path,
        "smoke_cmd": smoke_cmd,
        "ci_poll_interval": ci_poll_interval,
        "deploy_poll_interval": deploy_poll_interval,
        "skip_ci_poll": skip_ci_poll,
        "base_branch": base_branch,
    }
    return params


def _extract_result(envelope: dict) -> PipelineResult:
    """Pull the result record out of the wpx-pipeline JSON envelope.

    wpx-pipeline emits `emit_result(record, exit_code)` which wraps the
    record as `{"ok": <bool>, "data": {"result": {...}}}`. The SDK
    surface returns just the `result` dict as a typed Pydantic model.
    """
    data = envelope.get("data") or {}
    result_dict = data.get("result") or {}
    return PipelineResult.model_validate(result_dict)


class PipelineResource:
    """Sync pipeline operations."""

    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def run(
        self,
        *,
        wp: str,
        branch: str,
        dev_sha_at_creation: str,
        deploy_workflow: str,
        repo: Optional[str] = None,
        worktree_path: Optional[str] = None,
        staging_url: Optional[str] = None,
        health_path: Optional[str] = None,
        smoke_cmd: Optional[str] = None,
        ci_poll_interval: Optional[int] = None,
        deploy_poll_interval: Optional[int] = None,
        skip_ci_poll: bool = False,
        base_branch: Optional[str] = None,
    ) -> PipelineResult:
        """Run the per-WP Steps 8-10 pipeline.

        See OpenAPI spec at sulis-execution.openapi.yaml for full
        semantics. Returns a typed PipelineResult. The blocker case
        (CI red, deploy timed out, etc.) is returned as a result with
        outcome='blocker' — NOT raised as an exception.
        """
        params = _build_pipeline_params(
            wp=wp,
            branch=branch,
            project=self._config.project,
            dev_sha_at_creation=dev_sha_at_creation,
            deploy_workflow=deploy_workflow,
            repo_root=str(self._config.repo_root),
            repo=repo,
            worktree_path=worktree_path,
            staging_url=staging_url,
            health_path=health_path,
            smoke_cmd=smoke_cmd,
            ci_poll_interval=ci_poll_interval,
            deploy_poll_interval=deploy_poll_interval,
            skip_ci_poll=skip_ci_poll,
            base_branch=base_branch,
        )
        envelope = self._transport.invoke("wpx-pipeline", "run", params)
        return _extract_result(envelope)


class AsyncPipelineResource:
    """Async pipeline operations. Same shape; awaitable methods."""

    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def run(
        self,
        *,
        wp: str,
        branch: str,
        dev_sha_at_creation: str,
        deploy_workflow: str,
        repo: Optional[str] = None,
        worktree_path: Optional[str] = None,
        staging_url: Optional[str] = None,
        health_path: Optional[str] = None,
        smoke_cmd: Optional[str] = None,
        ci_poll_interval: Optional[int] = None,
        deploy_poll_interval: Optional[int] = None,
        skip_ci_poll: bool = False,
        base_branch: Optional[str] = None,
    ) -> PipelineResult:
        params = _build_pipeline_params(
            wp=wp,
            branch=branch,
            project=self._config.project,
            dev_sha_at_creation=dev_sha_at_creation,
            deploy_workflow=deploy_workflow,
            repo_root=str(self._config.repo_root),
            repo=repo,
            worktree_path=worktree_path,
            staging_url=staging_url,
            health_path=health_path,
            smoke_cmd=smoke_cmd,
            ci_poll_interval=ci_poll_interval,
            deploy_poll_interval=deploy_poll_interval,
            skip_ci_poll=skip_ci_poll,
            base_branch=base_branch,
        )
        envelope = await self._transport.invoke("wpx-pipeline", "run", params)
        return _extract_result(envelope)
