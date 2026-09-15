# ADR 0002: Default to Reproducible Local Agents

## Status

Accepted.

## Context

The workflow should remain runnable without external service credentials, network access, or nondeterministic provider behavior. The orchestration design still needs clear agent boundaries.

## Decision

Use deterministic stage agents behind an `Agent` interface. Keep orchestration independent from agent implementation details.

## Consequences

The repository is fully runnable offline and demo outputs are reproducible. Governance behavior can be tested deterministically.

The default runtime has less open ended generation capability than more advanced agent implementations. Alternate agents can be added later without changing dependency gates, output validation, policy checks, retries, approvals, or audit behavior.
