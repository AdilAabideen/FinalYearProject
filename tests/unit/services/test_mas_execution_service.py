"""Test Mas Execution Service service helpers."""

from __future__ import annotations

from fastapi import BackgroundTasks

from app.api.services import mas_execution_service
from app.config import settings
from app.schemas.mas_execution import MASExecutionStartRequest


def test_ut_srv_001_start_mas_execution_threads_explicit_model_id(monkeypatch):
    """Handle ut srv 001 start MAS execution threads explicit model id."""
    # Keep the main step clear.
    captured: dict[str, object] = {}

    def _fake_create_and_start_mas_run(*, workflow_id, input_payload, model_id, metadata=None):
        """Handle create and start MAS run."""
        # Keep the main step clear.
        captured["workflow_id"] = workflow_id
        captured["input_payload"] = input_payload
        captured["model_id"] = model_id
        captured["metadata"] = metadata
        return ("mas_1", {"chiefcomplaint": "pain"}, "schema", "v1")

    monkeypatch.setattr(
        mas_execution_service,
        "create_and_start_mas_run",
        _fake_create_and_start_mas_run,
    )

    response = mas_execution_service.start_mas_execution(
        workflow_id="esi_mas",
        payload=MASExecutionStartRequest(
            input={"chiefcomplaint": "pain"},
            model_id="medgemma-4b-it",
        ),
        background_tasks=BackgroundTasks(),
    )

    assert captured["model_id"] == "medgemma-4b-it"
    assert captured["metadata"] == {"source": "mas_execution_api"}
    assert response.model_id == "medgemma-4b-it"


def test_ut_srv_002_start_mas_execution_defaults_to_configured_model(monkeypatch):
    """Handle ut srv 002 start MAS execution defaults to configured model."""
    # Keep the main step clear.
    captured: dict[str, object] = {}

    def _fake_create_and_start_mas_run(*, workflow_id, input_payload, model_id, metadata=None):
        """Handle create and start MAS run."""
        # Keep the main step clear.
        captured["model_id"] = model_id
        return ("mas_2", {"chiefcomplaint": "pain"}, "schema", "v1")

    monkeypatch.setattr(
        mas_execution_service,
        "create_and_start_mas_run",
        _fake_create_and_start_mas_run,
    )
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    response = mas_execution_service.start_mas_execution(
        workflow_id="esi_mas",
        payload=MASExecutionStartRequest(input={"chiefcomplaint": "pain"}),
        background_tasks=BackgroundTasks(),
    )

    assert captured["model_id"] == "gpt-4o-mini"
    assert response.model_id == "gpt-4o-mini"
