"""Pydantic models for sulis-execution SDK responses.

Generated from sulis-execution.openapi.yaml. In Phase 0 (pilot) only
PipelineResult is defined; Phase 2 grows this to cover all 36
operations' response shapes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PipelineResult(BaseModel):
    """Result of `client.pipeline.run(...)`.

    Per the OpenAPI schema, outcome=success and outcome=blocker are
    both normal results. The blocker case is NOT raised as an exception.
    Inspect `outcome` and `blocker_reason` to decide what to do.
    """

    wp: str
    outcome: Literal["success", "blocker", "error", "pending"]
    merge_sha: Optional[str] = None
    deploy_url: Optional[str] = None
    deploy_workflow_run: Optional[str] = None
    health_status: Optional[Literal["healthy", "unhealthy", "skipped"]] = None
    health_url: Optional[str] = None
    smoke_verdict: Optional[str] = None
    blocker_reason: Optional[str] = None
    ci_poll_skipped: bool = False
    merge_already_complete: bool = False
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {
        "extra": "allow",  # Tolerate forward-compatible fields from the CLI
    }
