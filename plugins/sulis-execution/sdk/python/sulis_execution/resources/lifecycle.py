"""Lifecycle resource — atomically complete a Work Package's lifecycle.

After the pipeline succeeds, `complete()` atomically finalises a WP:
appends evidence to the WP file, flips INDEX status to `done`, removes
the worktree. All three or none — fail-fast.

Underlying CLI: `wpx-step12 wrap`. The SDK wraps that under cleaner names.
"""
from __future__ import annotations

from typing import Optional

from sulis_execution._helpers import _kwargs_to_params, _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import LifecycleCompleteResult

BINARY = "wpx-step12"
SUBCOMMAND = "wrap"  # underlying CLI subcommand; SDK method is `complete`


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class LifecycleResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def complete(
        self,
        *,
        wp: str,
        branch: str,
        pipeline_result: str,
        pre_squash_sha: Optional[str] = None,
        worktree_path: Optional[str] = None,
        post_deploy_verification: Optional[str] = None,
    ) -> LifecycleCompleteResult:
        """Atomically complete a Work Package's lifecycle.

        Chains three operations fail-fast:
        1. work_package.append_evidence
        2. index.flip_status (expected: in_progress → done)
        3. worktree.remove

        If any fails, returns details of what succeeded vs failed.
        """
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "branch": branch, "pipeline_result": pipeline_result,
            "pre_squash_sha": pre_squash_sha, "worktree_path": worktree_path,
            "post_deploy_verification": post_deploy_verification,
        })
        envelope = self._transport.invoke(BINARY, SUBCOMMAND, params)
        return LifecycleCompleteResult.model_validate(_result_payload(envelope))


class AsyncLifecycleResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def complete(
        self,
        *,
        wp: str,
        branch: str,
        pipeline_result: str,
        pre_squash_sha: Optional[str] = None,
        worktree_path: Optional[str] = None,
        post_deploy_verification: Optional[str] = None,
    ) -> LifecycleCompleteResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "branch": branch, "pipeline_result": pipeline_result,
            "pre_squash_sha": pre_squash_sha, "worktree_path": worktree_path,
            "post_deploy_verification": post_deploy_verification,
        })
        envelope = await self._transport.invoke(BINARY, SUBCOMMAND, params)
        return LifecycleCompleteResult.model_validate(_result_payload(envelope))
