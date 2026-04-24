from __future__ import annotations

from datetime import datetime

import pytest

from app.api.repository import agent_metrics_repository, agent_runs_repository
from app.models.agent_run import AgentRun


@pytest.mark.integration
@pytest.mark.db
def test_it_db_001_get_last_event_seq_returns_zero_when_none_exist(db_session):
    assert agent_runs_repository.get_last_event_seq(db_session, "missing") == 0


@pytest.mark.integration
@pytest.mark.db
def test_it_db_002_save_and_reload_agent_run(db_session):
    run = AgentRun(
        id="run_1",
        agent_name="vitals_agent",
        model_name="gpt-4o-mini",
        status="created",
        input_json={"input": "x"},
        output_json=None,
        error_text=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        started_at=None,
        finished_at=None,
    )
    agent_runs_repository.save_run(db_session, run, refresh=True)
    loaded = agent_runs_repository.get_run(db_session, "run_1")
    assert loaded is not None
    assert loaded.agent_name == "vitals_agent"


@pytest.mark.integration
@pytest.mark.db
def test_it_db_003_list_runs_filters_by_agent_name(db_session):
    for idx, agent_name in enumerate(["a", "b"]):
        agent_runs_repository.save_run(
            db_session,
                AgentRun(
                    id=f"run_{idx}",
                    agent_name=agent_name,
                    model_name="m",
                    status="created",
                input_json={},
                output_json=None,
                error_text=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                started_at=None,
                finished_at=None,
            ),
        )
    rows = agent_runs_repository.list_runs(db_session, agent_name="a", status=None, limit=10, offset=0, order="desc")
    assert [row.agent_name for row in rows] == ["a"]


@pytest.mark.integration
@pytest.mark.db
def test_it_db_004_append_event_persists_sequence_ordering(db_session):
    agent_runs_repository.append_event(
        db_session,
        run_id="run_1",
        agent_name="vitals_agent",
        seq=1,
        event_type="assistant",
        created_at=datetime.utcnow(),
    )
    agent_runs_repository.append_event(
        db_session,
        run_id="run_1",
        agent_name="vitals_agent",
        seq=2,
        event_type="tool_call",
        created_at=datetime.utcnow(),
    )
    rows = agent_runs_repository.list_events_after(db_session, run_id="run_1", after_seq=0, limit=10)
    assert [row.seq for row in rows] == [1, 2]


@pytest.mark.integration
@pytest.mark.db
def test_it_db_005_append_llm_call_persists_normalized_counts(db_session):
    agent_metrics_repository.append_llm_call(
        db_session,
        run_id="run_1",
        call_index=1,
        agent_system="handrolled",
        agent_name="vitals_agent",
        model_name="gpt-4o-mini",
        call_kind="main_loop",
        iteration=1,
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
        latency_ms=10,
        input_tokens=1,
        output_tokens=2,
        tokens_total=3,
        usage_source="estimated",
        cost_usd=None,
        had_tool_calls=True,
        tool_call_count=2,
        tool_call_parse_source="native_tool_calls",
        text_recovered_tool_call_count=1,
        native_tool_call_count=1,
        tool_names=["a", "b"],
    )
    row = agent_metrics_repository.list_llm_calls(db_session, "run_1")[0]
    assert row.tool_call_count == 2
    assert row.text_recovered_tool_call_count == 1


@pytest.mark.integration
@pytest.mark.db
def test_it_db_006_append_tool_call_persists_status_and_latency(db_session):
    agent_metrics_repository.append_tool_call(
        db_session,
        run_id="run_1",
        agent_name="vitals_agent",
        iteration=1,
        tool_call_id="call_1",
        tool_name="tool_a",
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
        latency_ms=15,
        status="success",
        result_char_count=10,
        result_estimated_tokens=2,
    )
    row = agent_metrics_repository.list_tool_calls(db_session, "run_1")[0]
    assert row.status == "success"
    assert row.latency_ms == 15


@pytest.mark.integration
@pytest.mark.db
def test_it_db_007_upsert_metrics_inserts_then_updates_same_row(db_session):
    agent_metrics_repository.upsert_run_metrics(
        db_session,
        run_id="run_1",
        agent_system="handrolled",
        agent_name="vitals_agent",
        model_name="gpt-4o-mini",
        status="created",
        failure_reason=None,
        duration_ms=1,
        llm_call_count=1,
        tool_call_count=1,
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
    agent_metrics_repository.upsert_run_metrics(
        db_session,
        run_id="run_1",
        agent_system="handrolled",
        agent_name="vitals_agent",
        model_name="gpt-4o-mini",
        status="succeeded",
        failure_reason=None,
        duration_ms=2,
        llm_call_count=2,
        tool_call_count=1,
        tool_error_count=0,
        reliability_issue_count=1,
        reliability_error_count=0,
        finalization_failure_count=0,
        tool_recovery_failure_count=0,
        input_tokens_total=2,
        output_tokens_total=2,
        tokens_total=4,
        cost_usd_total=None,
        schema_valid=True,
    )
    row = agent_metrics_repository.get_run_metrics(db_session, "run_1")
    assert row.status == "succeeded"
    assert row.llm_call_count == 2
