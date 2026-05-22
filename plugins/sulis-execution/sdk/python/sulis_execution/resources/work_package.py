"""Work Package resource — wraps `wpx-wp` subcommands.

Read metadata from a Work Package file; append acceptance evidence to it.

Underlying CLI: `wpx-wp`. The SDK wraps that under cleaner names —
`read_metadata` instead of the CLI's `read-frontmatter` (which leaks
markdown-author jargon).
"""
from __future__ import annotations

from sulis_execution._helpers import _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import (
    WorkPackageAppendEvidenceResult,
    WorkPackageReadMetadataResult,
)

BINARY = "wpx-wp"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class WorkPackageResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def read_metadata(
        self, *, wp: str, field: str
    ) -> WorkPackageReadMetadataResult:
        """Read frontmatter metadata from a WP file.

        Returns one field's value, or the whole frontmatter dict if
        field is "*". Underlying CLI subcommand: `read-frontmatter`.
        """
        params = {**_common(self._config), "wp": wp, "field": field}
        envelope = self._transport.invoke(BINARY, "read-frontmatter", params)
        return WorkPackageReadMetadataResult.model_validate(_result_payload(envelope))

    def append_evidence(
        self, *, wp: str, evidence_json: str
    ) -> WorkPackageAppendEvidenceResult:
        """Append the `## Acceptance Evidence` section to a WP file."""
        params = {**_common(self._config), "wp": wp, "evidence_json": evidence_json}
        envelope = self._transport.invoke(BINARY, "append-evidence", params)
        return WorkPackageAppendEvidenceResult.model_validate(_result_payload(envelope))


class AsyncWorkPackageResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def read_metadata(
        self, *, wp: str, field: str
    ) -> WorkPackageReadMetadataResult:
        params = {**_common(self._config), "wp": wp, "field": field}
        envelope = await self._transport.invoke(BINARY, "read-frontmatter", params)
        return WorkPackageReadMetadataResult.model_validate(_result_payload(envelope))

    async def append_evidence(
        self, *, wp: str, evidence_json: str
    ) -> WorkPackageAppendEvidenceResult:
        params = {**_common(self._config), "wp": wp, "evidence_json": evidence_json}
        envelope = await self._transport.invoke(BINARY, "append-evidence", params)
        return WorkPackageAppendEvidenceResult.model_validate(_result_payload(envelope))
