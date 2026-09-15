# Required Scenarios

## Greenfield

Requirement: create a URL shortener capability with custom aliases, optional expiration, redirect tracking, tests, and release controls.

Decomposition starts from normalized acceptance criteria, then separates architecture and risk work. Implementation is followed by parallel unit testing, integration testing, documentation, and security review. Release readiness synchronizes those outputs. Human release approval is mandatory before the final summary.

Demonstration input is in `scenarios/greenfield.json`. Generated execution evidence is in `artifacts/demos/greenfield.json` after the demo script runs.

## Brownfield

Requirement: improve existing analytics without storing raw visitor IP addresses.

The `codebase_reasoning` node is conditionally enabled. It scans real Python modules in the repository, ranks them by requirement and domain keyword overlap, extracts defined symbols, and returns an impacted file map plus data flow. Architecture planning waits for both decomposition and codebase reasoning before it proceeds.

This is deliberately different from a generic plan. The change proposal is grounded in the current repository before implementation scope is chosen.

Demonstration input is in `scenarios/brownfield.json`.

## Ambiguous

Requirement: make short links better, keep them a while, and make the service fast and secure.

Requirement understanding detects the lack of measurable retention and service targets. The graph then stops at `clarification_gate` instead of inventing requirements. A human can supply values such as retention days, availability target, and latency target. Those values are persisted in workflow context and execution resumes.

The clarification approval does not replace release governance. A separate release approval is still required after automated validation.

Demonstration input is in `scenarios/ambiguous.json`.

## Failure and recovery demonstration

Set workflow metadata `simulate_transient_failure` to true. The first implementation attempt fails. The orchestrator records the error, increments retry metrics, waits briefly, and retries within the node attempt limit. The second attempt succeeds and MTTR becomes measurable.

If all attempts fail and a fallback is configured, the fallback agent runs. If a critical policy finding occurs, the workflow safe stops and a mutating stage restores its artifact snapshot.

## Dynamic requirement change demonstration

Call the replan endpoint with a changed requirement. The run increments its plan version, clears downstream artifacts and approvals, records the reason and affected nodes, and starts again from requirement understanding. This preserves governance when an upstream assumption changes.
