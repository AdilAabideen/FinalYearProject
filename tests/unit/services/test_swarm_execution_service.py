from __future__ import annotations

from fastapi import BackgroundTasks

from app.api.services import swarm_execution_service
from app.config import settings
from app.schemas.swarm_execution import SwarmExecutionStartRequest


def test_ut_srv_001_start_swarm_execution_threads_explicit_model_id(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_create_and_start_swarm_run(*, workflow_id, input_payload, model_id, metadata=None):
        captured["workflow_id"] = workflow_id
        captured["input_payload"] = input_payload
        captured["model_id"] = model_id
        captured["metadata"] = metadata
        return ("swarm_1", {"chiefcomplaint": "pain"}, "schema", "v1")

    monkeypatch.setattr(
        swarm_execution_service,
        "create_and_start_swarm_run",
        _fake_create_and_start_swarm_run,
    )

    response = swarm_execution_service.start_swarm_execution(
        workflow_id="esi_swarm_v1",
        payload=SwarmExecutionStartRequest(
            input={"chiefcomplaint": "pain"},
            model_id="medgemma-4b-it",
        ),
        background_tasks=BackgroundTasks(),
    )

    assert captured["model_id"] == "medgemma-4b-it"
    assert captured["metadata"] == {"source": "mas_execution_api"}
    assert response.model_id == "medgemma-4b-it"


def test_ut_srv_002_start_swarm_execution_defaults_to_configured_model(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_create_and_start_swarm_run(*, workflow_id, input_payload, model_id, metadata=None):
        captured["model_id"] = model_id
        return ("swarm_2", {"chiefcomplaint": "pain"}, "schema", "v1")

    monkeypatch.setattr(
        swarm_execution_service,
        "create_and_start_swarm_run",
        _fake_create_and_start_swarm_run,
    )
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    response = swarm_execution_service.start_swarm_execution(
        workflow_id="esi_swarm_v1",
        payload=SwarmExecutionStartRequest(input={"chiefcomplaint": "pain"}),
        background_tasks=BackgroundTasks(),
    )

    assert captured["model_id"] == "gpt-4o-mini"
    assert response.model_id == "gpt-4o-mini"
