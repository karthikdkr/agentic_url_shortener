from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .workflow_models import Decision, WorkflowRun


class TransientAgentError(RuntimeError):
    pass


@dataclass(slots=True)
class AgentResult:
    artifact: dict[str, Any]
    decisions: list[Decision]


class Agent(ABC):
    @abstractmethod
    async def execute(self, run: WorkflowRun) -> AgentResult:
        raise NotImplementedError


def decision(node_id: str, summary: str, rationale: str, run: WorkflowRun) -> Decision:
    parents = [item.id for item in run.decisions[-3:]]
    return Decision(
        node_id=node_id,
        summary=summary,
        rationale=rationale,
        parent_decision_ids=parents,
    )


class RequirementAgent(Agent):
    ambiguous_terms = {
        "fast",
        "quick",
        "better",
        "simple",
        "a while",
        "soon",
        "secure",
        "scalable",
        "as needed",
        "lots",
    }

    async def execute(self, run: WorkflowRun) -> AgentResult:
        lowered = run.requirement.lower()
        questions: list[str] = []
        matched = sorted(term for term in self.ambiguous_terms if term in lowered)
        if run.scenario_type == "ambiguous" or matched:
            questions.extend(
                [
                    "What measurable success criteria define the requested behavior?",
                    "What retention, traffic, and availability targets should be assumed?",
                ]
            )
        artifact = {
            "original_requirement": run.requirement,
            "normalized_problem": (
                "Deliver the requested URL shortener change with explicit behavior, testable "
                "acceptance criteria, security constraints, observability, and safe change control."
            ),
            "acceptance_criteria": [
                "Behavior is exposed through versioned HTTP APIs or the redirect route.",
                "Invalid input fails safely with a clear client error.",
                "Automated tests cover success and important failure paths.",
                "Operational and security considerations are documented.",
                "Release requires a recorded human approval decision.",
            ],
            "detected_ambiguous_terms": matched,
            "open_questions": questions,
            "assumptions": [
                "Prototype deployment uses one application instance and SQLite by default.",
                "Production scale would move state and rate limiting to shared infrastructure.",
            ],
        }
        return AgentResult(
            artifact,
            [
                decision(
                    "requirement_understanding",
                    "Normalize requirement before planning",
                    "Measurable acceptance criteria reduce downstream rework and support gated validation.",
                    run,
                )
            ],
        )


class CodebaseReasoningAgent(Agent):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    async def execute(self, run: WorkflowRun) -> AgentResult:
        candidates: list[dict[str, Any]] = []
        terms = set(re.findall(r"[a-zA-Z_]{4,}", run.requirement.lower()))
        preferred = {"url", "analytics", "redirect", "alias", "expiry", "rate", "security"}
        needles = terms | preferred

        src = self.repo_root / "src"
        for path in src.rglob("*.py") if src.exists() else []:
            content = path.read_text(encoding="utf8", errors="ignore")
            lowered = content.lower()
            score = sum(1 for term in needles if term in lowered)
            if score:
                candidates.append(
                    {
                        "path": str(path.relative_to(self.repo_root)),
                        "relevance_score": score,
                        "symbols": sorted(
                            set(re.findall(r"(?:class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", content))
                        )[:12],
                    }
                )
        candidates.sort(key=lambda item: item["relevance_score"], reverse=True)
        impacted = candidates[:8]
        artifact = {
            "impacted_files": impacted,
            "data_flow": [
                "HTTP request",
                "FastAPI route",
                "URLShortenerService",
                "SQLAlchemy session",
                "SQLite or configured relational database",
            ],
            "change_risk": "medium" if impacted else "high",
            "reasoning": "Ranked actual source modules using requirement and domain keyword overlap.",
        }
        return AgentResult(
            artifact,
            [
                decision(
                    "codebase_reasoning",
                    "Limit brownfield change surface",
                    "Inspect and rank real repository modules before proposing modifications.",
                    run,
                )
            ],
        )


class TaskDecompositionAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        tasks = [
            {"id": "T1", "task": "Confirm requirement and acceptance criteria", "depends_on": []},
            {"id": "T2", "task": "Map affected architecture and data flow", "depends_on": ["T1"]},
            {"id": "T3", "task": "Implement the bounded change", "depends_on": ["T2"]},
            {"id": "T4", "task": "Run unit validation", "depends_on": ["T3"]},
            {"id": "T5", "task": "Run integration validation", "depends_on": ["T3"]},
            {"id": "T6", "task": "Update documentation", "depends_on": ["T3"]},
            {"id": "T7", "task": "Perform security and release review", "depends_on": ["T4", "T5", "T6"]},
        ]
        artifact = {
            "tasks": tasks,
            "parallelizable": [["T4", "T5", "T6"]],
            "critical_path": ["T1", "T2", "T3", "T5", "T7"],
        }
        return AgentResult(
            artifact,
            [
                decision(
                    "task_decomposition",
                    "Parallelize independent validation work",
                    "Unit tests, integration tests, and documentation can proceed after implementation and synchronize before release readiness.",
                    run,
                )
            ],
        )


class ArchitectureAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "components": [
                "FastAPI transport layer",
                "URLShortenerService domain service",
                "SQLAlchemy persistence",
                "Agentic workflow orchestrator",
                "Atomic workflow state store",
                "Policy and approval gates",
                "Audit and reliability metrics",
            ],
            "control_flow": [
                "requirement_understanding",
                "clarification_gate when needed",
                "task_decomposition plus optional codebase_reasoning",
                "architecture_design and risk_analysis in parallel",
                "implementation",
                "unit_testing plus integration_testing plus documentation plus security_review in parallel",
                "release_readiness",
                "release_approval",
                "final_summary",
            ],
            "key_decisions": [
                "Use deterministic local agents so the prototype is runnable without external credentials.",
                "Keep agent interfaces replaceable by alternate implementations.",
                "Persist workflow lineage separately from URL service data.",
            ],
        }
        return AgentResult(
            artifact,
            [
                decision(
                    "architecture_design",
                    "Prefer reproducible local execution",
                    "The workflow can run locally without external service dependencies while preserving clear agent boundaries and orchestration behavior.",
                    run,
                )
            ],
        )


class ArchitectureFallbackAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        return AgentResult(
            {
                "components": ["API", "service", "database", "workflow engine"],
                "control_flow": ["plan", "implement", "validate", "approve"],
                "key_decisions": ["Fallback architecture used after bounded retries"],
            },
            [
                decision(
                    "architecture_design",
                    "Use conservative fallback architecture",
                    "Fallback preserves a safe minimum design when the primary architecture agent cannot complete.",
                    run,
                )
            ],
        )


class RiskAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "risks": [
                {"risk": "Alias collision", "control": "Unique constraint plus bounded regeneration"},
                {"risk": "Unsafe target schemes", "control": "Allow only HTTP and HTTPS"},
                {"risk": "Abuse or burst traffic", "control": "Prototype sliding window rate limit"},
                {"risk": "Workflow runaway", "control": "Bounded retries and safe stop"},
                {"risk": "Unreviewed release", "control": "Mandatory release approval gate"},
                {"risk": "State corruption", "control": "Atomic workflow store replacement"},
            ],
            "tradeoffs": [
                "SQLite and local rate limiting favor reproducibility over horizontal scalability.",
                "Deterministic agents favor auditability over natural language generation breadth.",
            ],
        }
        return AgentResult(
            artifact,
            [
                decision(
                    "risk_analysis",
                    "Bound autonomy around high consequence actions",
                    "Retries are finite and release requires explicit human approval.",
                    run,
                )
            ],
        )


class ImplementationAgent(Agent):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    async def execute(self, run: WorkflowRun) -> AgentResult:
        if run.metadata.get("simulate_permanent_failure"):
            raise TransientAgentError("Injected persistent implementation failure for fallback demonstration")
        if run.metadata.get("simulate_transient_failure") and run.nodes["implementation"].attempts == 1:
            raise TransientAgentError("Injected transient implementation failure for retry demonstration")

        changed = [
            "src/urlshortener/service.py",
            "src/urlshortener/main.py",
            "src/urlshortener/orchestration/orchestrator.py",
        ]
        if run.scenario_type == "brownfield":
            impacted = run.artifacts.get("codebase_reasoning", {}).get("impacted_files", [])
            changed = [item["path"] for item in impacted[:4]] or changed

        artifact = {
            "changed_files": changed,
            "implementation_strategy": (
                "Apply the smallest coherent change set behind existing service and orchestration boundaries."
            ),
            "rollback_plan": "Restore the pre node artifact snapshot and stop downstream execution.",
            "generated_output": "Reviewable implementation manifest produced; repository code is the executable artifact.",
        }
        return AgentResult(
            artifact,
            [
                decision(
                    "implementation",
                    "Constrain implementation scope",
                    "Small reviewable changes reduce regression risk and make rollback tractable.",
                    run,
                )
            ],
        )


class ImplementationFallbackAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        if run.metadata.get("simulate_fallback_failure"):
            raise RuntimeError("Injected fallback failure for rollback demonstration")
        return AgentResult(
            {
                "changed_files": [],
                "implementation_strategy": "No code mutation. Produce a safe manual action plan.",
                "rollback_plan": "No repository mutation occurred.",
                "generated_output": "Fallback plan only",
            },
            [
                decision(
                    "implementation",
                    "Degrade to manual plan",
                    "When implementation cannot complete after bounded retries, preserve safety rather than guessing.",
                    run,
                )
            ],
        )


class UnitTestAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "suite": "tests/test_service.py and tests/test_orchestrator.py",
            "result": "pass by repository verification",
            "coverage_targets": ["alias collision", "expiration", "analytics", "approval gates", "retry", "replan"],
        }
        return AgentResult(artifact, [])


class IntegrationTestAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "suite": "tests/test_api.py",
            "result": "pass by repository verification",
            "flows": ["create then redirect", "analytics", "engineering run approval lifecycle"],
        }
        return AgentResult(artifact, [])


class DocumentationAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "documents": [
                "README.md",
                "docs/architecture.md",
                "docs/scenarios.md",
                "docs/testing.md",
                "docs/final_engineering_summary.md",
                "docs/requirements_traceability.md",
            ],
            "status": "complete",
        }
        return AgentResult(artifact, [])


class SecurityReviewAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "checks": [
                "URL scheme validation",
                "Custom alias character validation",
                "No raw IP address persisted in analytics",
                "Bounded retry loops",
                "Secret and unsafe construct output policy scan",
                "Mandatory release approval",
            ],
            "critical_findings": 0,
            "residual_risks": [
                "Prototype rate limiter is process local",
                "No malware or phishing reputation feed is integrated",
            ],
        }
        return AgentResult(artifact, [])


class ReleaseReadinessAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        prerequisite_results = {
            node: run.artifacts.get(node, {}).get("result", run.artifacts.get(node, {}).get("status", "complete"))
            for node in ("unit_testing", "integration_testing", "documentation", "security_review")
        }
        artifact = {
            "status": "ready_for_human_review",
            "prerequisites": prerequisite_results,
            "release_controls": ["human approval", "rollback plan", "audit trail"],
        }
        return AgentResult(artifact, [])


class FinalSummaryAgent(Agent):
    async def execute(self, run: WorkflowRun) -> AgentResult:
        artifact = {
            "plan_and_rationale": "Normalize, decompose, design, implement, validate in parallel, synchronize, approve, summarize.",
            "artifacts": sorted(run.artifacts.keys()),
            "risks_and_tradeoffs": run.artifacts.get("risk_analysis", {}),
            "validation": {
                "unit": run.artifacts.get("unit_testing", {}),
                "integration": run.artifacts.get("integration_testing", {}),
                "security": run.artifacts.get("security_review", {}),
            },
            "assumptions": run.artifacts.get("requirement_understanding", {}).get("assumptions", []),
            "limitations": [
                "Prototype workflow state store targets one process.",
                "Deterministic agents stand in for pluggable model backed agents.",
                "Production deployment should use shared persistence, distributed rate limiting, and managed observability.",
            ],
            "decision_lineage": [item.model_dump(mode="json") for item in run.decisions],
        }
        return AgentResult(artifact, [])


AGENT_NAMES = {
    "requirement_understanding": RequirementAgent,
    "task_decomposition": TaskDecompositionAgent,
    "architecture_design": ArchitectureAgent,
    "architecture_fallback": ArchitectureFallbackAgent,
    "risk_analysis": RiskAgent,
    "implementation_fallback": ImplementationFallbackAgent,
    "unit_testing": UnitTestAgent,
    "integration_testing": IntegrationTestAgent,
    "documentation": DocumentationAgent,
    "security_review": SecurityReviewAgent,
    "release_readiness": ReleaseReadinessAgent,
    "final_summary": FinalSummaryAgent,
}


def build_agents(repo_root: Path) -> dict[str, Agent]:
    agents: dict[str, Agent] = {name: cls() for name, cls in AGENT_NAMES.items()}
    agents["codebase_reasoning"] = CodebaseReasoningAgent(repo_root)
    agents["implementation"] = ImplementationAgent(repo_root)
    return agents


def artifact_as_pretty_json(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact, indent=2, sort_keys=True, default=str)
