# Final Engineering Summary

## Plan and rationale

The solution separates the product problem from the engineering control problem. The URL shortener is a conventional layered service. The agentic system is a separate control plane that turns requirements into staged, reviewable engineering evidence.

The central design choice is an explicit dependency graph rather than a linear chain. That allows independent work to proceed concurrently while still forcing synchronization before release. Human approval is represented as state in the graph, including an extra preimplementation checkpoint for high impact changes. This makes oversight auditable and prevents silent bypass.

## Delivered artifacts

The repository includes a runnable API, persistence models, URL domain service, analytics, safety controls, agent definitions, workflow graph, orchestrator, policy engine, state store, tests, Docker packaging, GitHub CI, three scenarios, generated demo traces, and supporting documentation.

## Risks and tradeoffs

SQLite and a process local rate limiter are intentionally optimized for local reproducibility. They are not presented as horizontally scalable production choices.

The workflow store is atomic for one process but does not provide distributed locking. A production control plane should use a transactional shared store and durable queue.

The default agents are deterministic. This keeps local execution reproducible and removes unnecessary external service dependencies. The tradeoff is less open ended generation flexibility. The `Agent` interface is the extension seam for alternate agent implementations.

Analytics intentionally avoid storing raw IP addresses. This reduces privacy exposure but means exact unique visitor counts are not available.

## Validation and safety

URL inputs are constrained to HTTP and HTTPS. Custom aliases have a strict character set. Generated aliases rely on both randomness and a database unique constraint. Collision handling has a fixed retry bound.

The agentic system checks dependency gates, stage output contracts, output policy rules, retry limits, approval state, and rollback behavior. Critical policy findings and rejected release approvals stop the workflow safely.

Automated tests validate product and orchestration behavior. CI reruns lint and tests independently of the workflow agent reports.

## Assumptions

The project is a prototype intended to run locally or in one container. The default environment requires no external service credentials. The workflow favors inspectable orchestration and governance behavior with reproducible local execution.

## Limitations

The prototype does not include authentication or multi tenant authorization. It does not include a malicious URL reputation provider. It does not run a distributed data store or rate limiter. It does not execute arbitrary generated code from agents because doing so would weaken the controlled autonomy and safety model.

## Next production steps

Move URL data and workflow state to managed PostgreSQL. Put rate limiting at the gateway or Redis layer. Add authentication and per tenant quotas. Export metrics and audit events to the organization observability stack. Add SAST, dependency, secret, and SBOM gates. Introduce a durable workflow queue. Add alternate agent implementations only behind the same output schemas, policies, retry limits, and human gates.
