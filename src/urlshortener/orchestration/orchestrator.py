from __future__ import annotations

import asyncio
import copy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agents import Agent, TransientAgentError, build_agents
from .graph import NODE_MAP, NODES, descendants
from .policies import critical, inspect_artifact
from .store import WorkflowStore
from .workflow_models import (
    ApprovalDecision,
    AuditEvent,
    NodeExecution,
    NodeStatus,
    RunStatus,
    WorkflowRun,
)


class RunNotFound(LookupError):
    pass


class InvalidApproval(ValueError):
    pass


class Orchestrator:
    def __init__(self, store: WorkflowStore, repo_root: Path | None = None) -> None:
        self.store = store
        self.repo_root = repo_root or Path.cwd()
        self.agents = build_agents(self.repo_root)

    async def start(
        self,
        requirement: str,
        scenario_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        run = WorkflowRun(
            requirement=requirement,
            scenario_type=scenario_type,
            metadata=metadata or {},
            nodes={node.id: NodeExecution(node_id=node.id) for node in NODES},
        )
        self._event(run, "run_started", detail={"scenario_type": scenario_type})
        self.store.save(run)
        return await self._drive(run)

    def get(self, run_id: str) -> WorkflowRun:
        run = self.store.get(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return run

    async def approve(
        self,
        run_id: str,
        node_id: str,
        approved: bool,
        reviewer: str,
        note: str,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        run = self.get(run_id)
        if node_id not in NODE_MAP or not NODE_MAP[node_id].approval_gate:
            raise InvalidApproval(f"{node_id} is not an approval gate")
        execution = run.nodes[node_id]
        if execution.status != NodeStatus.WAITING_APPROVAL:
            raise InvalidApproval(f"{node_id} is not waiting for approval")

        approval = ApprovalDecision(
            node_id=node_id,
            approved=approved,
            reviewer=reviewer,
            note=note,
            payload=payload or {},
        )
        run.approvals[node_id] = approval
        self._event(
            run,
            "approval_recorded",
            node_id=node_id,
            detail={"approved": approved, "reviewer": reviewer, "note": note},
        )

        if not approved:
            execution.status = NodeStatus.SAFE_STOP
            execution.finished_at = datetime.now(UTC)
            run.status = RunStatus.SAFE_STOP
            run.completed_at = datetime.now(UTC)
            self._event(run, "safe_stop", node_id=node_id, detail={"reason": "approval rejected"})
            self.store.save(run)
            return run

        if node_id == "clarification_gate":
            run.context["clarifications"] = approval.payload
        execution.status = NodeStatus.SUCCESS
        execution.finished_at = datetime.now(UTC)
        run.status = RunStatus.RUNNING
        self.store.save(run)
        return await self._drive(run)

    async def replan(self, run_id: str, changed_requirement: str, reason: str) -> WorkflowRun:
        run = self.get(run_id)
        previous_requirement = run.requirement
        run.requirement = changed_requirement
        run.plan_version += 1
        run.status = RunStatus.RUNNING
        run.completed_at = None
        run.context["replan_reason"] = reason
        run.context["previous_requirement"] = previous_requirement

        affected = {"requirement_understanding"} | descendants("requirement_understanding")
        for node_id in affected:
            run.nodes[node_id] = NodeExecution(node_id=node_id)
            run.artifacts.pop(node_id, None)
            run.approvals.pop(node_id, None)

        self._event(
            run,
            "replan_started",
            detail={"reason": reason, "plan_version": run.plan_version, "affected_nodes": sorted(affected)},
        )
        self.store.save(run)
        return await self._drive(run)

    async def _drive(self, run: WorkflowRun) -> WorkflowRun:
        while True:
            if run.status in {RunStatus.FAILED, RunStatus.SAFE_STOP, RunStatus.COMPLETED}:
                return run

            progress = False
            ready_agents: list[str] = []

            for node in NODES:
                execution = run.nodes[node.id]
                if execution.status != NodeStatus.PENDING:
                    continue
                if not self._dependencies_satisfied(run, node.dependencies):
                    continue

                if node.condition is not None and not node.condition(run):
                    execution.status = NodeStatus.SKIPPED
                    execution.finished_at = datetime.now(UTC)
                    self._event(run, "node_skipped", node_id=node.id)
                    progress = True
                    continue

                if node.approval_gate:
                    execution.status = NodeStatus.WAITING_APPROVAL
                    execution.started_at = execution.started_at or datetime.now(UTC)
                    run.status = RunStatus.WAITING_APPROVAL
                    self._event(run, "approval_requested", node_id=node.id)
                    self.store.save(run)
                    return run

                ready_agents.append(node.id)

            if ready_agents:
                progress = True
                await asyncio.gather(*(self._execute_node(run, node_id) for node_id in ready_agents))
                run.updated_at = datetime.now(UTC)
                self.store.save(run)

                if any(
                    item.status in {NodeStatus.FAILED, NodeStatus.SAFE_STOP}
                    for item in run.nodes.values()
                ):
                    run.status = (
                        RunStatus.SAFE_STOP
                        if any(item.status == NodeStatus.SAFE_STOP for item in run.nodes.values())
                        else RunStatus.FAILED
                    )
                    run.completed_at = datetime.now(UTC)
                    self.store.save(run)
                    return run

            final_status = run.nodes["final_summary"].status
            if final_status == NodeStatus.SUCCESS:
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now(UTC)
                self._event(run, "run_completed")
                self.store.save(run)
                return run

            if not progress:
                pending = [item.node_id for item in run.nodes.values() if item.status == NodeStatus.PENDING]
                if pending:
                    run.status = RunStatus.FAILED
                    run.completed_at = datetime.now(UTC)
                    self._event(run, "run_failed", detail={"reason": "blocked graph", "pending": pending})
                    self.store.save(run)
                return run

    async def _execute_node(self, run: WorkflowRun, node_id: str) -> None:
        node = NODE_MAP[node_id]
        execution = run.nodes[node_id]
        execution.status = NodeStatus.RUNNING
        execution.started_at = execution.started_at or datetime.now(UTC)
        snapshot = copy.deepcopy(run.artifacts) if node.mutating else None
        self._event(run, "node_started", node_id=node_id)

        agent = self.agents[node_id]
        last_error: Exception | None = None

        for attempt in range(1, node.max_attempts + 1):
            execution.attempts = attempt
            try:
                result = await agent.execute(run)
                findings = inspect_artifact(result.artifact)
                if critical(findings):
                    execution.status = NodeStatus.SAFE_STOP
                    execution.last_error = "Critical policy finding"
                    execution.finished_at = datetime.now(UTC)
                    self._event(
                        run,
                        "policy_safe_stop",
                        node_id=node_id,
                        detail={"findings": [asdict(item) for item in findings]},
                    )
                    if snapshot is not None:
                        run.artifacts = snapshot
                        run.rollback_count += 1
                        self._event(run, "rollback", node_id=node_id, detail={"reason": "policy violation"})
                    return

                self._validate_result(node_id, result.artifact)
                run.artifacts[node_id] = result.artifact
                run.decisions.extend(result.decisions)
                execution.status = NodeStatus.SUCCESS
                execution.finished_at = datetime.now(UTC)
                if run.first_failure_at and not run.recovered_at:
                    run.recovered_at = datetime.now(UTC)
                self._event(
                    run,
                    "node_succeeded",
                    node_id=node_id,
                    detail={"attempt": attempt, "findings": [asdict(item) for item in findings]},
                )
                return
            except (TransientAgentError, ValueError, RuntimeError) as exc:
                last_error = exc
                execution.last_error = str(exc)
                if run.first_failure_at is None:
                    run.first_failure_at = datetime.now(UTC)
                if attempt < node.max_attempts:
                    run.retry_count += 1
                    self._event(
                        run,
                        "node_retry",
                        node_id=node_id,
                        detail={"attempt": attempt, "error": str(exc)},
                    )
                    await asyncio.sleep(min(0.01 * (2 ** (attempt - 1)), 0.05))
                    continue
                break

        if node.fallback_agent:
            try:
                fallback = self.agents[node.fallback_agent]
                result = await fallback.execute(run)
                self._validate_result(node_id, result.artifact)
                run.artifacts[node_id] = result.artifact
                run.decisions.extend(result.decisions)
                execution.status = NodeStatus.SUCCESS
                execution.used_fallback = True
                execution.finished_at = datetime.now(UTC)
                self._event(
                    run,
                    "fallback_succeeded",
                    node_id=node_id,
                    detail={"fallback_agent": node.fallback_agent},
                )
                return
            except Exception as exc:  # defensive containment around fallback boundary
                last_error = exc
                execution.last_error = str(exc)

        if snapshot is not None:
            run.artifacts = snapshot
            run.rollback_count += 1
            execution.status = NodeStatus.ROLLED_BACK
            self._event(run, "rollback", node_id=node_id, detail={"reason": str(last_error)})
        else:
            execution.status = NodeStatus.FAILED
        execution.finished_at = datetime.now(UTC)
        self._event(run, "node_failed", node_id=node_id, detail={"error": str(last_error)})

    @staticmethod
    def _dependencies_satisfied(run: WorkflowRun, dependencies: tuple[str, ...]) -> bool:
        acceptable = {NodeStatus.SUCCESS, NodeStatus.SKIPPED}
        return all(run.nodes[item].status in acceptable for item in dependencies)

    @staticmethod
    def _validate_result(node_id: str, artifact: dict[str, Any]) -> None:
        required_fields = {
            "requirement_understanding": {"normalized_problem", "acceptance_criteria", "open_questions"},
            "codebase_reasoning": {"impacted_files", "data_flow"},
            "task_decomposition": {"tasks", "critical_path"},
            "architecture_design": {"components", "control_flow", "key_decisions"},
            "risk_analysis": {"risks", "tradeoffs"},
            "implementation": {"changed_files", "rollback_plan"},
            "unit_testing": {"result"},
            "integration_testing": {"result"},
            "documentation": {"status"},
            "security_review": {"critical_findings"},
            "release_readiness": {"status", "release_controls"},
            "final_summary": {"plan_and_rationale", "risks_and_tradeoffs", "limitations"},
        }
        missing = required_fields.get(node_id, set()) - set(artifact)
        if missing:
            raise ValueError(f"{node_id} output missing required fields: {sorted(missing)}")
        if node_id in {"unit_testing", "integration_testing"} and artifact.get("result") != "pass by repository verification":
            raise ValueError(f"{node_id} did not pass")
        if node_id == "security_review" and artifact.get("critical_findings") != 0:
            raise ValueError("Security review contains critical findings")

    @staticmethod
    def _event(
        run: WorkflowRun,
        event_type: str,
        node_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        run.audit.append(AuditEvent(event_type=event_type, node_id=node_id, detail=detail or {}))
        run.updated_at = datetime.now(UTC)

    def metrics(self) -> dict[str, Any]:
        runs = self.store.all()
        total = len(runs)
        completed = sum(run.status == RunStatus.COMPLETED for run in runs)
        failed = sum(run.status in {RunStatus.FAILED, RunStatus.SAFE_STOP} for run in runs)
        latencies = [
            (run.completed_at - run.created_at).total_seconds()
            for run in runs
            if run.completed_at is not None
        ]
        recovery_times = [
            (run.recovered_at - run.first_failure_at).total_seconds()
            for run in runs
            if run.recovered_at is not None and run.first_failure_at is not None
        ]
        return {
            "runs_total": total,
            "success_rate": completed / total if total else 0.0,
            "failed_or_safe_stopped": failed,
            "retry_count": sum(run.retry_count for run in runs),
            "rollback_count": sum(run.rollback_count for run in runs),
            "retry_frequency_per_run": sum(run.retry_count for run in runs) / total if total else 0.0,
            "rollback_frequency_per_run": sum(run.rollback_count for run in runs) / total if total else 0.0,
            "mean_end_to_end_latency_seconds": sum(latencies) / len(latencies) if latencies else None,
            "mttr_seconds": sum(recovery_times) / len(recovery_times) if recovery_times else None,
        }
