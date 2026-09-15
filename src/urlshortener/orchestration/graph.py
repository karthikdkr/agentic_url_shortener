from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .workflow_models import WorkflowRun


Condition = Callable[[WorkflowRun], bool]


@dataclass(frozen=True, slots=True)
class WorkflowNode:
    id: str
    dependencies: tuple[str, ...] = ()
    max_attempts: int = 2
    mutating: bool = False
    approval_gate: bool = False
    condition: Condition | None = None
    fallback_agent: str | None = None


def is_brownfield(run: WorkflowRun) -> bool:
    return run.scenario_type == "brownfield"


def has_open_questions(run: WorkflowRun) -> bool:
    artifact = run.artifacts.get("requirement_understanding", {})
    return bool(artifact.get("open_questions"))


def is_high_impact(run: WorkflowRun) -> bool:
    if bool(run.metadata.get("high_impact")):
        return True
    lowered = run.requirement.lower()
    markers = ("authentication", "authorization", "encryption", "migration", "delete data", "schema change")
    return any(marker in lowered for marker in markers)


NODES: tuple[WorkflowNode, ...] = (
    WorkflowNode("requirement_understanding"),
    WorkflowNode(
        "clarification_gate",
        dependencies=("requirement_understanding",),
        approval_gate=True,
        condition=has_open_questions,
    ),
    WorkflowNode(
        "codebase_reasoning",
        dependencies=("requirement_understanding", "clarification_gate"),
        condition=is_brownfield,
    ),
    WorkflowNode(
        "task_decomposition",
        dependencies=("requirement_understanding", "clarification_gate"),
    ),
    WorkflowNode(
        "architecture_design",
        dependencies=("task_decomposition", "codebase_reasoning"),
        fallback_agent="architecture_fallback",
    ),
    WorkflowNode("risk_analysis", dependencies=("task_decomposition",)),
    WorkflowNode(
        "change_approval",
        dependencies=("architecture_design", "risk_analysis"),
        approval_gate=True,
        condition=is_high_impact,
    ),
    WorkflowNode(
        "implementation",
        dependencies=("architecture_design", "risk_analysis", "change_approval"),
        mutating=True,
        max_attempts=3,
        fallback_agent="implementation_fallback",
    ),
    WorkflowNode("unit_testing", dependencies=("implementation",)),
    WorkflowNode("integration_testing", dependencies=("implementation",)),
    WorkflowNode("documentation", dependencies=("implementation",)),
    WorkflowNode("security_review", dependencies=("implementation",)),
    WorkflowNode(
        "release_readiness",
        dependencies=("unit_testing", "integration_testing", "documentation", "security_review"),
    ),
    WorkflowNode(
        "release_approval",
        dependencies=("release_readiness",),
        approval_gate=True,
    ),
    WorkflowNode("final_summary", dependencies=("release_approval",)),
)

NODE_MAP = {node.id: node for node in NODES}


def descendants(start_node: str) -> set[str]:
    result: set[str] = set()
    frontier = [start_node]
    while frontier:
        current = frontier.pop()
        for node in NODES:
            if current in node.dependencies and node.id not in result:
                result.add(node.id)
                frontier.append(node.id)
    return result
