from __future__ import annotations

import asyncio
import json
from pathlib import Path

from urlshortener.orchestration.orchestrator import Orchestrator
from urlshortener.orchestration.store import WorkflowStore
from urlshortener.orchestration.workflow_models import RunStatus

ROOT = Path(__file__).resolve().parents[1]


async def execute_scenario(orchestrator: Orchestrator, path: Path):
    scenario = json.loads(path.read_text(encoding="utf8"))
    run = await orchestrator.start(
        scenario["requirement"], scenario["scenario_type"], scenario.get("metadata", {})
    )

    if run.status == RunStatus.WAITING_APPROVAL and run.nodes["clarification_gate"].status.value == "waiting_approval":
        run = await orchestrator.approve(
            run.id,
            "clarification_gate",
            True,
            "demo_product_owner",
            "Clarifications accepted for demonstration",
            scenario.get("clarification_payload", {}),
        )

    if run.status == RunStatus.WAITING_APPROVAL and run.nodes["release_approval"].status.value == "waiting_approval":
        run = await orchestrator.approve(
            run.id,
            "release_approval",
            True,
            "demo_release_reviewer",
            "All automated gates passed",
        )

    output = ROOT / "artifacts" / "demos" / f"{path.stem}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run.model_dump(mode="json"), indent=2), encoding="utf8")
    print(f"{scenario['name']}: {run.status.value} -> {output.relative_to(ROOT)}")


async def main():
    state = ROOT / "artifacts" / "demos" / "scenario_state.json"
    if state.exists():
        state.unlink()
    orchestrator = Orchestrator(WorkflowStore(str(state)), repo_root=ROOT)
    for name in ("greenfield.json", "brownfield.json", "ambiguous.json"):
        await execute_scenario(orchestrator, ROOT / "scenarios" / name)
    metrics = orchestrator.metrics()
    metrics_path = ROOT / "artifacts" / "demos" / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf8")
    if state.exists():
        state.unlink()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
