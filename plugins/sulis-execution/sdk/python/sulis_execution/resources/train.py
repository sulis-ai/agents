"""Train resource — wraps `wpx-train` subcommands.

Operations: queue_list, queue_add, queue_remove, status, doctor, run.
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
    TrainDoctorResult,
    TrainInspectResult,
    TrainOverrideResult,
    TrainQueueListResult,
    TrainRunResult,
    TrainStatusResult,
)

BINARY = "wpx-train"


def _train_common(config: TransportConfig, repo: Optional[str]) -> dict:
    return _kwargs_to_params({
        "project": config.project,
        "repo_root": str(config.repo_root),
        "repo": repo,
    })


class TrainResource:
    """Sync train operations."""

    def __init__(self, transport: SubprocessTransport, config: TransportConfig) -> None:
        self._transport = transport
        self._config = config

    def queue_list(self, *, repo: Optional[str] = None) -> TrainQueueListResult:
        envelope = self._transport.invoke(BINARY, "queue-list",
                                          _train_common(self._config, repo))
        return TrainQueueListResult.model_validate(_result_payload(envelope))

    def queue_add(
        self, *, wp: str, reason: str = "", repo: Optional[str] = None
    ) -> TrainOverrideResult:
        params = {**_train_common(self._config, repo), "wp": wp, "reason": reason}
        envelope = self._transport.invoke(BINARY, "queue-add", params)
        return TrainOverrideResult.model_validate(_result_payload(envelope))

    def queue_remove(
        self, *, wp: str, reason: str = "", repo: Optional[str] = None
    ) -> TrainOverrideResult:
        params = {**_train_common(self._config, repo), "wp": wp, "reason": reason}
        envelope = self._transport.invoke(BINARY, "queue-remove", params)
        return TrainOverrideResult.model_validate(_result_payload(envelope))

    def status(self, *, repo: Optional[str] = None) -> TrainStatusResult:
        envelope = self._transport.invoke(BINARY, "status",
                                          _train_common(self._config, repo))
        return TrainStatusResult.model_validate(_result_payload(envelope))

    def doctor(self, *, repo: Optional[str] = None) -> TrainDoctorResult:
        envelope = self._transport.invoke(BINARY, "doctor",
                                          _train_common(self._config, repo))
        return TrainDoctorResult.model_validate(_result_payload(envelope))

    def inspect(self, *, train_id: Optional[str] = None) -> "TrainInspectResult":
        """Inspect a train's in-flight or historical state.

        - With train_id: returns the train's state snapshot (phase,
          phase_history, per-WP outcomes, pause_reason + recovery_hint
          when present).
        - Without train_id: returns a listing of recent trains
          (most-recent first; mix of in-flight + terminal).
        """
        params = _train_common(self._config, None)
        if train_id is not None:
            params["train_id"] = train_id
        params["json"] = True  # SDK consumers always want machine-readable
        envelope = self._transport.invoke(BINARY, "inspect", params)
        return TrainInspectResult.model_validate(_result_payload(envelope))

    def run(
        self,
        *,
        deploy_workflow: str,
        force: bool = False,
        staging_url: Optional[str] = None,
        health_path: Optional[str] = None,
        smoke_cmd: Optional[str] = None,
        ci_poll_interval: Optional[int] = None,
        deploy_poll_interval: Optional[int] = None,
        max_batch_size: int = 5,
        base_branch: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> TrainRunResult:
        params = _kwargs_to_params({
            **_train_common(self._config, repo),
            "force": force,
            "deploy_workflow": deploy_workflow,
            "staging_url": staging_url,
            "health_path": health_path,
            "smoke_cmd": smoke_cmd,
            "ci_poll_interval": ci_poll_interval,
            "deploy_poll_interval": deploy_poll_interval,
            "max_batch_size": max_batch_size,
            "base_branch": base_branch,
        })
        envelope = self._transport.invoke(BINARY, "run", params)
        return TrainRunResult.model_validate(_result_payload(envelope))


class AsyncTrainResource:
    """Async train operations."""

    def __init__(
        self, transport: AsyncSubprocessTransport, config: TransportConfig
    ) -> None:
        self._transport = transport
        self._config = config

    async def queue_list(self, *, repo: Optional[str] = None) -> TrainQueueListResult:
        envelope = await self._transport.invoke(
            BINARY, "queue-list", _train_common(self._config, repo)
        )
        return TrainQueueListResult.model_validate(_result_payload(envelope))

    async def queue_add(
        self, *, wp: str, reason: str = "", repo: Optional[str] = None
    ) -> TrainOverrideResult:
        params = {**_train_common(self._config, repo), "wp": wp, "reason": reason}
        envelope = await self._transport.invoke(BINARY, "queue-add", params)
        return TrainOverrideResult.model_validate(_result_payload(envelope))

    async def queue_remove(
        self, *, wp: str, reason: str = "", repo: Optional[str] = None
    ) -> TrainOverrideResult:
        params = {**_train_common(self._config, repo), "wp": wp, "reason": reason}
        envelope = await self._transport.invoke(BINARY, "queue-remove", params)
        return TrainOverrideResult.model_validate(_result_payload(envelope))

    async def status(self, *, repo: Optional[str] = None) -> TrainStatusResult:
        envelope = await self._transport.invoke(
            BINARY, "status", _train_common(self._config, repo)
        )
        return TrainStatusResult.model_validate(_result_payload(envelope))

    async def doctor(self, *, repo: Optional[str] = None) -> TrainDoctorResult:
        envelope = await self._transport.invoke(
            BINARY, "doctor", _train_common(self._config, repo)
        )
        return TrainDoctorResult.model_validate(_result_payload(envelope))

    async def inspect(self, *, train_id: Optional[str] = None) -> "TrainInspectResult":
        params = _train_common(self._config, None)
        if train_id is not None:
            params["train_id"] = train_id
        params["json"] = True
        envelope = await self._transport.invoke(BINARY, "inspect", params)
        return TrainInspectResult.model_validate(_result_payload(envelope))

    async def run(
        self,
        *,
        deploy_workflow: str,
        force: bool = False,
        staging_url: Optional[str] = None,
        health_path: Optional[str] = None,
        smoke_cmd: Optional[str] = None,
        ci_poll_interval: Optional[int] = None,
        deploy_poll_interval: Optional[int] = None,
        max_batch_size: int = 5,
        base_branch: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> TrainRunResult:
        params = _kwargs_to_params({
            **_train_common(self._config, repo),
            "force": force,
            "deploy_workflow": deploy_workflow,
            "staging_url": staging_url,
            "health_path": health_path,
            "smoke_cmd": smoke_cmd,
            "ci_poll_interval": ci_poll_interval,
            "deploy_poll_interval": deploy_poll_interval,
            "max_batch_size": max_batch_size,
            "base_branch": base_branch,
        })
        envelope = await self._transport.invoke(BINARY, "run", params)
        return TrainRunResult.model_validate(_result_payload(envelope))
