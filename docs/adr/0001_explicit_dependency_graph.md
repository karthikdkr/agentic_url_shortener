# ADR 0001: Use an Explicit Dependency Graph

## Status

Accepted.

## Context

A linear chain can look agentic while still hiding dependencies, synchronization, and governance. The workflow therefore uses explicit non linear, stateful execution.

## Decision

Represent lifecycle stages as graph nodes with declared dependencies, optional conditions, retry budgets, fallback agents, mutation markers, and approval gate markers.

The scheduler repeatedly finds ready nodes. Independent ready nodes execute concurrently. A downstream node starts only when all dependencies have reached acceptable terminal states.

## Consequences

The execution model is inspectable and testable. Parallel work and synchronization are visible. Replanning can compute descendants and invalidate only affected downstream work.

The graph is currently static code. A larger platform could externalize graph definitions after schema validation and policy review.
