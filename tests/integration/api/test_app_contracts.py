from __future__ import annotations

from datetime import datetime

import pytest

from app.api.repository import agent_metrics_repository, agent_runs_repository
from app.models.agent_run import AgentRun


def _seed_run(db_session):
    run = AgentRun(
        id="run_1",
        agent_name="vitals_agent",
        model_name="gpt-4o-mini",
        status="succeeded",
        input_json={"input": "x"},
        output_json={"ok": True},
        error_text=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        started_at=None,
        finished_at=None,
    )
    agent_runs_repository.save_run(db_session, run)
    agent_runs_repository.append_event(
        db_session,
        run_id="run_1",
        agent_name="vitals_agent",
        seq=1,
        event_type="assistant",
        payload_json={"ok": True},
        created_at=datetime.utcnow(),
    )
    agent_metrics_repository.upsert_run_metrics(
        db_session,
        run_id="run_1",
        agent_system="handrolled",
        agent_name="vitals_agent",
        model_name="gpt-4o-mini",
        status="succeeded",
        failure_reason=None,
        duration_ms=5,
        llm_call_count=1,
        tool_call_count=0,
        tool_error_count=0,
        reliability_issue_count=0,
        reliability_error_count=0,
        finalization_failure_count=0,
        tool_recovery_failure_count=0,
        input_tokens_total=1,
        output_tokens_total=1,
        tokens_total=2,
        cost_usd_total=None,
        schema_valid=True,
    )


@pytest.mark.integration
@pytest.mark.api
def test_it_api_001_root_returns_welcome_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]


@pytest.mark.integration
@pytest.mark.api
def test_it_api_002_health_returns_healthy_status(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.integration
@pytest.mark.api
def test_it_api_003_get_models_returns_registered_models(client):
    response = client.get("/api/models")
    assert response.status_code == 200
    assert any(item["id"] == "gpt-4o-mini" for item in response.json())


@pytest.mark.integration
@pytest.mark.api
def test_it_api_004_get_model_by_id_returns_one_model(client):
    response = client.get("/api/models/gpt-4o-mini")
    assert response.status_code == 200
    assert response.json()["id"] == "gpt-4o-mini"


@pytest.mark.integration
@pytest.mark.api
def test_it_api_005_unknown_model_returns_404(client):
    response = client.get("/api/models/does-not-exist")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
def test_it_api_006_list_agent_runs_supports_filters(client, db_session):
    _seed_run(db_session)
    response = client.get("/api/agent-runs", params={"agent_name": "vitals_agent"})
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.integration
@pytest.mark.api
def test_it_api_007_get_agent_run_returns_persisted_output(client, db_session):
    _seed_run(db_session)
    response = client.get("/api/agent-runs/run_1")
    assert response.status_code == 200
    assert response.json()["output_json"] == {"ok": True}


@pytest.mark.integration
@pytest.mark.api
def test_it_api_008_get_agent_run_metrics_returns_llm_and_tool_call_lists(client, db_session):
    _seed_run(db_session)
    response = client.get("/api/agent-runs/run_1/metrics")
    assert response.status_code == 200
    assert response.json()["metrics"]["llm_call_count"] == 1


@pytest.mark.integration
@pytest.mark.api
def test_it_api_009_list_events_paginates_by_after_seq(client, db_session):
    _seed_run(db_session)
    response = client.get("/api/agent-runs/run_1/events", params={"after_seq": 0, "limit": 10})
    assert response.status_code == 200
    assert response.json()["events"][0]["seq"] == 1
