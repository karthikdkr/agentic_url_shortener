# Requirements Traceability

| Engineering requirement | Implementation evidence |
| --- | --- |
| Requirement understanding | `RequirementAgent`, normalized problem, acceptance criteria, ambiguity detection |
| Task decomposition | `TaskDecompositionAgent` with dependencies, parallelizable set, and critical path |
| Brownfield codebase reasoning | `CodebaseReasoningAgent` scans actual source files and reports impacted modules and data flow |
| Explicit dependency graph | `orchestration/graph.py` |
| Entry and exit gates | Dependency checks, conditions, approval nodes, `_validate_result` |
| Sequential and parallel paths | Scheduler ready batches plus `asyncio.gather` |
| Synchronization | `release_readiness` depends on four parallel validation nodes |
| Cross stage context | `WorkflowRun.artifacts`, `context`, and `decisions` |
| Decision lineage | `Decision.parent_decision_ids` |
| Human approval checkpoints | `clarification_gate`, conditional `change_approval`, and mandatory `release_approval` |
| Bounded retries | Per node `max_attempts`, retry audit events, retry metrics |
| Fallback | Architecture and implementation fallback agents |
| Rollback | Artifact snapshot restore for failed mutating nodes |
| Safe stop | Rejected approval or critical policy finding |
| Security and compliance guardrails | `policies.py`, URL validation, privacy conscious analytics |
| Audit grade traceability | Timestamped `AuditEvent` list persisted with each run |
| Success, retry, rollback, MTTR, latency metrics | `Orchestrator.metrics()` |
| Dynamic replanning | `Orchestrator.replan()` invalidates descendants and approvals |
| Production quality outputs | URL APIs, schema models, tests, documentation, Docker, CI |
| Three scenarios | `scenarios/greenfield.json`, `brownfield.json`, `ambiguous.json` |
| Final engineering summary | Agent output plus `docs/final_engineering_summary.md` |
