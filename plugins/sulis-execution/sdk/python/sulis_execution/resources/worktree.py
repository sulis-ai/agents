"""Worktree resource — wraps `wpx-worktree` subcommands."""
from __future__ import annotations

from sulis_execution._helpers import _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import WorktreeCreateResult, WorktreeRemoveResult

BINARY = "wpx-worktree"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class WorktreeResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def create(
        self, *, wp: str, branch: str, worktree_path: str
    ) -> WorktreeCreateResult:
        params = {
            **_common(self._config),
            "wp": wp, "branch": branch, "worktree_path": worktree_path,
        }
        envelope = self._transport.invoke(BINARY, "create", params)
        return WorktreeCreateResult.model_validate(_result_payload(envelope))

    def remove(
        self,
        *,
        wp: str,
        worktree_path: str,
        force: bool = False,
        tolerate_missing: bool = False,
    ) -> WorktreeRemoveResult:
        params = {
            **_common(self._config),
            "wp": wp, "worktree_path": worktree_path,
            "force": force, "tolerate_missing": tolerate_missing,
        }
        envelope = self._transport.invoke(BINARY, "remove", params)
        return WorktreeRemoveResult.model_validate(_result_payload(envelope))


class AsyncWorktreeResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def create(
        self, *, wp: str, branch: str, worktree_path: str
    ) -> WorktreeCreateResult:
        params = {
            **_common(self._config),
            "wp": wp, "branch": branch, "worktree_path": worktree_path,
        }
        envelope = await self._transport.invoke(BINARY, "create", params)
        return WorktreeCreateResult.model_validate(_result_payload(envelope))

    async def remove(
        self,
        *,
        wp: str,
        worktree_path: str,
        force: bool = False,
        tolerate_missing: bool = False,
    ) -> WorktreeRemoveResult:
        params = {
            **_common(self._config),
            "wp": wp, "worktree_path": worktree_path,
            "force": force, "tolerate_missing": tolerate_missing,
        }
        envelope = await self._transport.invoke(BINARY, "remove", params)
        return WorktreeRemoveResult.model_validate(_result_payload(envelope))
