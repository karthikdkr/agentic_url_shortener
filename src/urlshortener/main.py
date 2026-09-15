from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .orchestration import InvalidApproval, Orchestrator, RunNotFound, WorkflowStore
from .rate_limit import SlidingWindowRateLimiter
from .schemas import (
    AnalyticsResponse,
    ApprovalRequest,
    CreateURLRequest,
    EngineeringRunRequest,
    ReplanRequest,
    URLResponse,
)
from .security import UnsafeURL
from .service import AliasConflict, URLNotFound, URLShortenerService, URLUnavailable


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agentic URL Shortener",
    version="1.0.0",
    description="URL shortener plus governed agentic SDLC orchestration prototype.",
)

limiter = SlidingWindowRateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)
workflow_store = WorkflowStore(settings.workflow_store_path)
orchestrator = Orchestrator(workflow_store, repo_root=Path.cwd())


def service(db: Session) -> URLShortenerService:
    return URLShortenerService(db, settings.base_url, settings.alias_length)


def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    return {"status": "ready"}


@app.post(
    "/api/v1/urls",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
)
def create_url(payload: CreateURLRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    svc = service(db)
    try:
        record = svc.create(str(payload.url), payload.custom_alias, payload.expires_in_days)
        return svc.response_payload(record)
    except AliasConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UnsafeURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/urls/{code}", response_model=URLResponse)
def get_url(code: str, db: Session = Depends(get_db)) -> dict[str, object]:
    svc = service(db)
    try:
        return svc.response_payload(svc.get(code))
    except URLNotFound as exc:
        raise HTTPException(status_code=404, detail="Short URL not found") from exc


@app.delete("/api/v1/urls/{code}", response_model=URLResponse)
def disable_url(code: str, db: Session = Depends(get_db)) -> dict[str, object]:
    svc = service(db)
    try:
        return svc.response_payload(svc.disable(code))
    except URLNotFound as exc:
        raise HTTPException(status_code=404, detail="Short URL not found") from exc


@app.get("/api/v1/urls/{code}/analytics", response_model=AnalyticsResponse)
def get_analytics(code: str, db: Session = Depends(get_db)) -> dict[str, object]:
    svc = service(db)
    try:
        return svc.analytics(code)
    except URLNotFound as exc:
        raise HTTPException(status_code=404, detail="Short URL not found") from exc


@app.post("/api/v1/engineering/runs", status_code=status.HTTP_201_CREATED)
async def start_engineering_run(payload: EngineeringRunRequest) -> dict:
    run = await orchestrator.start(payload.requirement, payload.scenario_type, payload.metadata)
    return run.model_dump(mode="json")


@app.get("/api/v1/engineering/runs/{run_id}")
def get_engineering_run(run_id: str) -> dict:
    try:
        return orchestrator.get(run_id).model_dump(mode="json")
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="Engineering run not found") from exc


@app.post("/api/v1/engineering/runs/{run_id}/approvals/{node_id}")
async def approve_engineering_gate(
    run_id: str,
    node_id: str,
    payload: ApprovalRequest,
) -> dict:
    try:
        run = await orchestrator.approve(
            run_id,
            node_id,
            payload.approved,
            payload.reviewer,
            payload.note,
            payload.payload,
        )
        return run.model_dump(mode="json")
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="Engineering run not found") from exc
    except InvalidApproval as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/engineering/runs/{run_id}/replan")
async def replan_engineering_run(run_id: str, payload: ReplanRequest) -> dict:
    try:
        run = await orchestrator.replan(run_id, payload.changed_requirement, payload.reason)
        return run.model_dump(mode="json")
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="Engineering run not found") from exc


@app.get("/api/v1/engineering/metrics")
def engineering_metrics() -> dict:
    return orchestrator.metrics()


@app.get("/{code}", include_in_schema=False)
def redirect(code: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    svc = service(db)
    try:
        target = svc.resolve(code, request.headers.get("referer"), request.headers.get("user-agent"))
        return RedirectResponse(target, status_code=307)
    except URLNotFound as exc:
        raise HTTPException(status_code=404, detail="Short URL not found") from exc
    except URLUnavailable as exc:
        raise HTTPException(status_code=410, detail="Short URL is disabled or expired") from exc
