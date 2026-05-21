"""Blocker resource — wraps `wpx-blocker` subcommands."""
from __future__ import annotations

from typing import Optional

from sulis_execution._helpers import _kwargs_to_params, _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import BlockerArchiveResult, BlockerWriteResult

BINARY = "wpx-blocker"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


def _write_params(
    config: TransportConfig,
    *,
    wp: str,
    title: str,
    step: str,
    trigger: str,
    observation: str,
    root_cause: str,
    scope: str,
    plain_english: str,
    suggested_next: str,
    five_whys_json: Optional[str] = None,
    scope_reason: Optional[str] = None,
    attempts_json: Optional[str] = None,
    force: bool = False,
) -> dict:
    return _kwargs_to_params({
        **_common(config),
        "wp": wp, "title": title, "step": step, "trigger": trigger,
        "observation": observation, "root_cause": root_cause, "scope": scope,
        "plain_english": plain_english, "suggested_next": suggested_next,
        "five_whys_json": five_whys_json, "scope_reason": scope_reason,
        "attempts_json": attempts_json, "force": force,
    })


class BlockerResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def write(self, **kwargs) -> BlockerWriteResult:
        params = _write_params(self._config, **kwargs)
        envelope = self._transport.invoke(BINARY, "write", params)
        return BlockerWriteResult.model_validate(_result_payload(envelope))

    def archive(self, *, wp: str) -> BlockerArchiveResult:
        params = {**_common(self._config), "wp": wp}
        envelope = self._transport.invoke(BINARY, "archive", params)
        return BlockerArchiveResult.model_validate(_result_payload(envelope))


class AsyncBlockerResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def write(self, **kwargs) -> BlockerWriteResult:
        params = _write_params(self._config, **kwargs)
        envelope = await self._transport.invoke(BINARY, "write", params)
        return BlockerWriteResult.model_validate(_result_payload(envelope))

    async def archive(self, *, wp: str) -> BlockerArchiveResult:
        params = {**_common(self._config), "wp": wp}
        envelope = await self._transport.invoke(BINARY, "archive", params)
        return BlockerArchiveResult.model_validate(_result_payload(envelope))
