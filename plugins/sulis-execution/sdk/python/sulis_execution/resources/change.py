"""Change resource — wraps `sulis-change` subcommands.

Note: sulis-change is project-independent (the change branch convention
is repo-wide, not project-scoped). Methods here pass only --repo-root,
not --project.
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
    ChangeAdoptResult,
    ChangeFinishResult,
    ChangeListResult,
    ChangeStartResult,
    ChangeStatusResult,
)

BINARY = "sulis-change"


def _common(config: TransportConfig) -> dict:
    return {"repo_root": str(config.repo_root)}


class ChangeResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def start(
        self, *, slug: str, primitive: str = "feat", base: str = "dev"
    ) -> ChangeStartResult:
        params = {
            **_common(self._config), "slug": slug, "primitive": primitive, "base": base,
        }
        envelope = self._transport.invoke(BINARY, "start", params)
        return ChangeStartResult.model_validate(_result_payload(envelope))

    def adopt(
        self,
        *,
        slug: str,
        primitive: str = "feat",
        base: str = "dev",
        mode: str = "forward",
        remote_ref: str = "origin/dev",
        force: bool = False,
    ) -> ChangeAdoptResult:
        params = {
            **_common(self._config),
            "slug": slug, "primitive": primitive, "base": base,
            "mode": mode, "remote_ref": remote_ref, "force": force,
        }
        envelope = self._transport.invoke(BINARY, "adopt", params)
        return ChangeAdoptResult.model_validate(_result_payload(envelope))

    def finish(
        self,
        *,
        slug: str,
        primitive: str = "feat",
        base: str = "dev",
        merge: bool = False,
        pr: bool = False,
        no_cleanup: bool = False,
    ) -> ChangeFinishResult:
        params = {
            **_common(self._config),
            "slug": slug, "primitive": primitive, "base": base,
            "merge": merge, "pr": pr, "no_cleanup": no_cleanup,
        }
        envelope = self._transport.invoke(BINARY, "finish", params)
        return ChangeFinishResult.model_validate(_result_payload(envelope))

    def list(self, *, base: str = "dev") -> ChangeListResult:
        params = {**_common(self._config), "base": base}
        envelope = self._transport.invoke(BINARY, "list", params)
        return ChangeListResult.model_validate(_result_payload(envelope))

    def status(
        self, *, slug: str, primitive: str = "feat", base: str = "dev"
    ) -> ChangeStatusResult:
        params = {
            **_common(self._config),
            "slug": slug, "primitive": primitive, "base": base,
        }
        envelope = self._transport.invoke(BINARY, "status", params)
        return ChangeStatusResult.model_validate(_result_payload(envelope))


class AsyncChangeResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def start(
        self, *, slug: str, primitive: str = "feat", base: str = "dev"
    ) -> ChangeStartResult:
        params = {
            **_common(self._config), "slug": slug, "primitive": primitive, "base": base,
        }
        envelope = await self._transport.invoke(BINARY, "start", params)
        return ChangeStartResult.model_validate(_result_payload(envelope))

    async def adopt(
        self,
        *,
        slug: str,
        primitive: str = "feat",
        base: str = "dev",
        mode: str = "forward",
        remote_ref: str = "origin/dev",
        force: bool = False,
    ) -> ChangeAdoptResult:
        params = {
            **_common(self._config),
            "slug": slug, "primitive": primitive, "base": base,
            "mode": mode, "remote_ref": remote_ref, "force": force,
        }
        envelope = await self._transport.invoke(BINARY, "adopt", params)
        return ChangeAdoptResult.model_validate(_result_payload(envelope))

    async def finish(
        self,
        *,
        slug: str,
        primitive: str = "feat",
        base: str = "dev",
        merge: bool = False,
        pr: bool = False,
        no_cleanup: bool = False,
    ) -> ChangeFinishResult:
        params = {
            **_common(self._config),
            "slug": slug, "primitive": primitive, "base": base,
            "merge": merge, "pr": pr, "no_cleanup": no_cleanup,
        }
        envelope = await self._transport.invoke(BINARY, "finish", params)
        return ChangeFinishResult.model_validate(_result_payload(envelope))

    async def list(self, *, base: str = "dev") -> ChangeListResult:
        params = {**_common(self._config), "base": base}
        envelope = await self._transport.invoke(BINARY, "list", params)
        return ChangeListResult.model_validate(_result_payload(envelope))

    async def status(
        self, *, slug: str, primitive: str = "feat", base: str = "dev"
    ) -> ChangeStatusResult:
        params = {
            **_common(self._config),
            "slug": slug, "primitive": primitive, "base": base,
        }
        envelope = await self._transport.invoke(BINARY, "status", params)
        return ChangeStatusResult.model_validate(_result_payload(envelope))
