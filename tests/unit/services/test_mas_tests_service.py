from __future__ import annotations
import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

from app.agentic.eval_types import EvalResult
from app.api.services import mas_tests_service
from app.config import settings
from app.models.mas_test_case import MasTestCase
from app.models.mas_test_run import MasTestRun
from app.schemas.mas_tests import MasTestRunStartRequest


class _FakeEvaluator:
    def validate_expected(self, expected_json):
        return None

    def evaluate(self, expected_json, actual_json, *, swarm_status):
        return EvalResult(
            passed=swarm_status == "completed",
            score=1.0 if swarm_status == "completed" else 0.0,
            diff_json={},
            metrics_json={},
        )

    def aggregate(self, results):
        return {"passed": sum(1 for item in results if item.passed)}


def _seed_case(db_session, *, case_id: str = "case_1") -> MasTestCase:
    now = datetime.utcnow()
    case = MasTestCase(
        id=case_id,
        workflow_id="esi_swarm_v1",
        name="Case 1",
        enabled=True,
        input_json={"chiefcomplaint": "pain"},
        expected_json={"esi_level": 1},
        created_at=now,
        updated_at=now,
    )
    db_session.add(case)
    db_session.commit()
    return case


async def _collect_stream_chunks(response) -> list[str]:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode())
        else:
            chunks.append(chunk)
    return chunks

def test_ut_srv_003_mas_test_start_run_persists_selected_model(monkeypatch, db_session):
    case = _seed_case(db_session)
    monkeypatch.setattr(mas_tests_service, "_workflow_evaluator_or_400", lambda workflow_id: _FakeEvaluator())

    result = mas_tests_service.start_run(
        MasTestRunStartRequest(
            workflow_id="esi_swarm_v1",
            name="medgemma test",
            model_id="medgemma-4b-it",
            case_ids=[case.id],
        ),
        db_session,
    )

    persisted = db_session.get(MasTestRun, result.id)
    assert result.model_name == "medgemma-4b-it"
    assert persisted is not None
    assert persisted.model_name == "medgemma-4b-it"


def test_ut_srv_004_mas_test_resolve_model_prefers_persisted_value():
    run = MasTestRun(
        id="run_1",
        workflow_id="esi_swarm_v1",
        model_name="medgemma-4b-it",
        name="x",
        status="created",
        selected_case_ids_json=["case_1"],
        metrics_json=None,
        started_at=None,
        finished_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    assert mas_tests_service._resolve_test_run_model_id(run) == "medgemma-4b-it"


def test_ut_srv_005_mas_test_resolve_model_falls_back_to_default(monkeypatch):
    run = MasTestRun(
        id="run_2",
        workflow_id="esi_swarm_v1",
        model_name=None,
        name="x",
        status="created",
        selected_case_ids_json=["case_1"],
        metrics_json=None,
        started_at=None,
        finished_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    assert mas_tests_service._resolve_test_run_model_id(run) == "gpt-4o-mini"


def test_ut_srv_006_mas_test_stream_run_emits_case_backoff_and_sleeps(monkeypatch, db_session):
    case_1 = _seed_case(db_session, case_id="case_1")
    case_2 = _seed_case(db_session, case_id="case_2")
    monkeypatch.setattr(mas_tests_service, "_workflow_evaluator_or_400", lambda workflow_id: _FakeEvaluator())

    started = mas_tests_service.start_run(
        MasTestRunStartRequest(
            workflow_id="esi_swarm_v1",
            name="backoff test",
            model_id="medgemma-4b-it",
            case_ids=[case_1.id, case_2.id],
        ),
        db_session,
    )

    created_swarm_ids: list[str] = []
    sleep_calls: list[float] = []

    def _fake_create_and_start_swarm_run(*, workflow_id, input_payload, model_id, metadata):
        swarm_run_id = f"swarm_{len(created_swarm_ids) + 1}"
        created_swarm_ids.append(swarm_run_id)
        return swarm_run_id, input_payload, None, "1.0.0"

    async def _fake_execute_swarm_run(*, workflow_id, workflow_version, swarm_run_id, case_info, model_id):
        return None

    monkeypatch.setattr(mas_tests_service.swarm_execution_service, "create_and_start_swarm_run", _fake_create_and_start_swarm_run)
    monkeypatch.setattr(mas_tests_service.swarm_execution_service, "execute_swarm_run", _fake_execute_swarm_run)
    monkeypatch.setattr(mas_tests_service, "SessionLocal", lambda: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(
        mas_tests_service.swarm_runs_repository,
        "get_swarm_run",
        lambda db, swarm_run_id: SimpleNamespace(
            status="completed",
            duration_ms=1234,
            error_text=None,
            final_output_json={"acuity": "2"},
        ),
    )
    monkeypatch.setattr(
        mas_tests_service.swarm_final_outputs_repository,
        "get_latest_swarm_final_output_for_run",
        lambda db, swarm_run_id: None,
    )
    monkeypatch.setattr(settings, "MAS_TEST_CASE_BACKOFF_S", 7.0)
    monkeypatch.setattr("app.api.services.mas_tests_service.time.sleep", lambda seconds: sleep_calls.append(seconds))

    response = mas_tests_service.stream_run(started.id, db_session)
    chunks = asyncio.run(_collect_stream_chunks(response))
    events = [json.loads(line.removeprefix("data: ")) for chunk in chunks for line in chunk.splitlines() if line.startswith("data: ")]

    assert any(event.get("seconds") == 7.0 and event.get("next_index") == 1 for event in events)
    assert sleep_calls == [7.0]
