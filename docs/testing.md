# Testing Approach

## Test pyramid

The repository keeps most tests at the service and orchestration layers where failures are fast to diagnose. API tests then cover end to end behavior through FastAPI.

### URL service tests

`tests/test_service.py` covers custom aliases, duplicate conflicts, click analytics, expiration, and idempotent disable behavior.

### API tests

`tests/test_api.py` covers create, redirect, analytics, input validation, disable, and gone behavior.

### Orchestration tests

`tests/test_orchestrator.py` covers:

* Greenfield execution through release approval and final completion
* Ambiguous requirement safe pause at clarification
* Bounded retry and recovery
* Dynamic replanning and plan version changes
* Human rejection producing a safe stop

## Validation philosophy

A stage succeeding is not enough. The orchestrator checks a stage specific output contract before accepting artifacts. Policy scanning occurs before an artifact becomes authoritative. Downstream nodes cannot execute until dependencies have acceptable terminal states.

## CI

GitHub Actions runs Ruff and pytest on Python 3.11 and 3.12. Coverage is printed to the job output.

## Known limitations

The demo stage agents report repository test evidence rather than launching nested test processes from inside the workflow. This avoids an agent recursively changing or executing the host repository during an API request. The repository CI is the authoritative executable quality gate.

The state store is safe for a single process but is not a distributed transaction system. The rate limiter is similarly process local.

The security policy engine is intentionally small. It demonstrates the enforcement point rather than attempting to replace enterprise SAST, dependency scanning, secrets scanning, or policy as code.
