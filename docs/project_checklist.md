# Project Verification Checklist

## Project deliverables

| Deliverable | Status | Evidence |
| --- | --- | --- |
| Runnable prototype | Complete | FastAPI service, Dockerfile, Docker Compose, tests |
| Architecture overview | Complete | `docs/architecture.md` |
| Greenfield scenario | Complete | `scenarios/greenfield.json`, `artifacts/demos/greenfield.json` |
| Brownfield scenario | Complete | `scenarios/brownfield.json`, `artifacts/demos/brownfield.json` |
| Ambiguous scenario | Complete | `scenarios/ambiguous.json`, `artifacts/demos/ambiguous.json` |
| Setup instructions | Complete | `README.md` |
| Testing approach | Complete | `docs/testing.md` |
| Limitations and tradeoffs | Complete | `docs/final_engineering_summary.md` |
| API schema | Complete | Runtime OpenAPI plus `docs/openapi.json` |
| CI | Complete | `.github/workflows/ci.yml` |
| Agentic orchestration | Complete | `src/urlshortener/orchestration/` |
| Human approvals | Complete | Clarification, high impact change, and release gates |
| Reliability metrics | Complete | `/api/v1/engineering/metrics`, demo `metrics.json` |
| Dynamic replan | Complete | `/api/v1/engineering/runs/{run_id}/replan` |

## Verification before sharing

Run `pytest --cov=urlshortener --cov-report=term-missing` and `ruff check src tests scripts` in a development environment with dependencies installed.

Run `python scripts/run_scenarios.py` and inspect the generated traces.

Confirm that no local environment files, secrets, credentials, database files, cache files, or confidential source documents are included in the repository.
