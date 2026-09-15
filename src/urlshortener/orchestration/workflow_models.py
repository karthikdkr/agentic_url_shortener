from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    ROLLED_BACK = "rolled_back"
    SAFE_STOP = "safe_stop"


class RunStatus(str, Enum):
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SAFE_STOP = "safe_stop"


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    node_id: str
    summary: str
    rationale: str
    parent_decision_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    at: datetime = Field(default_factory=utc_now)
    event_type: str
    node_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    node_id: str
    approved: bool
    reviewer: str
    note: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    decided_at: datetime = Field(default_factory=utc_now)


class NodeExecution(BaseModel):
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_error: str | None = None
    used_fallback: bool = False


class WorkflowRun(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    requirement: str
    scenario_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RunStatus = RunStatus.RUNNING
    plan_version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    first_failure_at: datetime | None = None
    recovered_at: datetime | None = None
    nodes: dict[str, NodeExecution] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    decisions: list[Decision] = Field(default_factory=list)
    approvals: dict[str, ApprovalDecision] = Field(default_factory=dict)
    audit: list[AuditEvent] = Field(default_factory=list)
    retry_count: int = 0
    rollback_count: int = 0
