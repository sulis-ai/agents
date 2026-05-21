"""WP resource — wraps `wpx-wp` subcommands."""
from __future__ import annotations

from sulis_execution._helpers import _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import WpAppendEvidenceResult, WpReadFrontmatterResult

BINARY = "wpx-wp"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class WpResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def read_frontmatter(self, *, wp: str, field: str) -> WpReadFrontmatterResult:
        params = {**_common(self._config), "wp": wp, "field": field}
        envelope = self._transport.invoke(BINARY, "read-frontmatter", params)
        return WpReadFrontmatterResult.model_validate(_result_payload(envelope))

    def append_evidence(
        self, *, wp: str, evidence_json: str
    ) -> WpAppendEvidenceResult:
        params = {**_common(self._config), "wp": wp, "evidence_json": evidence_json}
        envelope = self._transport.invoke(BINARY, "append-evidence", params)
        return WpAppendEvidenceResult.model_validate(_result_payload(envelope))


class AsyncWpResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def read_frontmatter(
        self, *, wp: str, field: str
    ) -> WpReadFrontmatterResult:
        params = {**_common(self._config), "wp": wp, "field": field}
        envelope = await self._transport.invoke(BINARY, "read-frontmatter", params)
        return WpReadFrontmatterResult.model_validate(_result_payload(envelope))

    async def append_evidence(
        self, *, wp: str, evidence_json: str
    ) -> WpAppendEvidenceResult:
        params = {**_common(self._config), "wp": wp, "evidence_json": evidence_json}
        envelope = await self._transport.invoke(BINARY, "append-evidence", params)
        return WpAppendEvidenceResult.model_validate(_result_payload(envelope))
