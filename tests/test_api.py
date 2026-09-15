from __future__ import annotations


def test_create_redirect_and_analytics(client):
    response = client.post(
        "/api/v1/urls",
        json={"url": "https://example.com/docs", "custom_alias": "docs123"},
    )
    assert response.status_code == 201
    assert response.json()["code"] == "docs123"

    redirect = client.get(
        "/docs123",
        headers={"referer": "https://search.example/query", "user-agent": "curl/8"},
        follow_redirects=False,
    )
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/docs"

    analytics = client.get("/api/v1/urls/docs123/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["total_clicks"] == 1


def test_invalid_alias_is_rejected(client):
    response = client.post(
        "/api/v1/urls",
        json={"url": "https://example.com", "custom_alias": "bad alias"},
    )
    assert response.status_code == 422


def test_disable_changes_redirect_to_gone(client):
    client.post(
        "/api/v1/urls",
        json={"url": "https://example.com", "custom_alias": "gone123"},
    )
    disabled = client.delete("/api/v1/urls/gone123")
    assert disabled.status_code == 200
    assert disabled.json()["disabled"] is True
    redirect = client.get("/gone123", follow_redirects=False)
    assert redirect.status_code == 410


def test_engineering_api_lifecycle(client, tmp_path, monkeypatch):
    import urlshortener.main as main_module
    from urlshortener.orchestration.orchestrator import Orchestrator
    from urlshortener.orchestration.store import WorkflowStore

    replacement = Orchestrator(
        WorkflowStore(str(tmp_path / "api_runs.json")),
        repo_root=tmp_path,
    )
    monkeypatch.setattr(main_module, "orchestrator", replacement)

    started = client.post(
        "/api/v1/engineering/runs",
        json={
            "requirement": "Add expiration support with tests and documentation",
            "scenario_type": "greenfield",
        },
    )
    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "waiting_approval"
    assert body["nodes"]["release_approval"]["status"] == "waiting_approval"

    approved = client.post(
        f"/api/v1/engineering/runs/{body['id']}/approvals/release_approval",
        json={
            "approved": True,
            "reviewer": "api_reviewer",
            "note": "Reviewed",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
