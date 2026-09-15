from __future__ import annotations

import asyncio

from urlshortener.orchestration.orchestrator import Orchestrator
from urlshortener.orchestration.store import WorkflowStore
from urlshortener.orchestration.workflow_models import NodeStatus, RunStatus


def run(coro):
    return asyncio.run(coro)


def test_greenfield_waits_for_release_approval_then_completes(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(orchestrator.start("Create URL expiration support with tests", "greenfield"))

    assert item.status == RunStatus.WAITING_APPROVAL
    assert item.nodes["clarification_gate"].status == NodeStatus.SKIPPED
    assert item.nodes["release_approval"].status == NodeStatus.WAITING_APPROVAL
    assert item.nodes["architecture_design"].status == NodeStatus.SUCCESS
    assert item.nodes["risk_analysis"].status == NodeStatus.SUCCESS

    completed = run(
        orchestrator.approve(
            item.id,
            "release_approval",
            True,
            "reviewer",
            "Validated change",
        )
    )
    assert completed.status == RunStatus.COMPLETED
    assert "final_summary" in completed.artifacts


def test_ambiguous_scenario_requires_clarification(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(orchestrator.start("Make short links better and keep them a while", "ambiguous"))
    assert item.status == RunStatus.WAITING_APPROVAL
    assert item.nodes["clarification_gate"].status == NodeStatus.WAITING_APPROVAL

    resumed = run(
        orchestrator.approve(
            item.id,
            "clarification_gate",
            True,
            "product_owner",
            "Use 30 day expiration and 99.9 percent availability target",
            {"retention_days": 30, "availability_target": "99.9%"},
        )
    )
    assert resumed.nodes["clarification_gate"].status == NodeStatus.SUCCESS
    assert resumed.nodes["release_approval"].status == NodeStatus.WAITING_APPROVAL


def test_bounded_retry_recovers(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(
        orchestrator.start(
            "Add reliable redirect handling and tests",
            "greenfield",
            {"simulate_transient_failure": True},
        )
    )
    assert item.retry_count == 1
    assert item.nodes["implementation"].attempts == 2
    assert item.nodes["implementation"].status == NodeStatus.SUCCESS


def test_replan_invalidates_downstream_and_increments_plan_version(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(orchestrator.start("Add expiration support to URL creation", "greenfield"))
    assert item.nodes["release_approval"].status == NodeStatus.WAITING_APPROVAL

    replanned = run(
        orchestrator.replan(
            item.id,
            "Add expiration support and expose remaining lifetime in URL details",
            "Product requirement changed after design review",
        )
    )
    assert replanned.plan_version == 2
    assert replanned.nodes["release_approval"].status == NodeStatus.WAITING_APPROVAL
    assert any(event.event_type == "replan_started" for event in replanned.audit)


def test_rejected_release_safe_stops(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(orchestrator.start("Add URL analytics export", "greenfield"))
    stopped = run(
        orchestrator.approve(
            item.id,
            "release_approval",
            False,
            "security_reviewer",
            "Do not release until privacy review is complete",
        )
    )
    assert stopped.status == RunStatus.SAFE_STOP
    assert stopped.nodes["release_approval"].status == NodeStatus.SAFE_STOP


def test_high_impact_change_requires_preimplementation_approval(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(
        orchestrator.start(
            "Add authentication and authorization to URL management APIs",
            "greenfield",
        )
    )
    assert item.status == RunStatus.WAITING_APPROVAL
    assert item.nodes["change_approval"].status == NodeStatus.WAITING_APPROVAL
    assert item.nodes["implementation"].status == NodeStatus.PENDING

    resumed = run(
        orchestrator.approve(
            item.id,
            "change_approval",
            True,
            "security_owner",
            "Architecture and controls reviewed",
        )
    )
    assert resumed.nodes["implementation"].status == NodeStatus.SUCCESS
    assert resumed.nodes["release_approval"].status == NodeStatus.WAITING_APPROVAL


def test_fallback_after_bounded_primary_failures(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(
        orchestrator.start(
            "Add deterministic alias generation tests",
            "greenfield",
            {"simulate_permanent_failure": True},
        )
    )
    assert item.nodes["implementation"].status == NodeStatus.SUCCESS
    assert item.nodes["implementation"].used_fallback is True
    assert item.retry_count == 2


def test_failed_fallback_rolls_back_mutating_stage(tmp_path):
    orchestrator = Orchestrator(WorkflowStore(str(tmp_path / "runs.json")), repo_root=tmp_path)
    item = run(
        orchestrator.start(
            "Add deterministic alias generation tests",
            "greenfield",
            {"simulate_permanent_failure": True, "simulate_fallback_failure": True},
        )
    )
    assert item.status == RunStatus.FAILED
    assert item.nodes["implementation"].status == NodeStatus.ROLLED_BACK
    assert item.rollback_count == 1
    assert any(event.event_type == "rollback" for event in item.audit)
