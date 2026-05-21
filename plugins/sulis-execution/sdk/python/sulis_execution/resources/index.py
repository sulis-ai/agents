"""Index resource — wraps `wpx-index` subcommands.

Operations: flip_status, set_status, list_ready, read_config,
propagate_blocked, add_wp, sync_auto_drafts.
"""
from __future__ import annotations

from typing import Optional

from sulis_execution._helpers import _kwargs_to_params, _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import (
    IndexAddWpResult,
    IndexFlipStatusResult,
    IndexListReadyResult,
    IndexPropagateBlockedResult,
    IndexReadConfigResult,
    IndexSyncAutoDraftsResult,
)

BINARY = "wpx-index"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class IndexResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def flip_status(
        self, *, wp: str, to: str, expected: Optional[str] = None
    ) -> IndexFlipStatusResult:
        params = _kwargs_to_params({
            **_common(self._config), "wp": wp, "to": to, "expected": expected,
        })
        envelope = self._transport.invoke(BINARY, "flip-status", params)
        return IndexFlipStatusResult.model_validate(_result_payload(envelope))

    def set_status(self, *, wp: str, to: str) -> IndexFlipStatusResult:
        params = {**_common(self._config), "wp": wp, "to": to}
        envelope = self._transport.invoke(BINARY, "set-status", params)
        return IndexFlipStatusResult.model_validate(_result_payload(envelope))

    def list_ready(self) -> IndexListReadyResult:
        envelope = self._transport.invoke(BINARY, "list-ready", _common(self._config))
        return IndexListReadyResult.model_validate(_result_payload(envelope))

    def read_config(self) -> IndexReadConfigResult:
        envelope = self._transport.invoke(BINARY, "read-config", _common(self._config))
        return IndexReadConfigResult.model_validate(_result_payload(envelope))

    def propagate_blocked(self, *, wp: str) -> IndexPropagateBlockedResult:
        params = {**_common(self._config), "wp": wp}
        envelope = self._transport.invoke(BINARY, "propagate-blocked", params)
        return IndexPropagateBlockedResult.model_validate(_result_payload(envelope))

    def add_wp(
        self,
        *,
        wp: str,
        from_wp_file: bool = False,
        title: Optional[str] = None,
        primitive: Optional[str] = None,
        status: str = "pending",
        depends_on: str = "",
        blocks: str = "",
        token_estimate: str = "?",
        tdd: Optional[str] = None,
    ) -> IndexAddWpResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp,
            "from_wp_file": from_wp_file,
            "title": title,
            "primitive": primitive,
            "status": status,
            "depends_on": depends_on,
            "blocks": blocks,
            "token_estimate": token_estimate,
            "tdd": tdd,
        })
        envelope = self._transport.invoke(BINARY, "add-wp", params)
        return IndexAddWpResult.model_validate(_result_payload(envelope))

    def sync_auto_drafts(self) -> IndexSyncAutoDraftsResult:
        envelope = self._transport.invoke(
            BINARY, "sync-auto-drafts", _common(self._config)
        )
        return IndexSyncAutoDraftsResult.model_validate(_result_payload(envelope))


class AsyncIndexResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def flip_status(
        self, *, wp: str, to: str, expected: Optional[str] = None
    ) -> IndexFlipStatusResult:
        params = _kwargs_to_params({
            **_common(self._config), "wp": wp, "to": to, "expected": expected,
        })
        envelope = await self._transport.invoke(BINARY, "flip-status", params)
        return IndexFlipStatusResult.model_validate(_result_payload(envelope))

    async def set_status(self, *, wp: str, to: str) -> IndexFlipStatusResult:
        params = {**_common(self._config), "wp": wp, "to": to}
        envelope = await self._transport.invoke(BINARY, "set-status", params)
        return IndexFlipStatusResult.model_validate(_result_payload(envelope))

    async def list_ready(self) -> IndexListReadyResult:
        envelope = await self._transport.invoke(
            BINARY, "list-ready", _common(self._config)
        )
        return IndexListReadyResult.model_validate(_result_payload(envelope))

    async def read_config(self) -> IndexReadConfigResult:
        envelope = await self._transport.invoke(
            BINARY, "read-config", _common(self._config)
        )
        return IndexReadConfigResult.model_validate(_result_payload(envelope))

    async def propagate_blocked(self, *, wp: str) -> IndexPropagateBlockedResult:
        params = {**_common(self._config), "wp": wp}
        envelope = await self._transport.invoke(BINARY, "propagate-blocked", params)
        return IndexPropagateBlockedResult.model_validate(_result_payload(envelope))

    async def add_wp(
        self,
        *,
        wp: str,
        from_wp_file: bool = False,
        title: Optional[str] = None,
        primitive: Optional[str] = None,
        status: str = "pending",
        depends_on: str = "",
        blocks: str = "",
        token_estimate: str = "?",
        tdd: Optional[str] = None,
    ) -> IndexAddWpResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp,
            "from_wp_file": from_wp_file,
            "title": title,
            "primitive": primitive,
            "status": status,
            "depends_on": depends_on,
            "blocks": blocks,
            "token_estimate": token_estimate,
            "tdd": tdd,
        })
        envelope = await self._transport.invoke(BINARY, "add-wp", params)
        return IndexAddWpResult.model_validate(_result_payload(envelope))

    async def sync_auto_drafts(self) -> IndexSyncAutoDraftsResult:
        envelope = await self._transport.invoke(
            BINARY, "sync-auto-drafts", _common(self._config)
        )
        return IndexSyncAutoDraftsResult.model_validate(_result_payload(envelope))
