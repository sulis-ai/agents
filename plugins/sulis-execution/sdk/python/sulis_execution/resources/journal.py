"""Journal resource — wraps `wpx-journal` subcommands.

Operations: init, start_step, complete_step, record_attempt,
record_preflight, record_postdeploy, seed_plan, mark_plan_item,
add_plan_item, read.
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
    JournalAddPlanItemResult,
    JournalAttemptResult,
    JournalMarkPlanItemResult,
    JournalPathResult,
    JournalPostdeployResult,
    JournalPreflightResult,
    JournalReadResult,
    JournalSeedPlanResult,
    JournalStepResult,
)

BINARY = "wpx-journal"


def _common(config: TransportConfig) -> dict:
    return {"project": config.project, "repo_root": str(config.repo_root)}


class JournalResource:
    def __init__(
        self, transport: SubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    def init(self, *, wp: str, force: bool = False) -> JournalPathResult:
        params = _kwargs_to_params({**_common(self._config), "wp": wp, "force": force})
        envelope = self._transport.invoke(BINARY, "init", params)
        return JournalPathResult.model_validate(_result_payload(envelope))

    def start_step(self, *, wp: str, step: int) -> JournalStepResult:
        params = {**_common(self._config), "wp": wp, "step": step}
        envelope = self._transport.invoke(BINARY, "start-step", params)
        return JournalStepResult.model_validate(_result_payload(envelope))

    def complete_step(
        self, *, wp: str, step: int, outcome: str
    ) -> JournalStepResult:
        params = {**_common(self._config), "wp": wp, "step": step, "outcome": outcome}
        envelope = self._transport.invoke(BINARY, "complete-step", params)
        return JournalStepResult.model_validate(_result_payload(envelope))

    def record_attempt(
        self,
        *,
        wp: str,
        step: int,
        attempt: int,
        failure: str,
        root_cause: str,
        change: str,
        outcome: str,
    ) -> JournalAttemptResult:
        params = {
            **_common(self._config),
            "wp": wp, "step": step, "attempt": attempt, "failure": failure,
            "root_cause": root_cause, "change": change, "outcome": outcome,
        }
        envelope = self._transport.invoke(BINARY, "record-attempt", params)
        return JournalAttemptResult.model_validate(_result_payload(envelope))

    def record_preflight(
        self, *, wp: str, tool: str, status: str, fallback: Optional[str] = None
    ) -> JournalPreflightResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "tool": tool, "status": status, "fallback": fallback,
        })
        envelope = self._transport.invoke(BINARY, "record-preflight", params)
        return JournalPreflightResult.model_validate(_result_payload(envelope))

    def record_postdeploy(
        self, *, wp: str, verdict: str, findings_json: Optional[str] = None
    ) -> JournalPostdeployResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "verdict": verdict, "findings_json": findings_json,
        })
        envelope = self._transport.invoke(BINARY, "record-postdeploy", params)
        return JournalPostdeployResult.model_validate(_result_payload(envelope))

    def seed_plan(
        self, *, wp: str, approach: str, plan_json: str, force: bool = False
    ) -> JournalSeedPlanResult:
        params = {
            **_common(self._config),
            "wp": wp, "approach": approach, "plan_json": plan_json, "force": force,
        }
        envelope = self._transport.invoke(BINARY, "seed-plan", params)
        return JournalSeedPlanResult.model_validate(_result_payload(envelope))

    def mark_plan_item(
        self,
        *,
        wp: str,
        item: int,
        status: str,
        expected: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> JournalMarkPlanItemResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "item": item, "status": status, "expected": expected,
            "notes": notes,
        })
        envelope = self._transport.invoke(BINARY, "mark-plan-item", params)
        return JournalMarkPlanItemResult.model_validate(_result_payload(envelope))

    def add_plan_item(
        self, *, wp: str, description: str, step: str, notes: Optional[str] = None
    ) -> JournalAddPlanItemResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "description": description, "step": step, "notes": notes,
        })
        envelope = self._transport.invoke(BINARY, "add-plan-item", params)
        return JournalAddPlanItemResult.model_validate(_result_payload(envelope))

    def read(self, *, wp: str, field: str) -> JournalReadResult:
        params = {**_common(self._config), "wp": wp, "field": field}
        envelope = self._transport.invoke(BINARY, "read", params)
        return JournalReadResult.model_validate(_result_payload(envelope))


class AsyncJournalResource:
    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def init(self, *, wp: str, force: bool = False) -> JournalPathResult:
        params = _kwargs_to_params({**_common(self._config), "wp": wp, "force": force})
        envelope = await self._transport.invoke(BINARY, "init", params)
        return JournalPathResult.model_validate(_result_payload(envelope))

    async def start_step(self, *, wp: str, step: int) -> JournalStepResult:
        params = {**_common(self._config), "wp": wp, "step": step}
        envelope = await self._transport.invoke(BINARY, "start-step", params)
        return JournalStepResult.model_validate(_result_payload(envelope))

    async def complete_step(
        self, *, wp: str, step: int, outcome: str
    ) -> JournalStepResult:
        params = {**_common(self._config), "wp": wp, "step": step, "outcome": outcome}
        envelope = await self._transport.invoke(BINARY, "complete-step", params)
        return JournalStepResult.model_validate(_result_payload(envelope))

    async def record_attempt(
        self,
        *,
        wp: str,
        step: int,
        attempt: int,
        failure: str,
        root_cause: str,
        change: str,
        outcome: str,
    ) -> JournalAttemptResult:
        params = {
            **_common(self._config),
            "wp": wp, "step": step, "attempt": attempt, "failure": failure,
            "root_cause": root_cause, "change": change, "outcome": outcome,
        }
        envelope = await self._transport.invoke(BINARY, "record-attempt", params)
        return JournalAttemptResult.model_validate(_result_payload(envelope))

    async def record_preflight(
        self, *, wp: str, tool: str, status: str, fallback: Optional[str] = None
    ) -> JournalPreflightResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "tool": tool, "status": status, "fallback": fallback,
        })
        envelope = await self._transport.invoke(BINARY, "record-preflight", params)
        return JournalPreflightResult.model_validate(_result_payload(envelope))

    async def record_postdeploy(
        self, *, wp: str, verdict: str, findings_json: Optional[str] = None
    ) -> JournalPostdeployResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "verdict": verdict, "findings_json": findings_json,
        })
        envelope = await self._transport.invoke(BINARY, "record-postdeploy", params)
        return JournalPostdeployResult.model_validate(_result_payload(envelope))

    async def seed_plan(
        self, *, wp: str, approach: str, plan_json: str, force: bool = False
    ) -> JournalSeedPlanResult:
        params = {
            **_common(self._config),
            "wp": wp, "approach": approach, "plan_json": plan_json, "force": force,
        }
        envelope = await self._transport.invoke(BINARY, "seed-plan", params)
        return JournalSeedPlanResult.model_validate(_result_payload(envelope))

    async def mark_plan_item(
        self,
        *,
        wp: str,
        item: int,
        status: str,
        expected: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> JournalMarkPlanItemResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "item": item, "status": status, "expected": expected,
            "notes": notes,
        })
        envelope = await self._transport.invoke(BINARY, "mark-plan-item", params)
        return JournalMarkPlanItemResult.model_validate(_result_payload(envelope))

    async def add_plan_item(
        self, *, wp: str, description: str, step: str, notes: Optional[str] = None
    ) -> JournalAddPlanItemResult:
        params = _kwargs_to_params({
            **_common(self._config),
            "wp": wp, "description": description, "step": step, "notes": notes,
        })
        envelope = await self._transport.invoke(BINARY, "add-plan-item", params)
        return JournalAddPlanItemResult.model_validate(_result_payload(envelope))

    async def read(self, *, wp: str, field: str) -> JournalReadResult:
        params = {**_common(self._config), "wp": wp, "field": field}
        envelope = await self._transport.invoke(BINARY, "read", params)
        return JournalReadResult.model_validate(_result_payload(envelope))
