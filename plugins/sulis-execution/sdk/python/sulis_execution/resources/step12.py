"""Step 12 resource — wraps `wpx-step12 wrap`."""
from __future__ import annotations

from typing import Optional

from sulis_execution._helpers import _kwargs_to_params, _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import Step12WrapResult

BINARY = "wpx-step12"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class Step12Resource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def wrap(
        self,
        *,
        wp: str,
        branch: str,
        pipeline_result: str,
        pre_squash_sha: Optional[str] = None,
        worktree_path: Optional[str] = None,
        post_deploy_verification: Optional[str] = None,
    ) -> Step12WrapResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "branch": branch, "pipeline_result": pipeline_result,
            "pre_squash_sha": pre_squash_sha, "worktree_path": worktree_path,
            "post_deploy_verification": post_deploy_verification,
        })
        envelope = self._transport.invoke(BINARY, "wrap", params)
        return Step12WrapResult.model_validate(_result_payload(envelope))


class AsyncStep12Resource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def wrap(
        self,
        *,
        wp: str,
        branch: str,
        pipeline_result: str,
        pre_squash_sha: Optional[str] = None,
        worktree_path: Optional[str] = None,
        post_deploy_verification: Optional[str] = None,
    ) -> Step12WrapResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "branch": branch, "pipeline_result": pipeline_result,
            "pre_squash_sha": pre_squash_sha, "worktree_path": worktree_path,
            "post_deploy_verification": post_deploy_verification,
        })
        envelope = await self._transport.invoke(BINARY, "wrap", params)
        return Step12WrapResult.model_validate(_result_payload(envelope))
