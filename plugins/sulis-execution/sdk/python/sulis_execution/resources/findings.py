"""Findings resource — wraps `wpx-findings` subcommands."""
from __future__ import annotations

from typing import Optional

from sulis_execution._helpers import _kwargs_to_params, _result_payload
from sulis_execution.transport import (
    AsyncSubprocessTransport,
    SubprocessTransport,
    TransportConfig,
)
from sulis_execution.types import FindingsAutoDraftWpResult, FindingsRegisterResult

BINARY = "wpx-findings"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class FindingsResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def register(
        self,
        *,
        wp: str,
        severity: str,
        summary: str,
        file: str,
        evidence_json: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        primitive: Optional[str] = None,
    ) -> FindingsRegisterResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "severity": severity, "summary": summary, "file": file,
            "evidence_json": evidence_json, "suggested_fix": suggested_fix,
            "primitive": primitive,
        })
        envelope = self._transport.invoke(BINARY, "register", params)
        return FindingsRegisterResult.model_validate(_result_payload(envelope))

    def auto_draft_wp(
        self,
        *,
        source_finding: str,
        source_wp: str,
        auto_wp_id: str,
        severity: str,
        primitive: str = "Secure",
    ) -> FindingsAutoDraftWpResult:
        params = {
            **_common(self._config),
            "source_finding": source_finding, "source_wp": source_wp,
            "auto_wp_id": auto_wp_id, "severity": severity, "primitive": primitive,
        }
        envelope = self._transport.invoke(BINARY, "auto-draft-wp", params)
        return FindingsAutoDraftWpResult.model_validate(_result_payload(envelope))


class AsyncFindingsResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def register(
        self,
        *,
        wp: str,
        severity: str,
        summary: str,
        file: str,
        evidence_json: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        primitive: Optional[str] = None,
    ) -> FindingsRegisterResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "severity": severity, "summary": summary, "file": file,
            "evidence_json": evidence_json, "suggested_fix": suggested_fix,
            "primitive": primitive,
        })
        envelope = await self._transport.invoke(BINARY, "register", params)
        return FindingsRegisterResult.model_validate(_result_payload(envelope))

    async def auto_draft_wp(
        self,
        *,
        source_finding: str,
        source_wp: str,
        auto_wp_id: str,
        severity: str,
        primitive: str = "Secure",
    ) -> FindingsAutoDraftWpResult:
        params = {
            **_common(self._config),
            "source_finding": source_finding, "source_wp": source_wp,
            "auto_wp_id": auto_wp_id, "severity": severity, "primitive": primitive,
        }
        envelope = await self._transport.invoke(BINARY, "auto-draft-wp", params)
        return FindingsAutoDraftWpResult.model_validate(_result_payload(envelope))
