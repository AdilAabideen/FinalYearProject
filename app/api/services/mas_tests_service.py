from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agentic.eval_types import EvalResult
from app.agentic.model_registry import validate_model_for_agent
from app.agentic.workflows.registry import get_workflow_definition, get_workflow_spec, list_workflow_specs
from app.api.repository import (
    mas_tests_repository,
    mas_final_outputs_repository,
    mas_run_metrics_repository,
    mas_runs_repository,
)
from app.api.services import mas_execution_service
from app.api.services.mas_run_metrics_service import TERMINAL_MAS_STATUSES, persist_mas_run_metrics
from app.config import settings
from app.database import SessionLocal
from app.models.mas_test_case import MasTestCase
from app.models.mas_test_case_run import MasTestCaseRun
from app.models.mas_test_run import MasTestRun
from app.schemas.mas_tests import (
    MasTestCaseAnalyticsRead,
    MasTestCaseCreateRequest,
    MasTestCaseRead,
    MasTestCaseRunMetricRead,
    MasTestCaseRunRead,
    MasTestCaseUpdateRequest,
    MasTestRunAnalyticsRead,
    MasTestRunAnalyticsSummaryRead,
    MasTestRunBatchMetricsRead,
    MasTestRunDetailRead,
    MasTestRunMetricsSummaryRead,
    MasTestRunRead,
    MasTestRunStartRequest,
)


def _workflow_spec_or_400(workflow_id: str):
    try:
        return get_workflow_spec(workflow_id)
    except ValueError:
        supported = sorted(spec.workflow_id for spec in list_workflow_specs())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported workflow_id '{workflow_id}'. Supported: {supported}",
        )


def _workflow_evaluator_or_400(workflow_id: str):
    spec = _workflow_spec_or_400(workflow_id)
    if spec.test_evaluator is None:
        raise HTTPException(
            status_code=400,
            detail=f"No MAS test evaluator configured for workflow_id '{workflow_id}'",
        )
    return spec.test_evaluator


def _validate_case_payload_or_400(
    *,
    workflow_id: str,
    input_json: dict[str, Any],
    expected_json: dict[str, Any],
) -> None:
    evaluator = _workflow_evaluator_or_400(workflow_id)
    try:
        evaluator.validate_expected(expected_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _normalize_runtime_input_or_400(
    *,
    workflow_id: str,
    input_json: dict[str, Any],
) -> dict[str, Any]:
    candidate = dict(input_json)
    if "gender" not in candidate and "der" in candidate:
        candidate["gender"] = candidate["der"]
    if "heartrate" not in candidate and "heartte" in candidate:
        candidate["heartrate"] = candidate["heartte"]
    if "arrival_transport" not in candidate and "rival_transport" in candidate:
        candidate["arrival_transport"] = candidate["rival_transport"]
    normalized_input, _, _ = mas_execution_service.normalize_workflow_input(workflow_id, candidate)
    return normalized_input


def _resolve_test_run_model_id(run: MasTestRun) -> str:
    return run.model_name or settings.OPENAI_MODEL


def _build_case_diff_payload(
    *,
    expected_answer: dict[str, Any],
    actual_answer: Optional[dict[str, Any]],
    mas_status: str,
    passed: bool,
    evaluator_diff: Optional[dict[str, Any]],
    error_text: Optional[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "expected_answer": expected_answer,
        "actual_answer": actual_answer,
        "mas_status": mas_status,
        "passed": passed,
    }
    if error_text:
        payload["mas_error_text"] = error_text
    if isinstance(evaluator_diff, dict):
        payload.update(evaluator_diff)
    return payload


def _stream_legacy_swarm_diff_payload(payload: dict[str, Any]) -> dict[str, Any]:
    legacy = dict(payload)
    if "mas_status" in legacy:
        legacy["swarm_status"] = legacy.pop("mas_status")
    if "mas_error_text" in legacy:
        legacy["swarm_error_text"] = legacy.pop("mas_error_text")
    return legacy


def _avg_or_none(total: float, count: int, ndigits: int = 4) -> Optional[float]:
    if count <= 0:
        return None
    return round(total / count, ndigits)


def list_cases(
    *,
    workflow_id: Optional[str],
    enabled: Optional[bool],
    limit: int,
    offset: int,
    order: str,
    db: Session,
) -> list[MasTestCaseRead]:
    rows = mas_tests_repository.list_test_cases(
        db,
        workflow_id=workflow_id,
        enabled=enabled,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [MasTestCaseRead.model_validate(row.__dict__) for row in rows]


def create_case(payload: MasTestCaseCreateRequest, db: Session) -> MasTestCaseRead:
    _validate_case_payload_or_400(
        workflow_id=payload.workflow_id,
        input_json=payload.input_json,
        expected_json=payload.expected_json,
    )
    _normalize_runtime_input_or_400(
        workflow_id=payload.workflow_id,
        input_json=payload.input_json,
    )

    now = datetime.utcnow()
    row = MasTestCase(
        id=str(uuid.uuid4()),
        workflow_id=payload.workflow_id,
        name=payload.name,
        enabled=payload.enabled,
        input_json=payload.input_json,
        expected_json=payload.expected_json,
        created_at=now,
        updated_at=now,
    )
    mas_tests_repository.save_test_case(db, row, refresh=True)
    return MasTestCaseRead.model_validate(row.__dict__)


def update_case(
    case_id: str,
    payload: MasTestCaseUpdateRequest,
    db: Session,
) -> MasTestCaseRead:
    row = mas_tests_repository.get_test_case(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Test case not found")

    workflow_id = payload.workflow_id or row.workflow_id
    input_json = payload.input_json if payload.input_json is not None else row.input_json
    expected_json = payload.expected_json if payload.expected_json is not None else row.expected_json

    _validate_case_payload_or_400(
        workflow_id=workflow_id,
        input_json=input_json,
        expected_json=expected_json,
    )
    _normalize_runtime_input_or_400(
        workflow_id=workflow_id,
        input_json=input_json,
    )

    row.workflow_id = workflow_id
    row.input_json = input_json
    row.expected_json = expected_json
    if payload.name is not None:
        row.name = payload.name
    if payload.enabled is not None:
        row.enabled = payload.enabled
    row.updated_at = datetime.utcnow()
    mas_tests_repository.save_test_case(db, row, refresh=True)
    return MasTestCaseRead.model_validate(row.__dict__)


def delete_case(case_id: str, db: Session) -> None:
    row = mas_tests_repository.get_test_case(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    row.enabled = False
    row.updated_at = datetime.utcnow()
    mas_tests_repository.save_test_case(db, row)


def start_run(payload: MasTestRunStartRequest, db: Session) -> MasTestRunRead:
    if not payload.case_ids:
        raise HTTPException(status_code=400, detail="case_ids must be non-empty")

    _workflow_evaluator_or_400(payload.workflow_id)
    workflow = get_workflow_definition(payload.workflow_id)
    model_id = payload.model_id or settings.OPENAI_MODEL
    for agent_name in workflow.participating_agents:
        validate_model_for_agent(
            model_id=model_id,
            agent_name=agent_name,
            requires_tools=True,
        )

    cases = mas_tests_repository.get_test_cases_by_ids(db, payload.case_ids)
    case_by_id = {case.id: case for case in cases}
    missing = [case_id for case_id in payload.case_ids if case_id not in case_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown test case ids: {missing}")

    wrong_workflow = [case.id for case in cases if case.workflow_id != payload.workflow_id]
    if wrong_workflow:
        raise HTTPException(status_code=400, detail=f"Test cases do not match workflow_id: {wrong_workflow}")

    disabled = [case.id for case in cases if not case.enabled]
    if disabled:
        raise HTTPException(status_code=400, detail=f"Selected test cases are disabled: {disabled}")

    evaluator = _workflow_evaluator_or_400(payload.workflow_id)
    for case in cases:
        try:
            evaluator.validate_expected(case.expected_json)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid expected_json for case_id={case.id}: {exc}") from exc

    now = datetime.utcnow()
    run_id = str(uuid.uuid4())
    run = MasTestRun(
        id=run_id,
        workflow_id=payload.workflow_id,
        model_name=model_id,
        name=payload.name,
        status="created",
        selected_case_ids_json=payload.case_ids,
        metrics_json=None,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    case_runs = [
        MasTestCaseRun(
            id=str(uuid.uuid4()),
            test_run_id=run_id,
            test_case_id=case_id,
            mas_run_id=None,
            status="created",
            passed=None,
            score=None,
            diff_json=None,
            metrics_json=None,
            error_text=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )
        for case_id in payload.case_ids
    ]
    mas_tests_repository.create_test_run_with_case_runs(db, run, case_runs)
    return MasTestRunRead.model_validate(run.__dict__)


def list_runs(
    *,
    workflow_id: Optional[str],
    limit: int,
    offset: int,
    order: str,
    db: Session,
) -> list[MasTestRunRead]:
    rows = mas_tests_repository.list_test_runs(
        db,
        workflow_id=workflow_id,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [MasTestRunRead.model_validate(row.__dict__) for row in rows]


def get_run(run_id: str, db: Session) -> MasTestRunDetailRead:
    run = mas_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    case_runs = mas_tests_repository.get_case_runs_for_test_run(db, run_id)
    by_case_id = {case_run.test_case_id: case_run for case_run in case_runs}
    ordered = [by_case_id[case_id] for case_id in run.selected_case_ids_json if case_id in by_case_id]
    return MasTestRunDetailRead(
        run=MasTestRunRead.model_validate(run.__dict__),
        case_runs=[MasTestCaseRunRead.model_validate(case_run.__dict__) for case_run in ordered],
    )


def get_run_metrics(run_id: str, db: Session) -> MasTestRunBatchMetricsRead:
    run = mas_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    case_runs = mas_tests_repository.get_case_runs_for_test_run(db, run_id)
    by_case_id = {case_run.test_case_id: case_run for case_run in case_runs}
    ordered = [by_case_id[case_id] for case_id in run.selected_case_ids_json if case_id in by_case_id]

    case_ids = [case_run.test_case_id for case_run in ordered]
    case_rows = mas_tests_repository.get_test_cases_by_ids(db, case_ids) if case_ids else []
    case_name_by_id = {case.id: case.name for case in case_rows}

    successful_runs = 0
    failed_runs = 0
    execution_failed_count = 0
    missing_final_output_count = 0
    duration_ms_total = 0
    duration_count = 0
    case_metrics: list[MasTestCaseRunMetricRead] = []

    for case_run in ordered:
        metrics = dict(case_run.metrics_json or {})
        if case_run.passed is True:
            successful_runs += 1
        elif case_run.status == "failed":
            failed_runs += 1
        if metrics.get("exec_failed") is True:
            execution_failed_count += 1
        if metrics.get("missing_final_output") is True:
            missing_final_output_count += 1
        duration_ms = metrics.get("duration_ms")
        if isinstance(duration_ms, int):
            duration_ms_total += duration_ms
            duration_count += 1

        case_metrics.append(
            MasTestCaseRunMetricRead(
                test_case_id=case_run.test_case_id,
                test_case_name=case_name_by_id.get(case_run.test_case_id),
                mas_run_id=case_run.mas_run_id,
                status=case_run.status,
                passed=case_run.passed,
                score=case_run.score,
                failure_reason=metrics.get("failure_reason"),
                mas_status=metrics.get("mas_status"),
                duration_ms=duration_ms if isinstance(duration_ms, int) else None,
            )
        )

    total_runs = len(ordered)
    runs_with_mas_run = len([case_run for case_run in ordered if case_run.mas_run_id])
    success_rate = round((successful_runs / total_runs), 4) if total_runs else 0.0

    summary = MasTestRunMetricsSummaryRead(
        total_runs=total_runs,
        runs_with_mas_run=runs_with_mas_run,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        execution_failed_count=execution_failed_count,
        missing_final_output_count=missing_final_output_count,
        duration_ms_total=duration_ms_total,
        duration_ms_avg=_avg_or_none(duration_ms_total, duration_count),
    )

    return MasTestRunBatchMetricsRead(
        run=MasTestRunRead.model_validate(run.__dict__),
        summary=summary,
        cases=case_metrics,
    )


def get_run_analytics(run_id: str, db: Session) -> MasTestRunAnalyticsRead:
    run = mas_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    case_runs = mas_tests_repository.get_case_runs_for_test_run(db, run_id)
    by_case_id = {case_run.test_case_id: case_run for case_run in case_runs}
    ordered = [by_case_id[case_id] for case_id in run.selected_case_ids_json if case_id in by_case_id]

    case_ids = [case_run.test_case_id for case_run in ordered]
    case_rows = mas_tests_repository.get_test_cases_by_ids(db, case_ids) if case_ids else []
    case_name_by_id = {case.id: case.name for case in case_rows}

    analytics_cases: list[MasTestCaseAnalyticsRead] = []
    metric_count = 0
    duration_ms_total = 0
    agent_run_count_total = 0
    handoff_count_total = 0
    gate_evaluation_count_total = 0
    input_tokens_total = 0
    output_tokens_total = 0
    tokens_total = 0
    llm_call_count_total = 0
    tool_call_count_total = 0
    tool_error_count_total = 0
    cost_usd_values: list[float] = []
    reliability_issue_count_total = 0
    reliability_error_count_total = 0
    finalization_failure_count_total = 0

    for case_run in ordered:
        mas_status = None
        duration_ms = None
        metrics_row = None

        if case_run.mas_run_id:
            mas_run = mas_runs_repository.get_mas_run(db, case_run.mas_run_id)
            if mas_run is not None:
                mas_status = mas_run.status
                if mas_run.status in TERMINAL_MAS_STATUSES:
                    persist_mas_run_metrics(case_run.mas_run_id)
            metrics_row = mas_run_metrics_repository.get_mas_run_metrics(db, case_run.mas_run_id)

        if metrics_row is not None:
            metric_count += 1
            duration_ms = metrics_row.duration_ms
            duration_ms_total += int(metrics_row.duration_ms or 0)
            agent_run_count_total += int(metrics_row.agent_run_count or 0)
            handoff_count_total += int(metrics_row.handoff_count or 0)
            gate_evaluation_count_total += int(metrics_row.gate_evaluation_count or 0)
            input_tokens_total += int(metrics_row.input_tokens_total or 0)
            output_tokens_total += int(metrics_row.output_tokens_total or 0)
            tokens_total += int(metrics_row.tokens_total or 0)
            llm_call_count_total += int(metrics_row.llm_call_count_total or 0)
            tool_call_count_total += int(metrics_row.tool_call_count_total or 0)
            tool_error_count_total += int(metrics_row.tool_error_count_total or 0)
            if metrics_row.cost_usd_total is not None:
                cost_usd_values.append(float(metrics_row.cost_usd_total))
            reliability_issue_count_total += int(metrics_row.reliability_issue_count or 0)
            reliability_error_count_total += int(metrics_row.reliability_error_count or 0)
            finalization_failure_count_total += int(metrics_row.finalization_failure_count or 0)

        analytics_cases.append(
            MasTestCaseAnalyticsRead(
                test_case_id=case_run.test_case_id,
                test_case_name=case_name_by_id.get(case_run.test_case_id),
                mas_run_id=case_run.mas_run_id,
                mas_status=mas_status,
                duration_ms=(metrics_row.duration_ms if metrics_row is not None else None),
                agent_run_count=(metrics_row.agent_run_count if metrics_row is not None else None),
                handoff_count=(metrics_row.handoff_count if metrics_row is not None else None),
                gate_evaluation_count=(metrics_row.gate_evaluation_count if metrics_row is not None else None),
                input_tokens_total=(int(metrics_row.input_tokens_total or 0) if metrics_row is not None else 0),
                output_tokens_total=(int(metrics_row.output_tokens_total or 0) if metrics_row is not None else 0),
                tokens_total=(int(metrics_row.tokens_total or 0) if metrics_row is not None else 0),
                llm_call_count_total=(int(metrics_row.llm_call_count_total or 0) if metrics_row is not None else 0),
                tool_call_count_total=(int(metrics_row.tool_call_count_total or 0) if metrics_row is not None else 0),
                tool_error_count_total=(int(metrics_row.tool_error_count_total or 0) if metrics_row is not None else 0),
                cost_usd_total=(metrics_row.cost_usd_total if metrics_row is not None else None),
                cost_usd_per_agent_run=(metrics_row.cost_usd_per_agent_run if metrics_row is not None else None),
                reliability_issue_count=(int(metrics_row.reliability_issue_count or 0) if metrics_row is not None else 0),
                reliability_error_count=(int(metrics_row.reliability_error_count or 0) if metrics_row is not None else 0),
                finalization_failure_count=(
                    int(metrics_row.finalization_failure_count or 0) if metrics_row is not None else 0
                ),
            )
        )

    cost_usd_total = sum(cost_usd_values) if cost_usd_values else None
    case_count = len(ordered)
    summary = MasTestRunAnalyticsSummaryRead(
        total_cases=case_count,
        cases_with_mas_run=len([case_run for case_run in ordered if case_run.mas_run_id]),
        cases_with_metrics=metric_count,
        duration_ms_total=duration_ms_total,
        duration_ms_avg=_avg_or_none(duration_ms_total, metric_count),
        agent_run_count_total=agent_run_count_total,
        agent_run_count_avg=_avg_or_none(agent_run_count_total, metric_count),
        handoff_count_total=handoff_count_total,
        handoff_count_avg=_avg_or_none(handoff_count_total, metric_count),
        gate_evaluation_count_total=gate_evaluation_count_total,
        gate_evaluation_count_avg=_avg_or_none(gate_evaluation_count_total, metric_count),
        input_tokens_total=input_tokens_total,
        input_tokens_avg=_avg_or_none(input_tokens_total, metric_count),
        output_tokens_total=output_tokens_total,
        output_tokens_avg=_avg_or_none(output_tokens_total, metric_count),
        tokens_total=tokens_total,
        tokens_avg=_avg_or_none(tokens_total, metric_count),
        llm_call_count_total=llm_call_count_total,
        llm_call_count_avg=_avg_or_none(llm_call_count_total, metric_count),
        tool_call_count_total=tool_call_count_total,
        tool_call_count_avg=_avg_or_none(tool_call_count_total, metric_count),
        tool_error_count_total=tool_error_count_total,
        tool_error_count_avg=_avg_or_none(tool_error_count_total, metric_count),
        cost_usd_total=round(cost_usd_total, 6) if cost_usd_total is not None else None,
        cost_usd_avg=_avg_or_none(cost_usd_total or 0.0, len(cost_usd_values), ndigits=6) if cost_usd_values else None,
        reliability_issue_count_total=reliability_issue_count_total,
        reliability_issue_count_avg=_avg_or_none(reliability_issue_count_total, metric_count),
        reliability_error_count_total=reliability_error_count_total,
        reliability_error_count_avg=_avg_or_none(reliability_error_count_total, metric_count),
        finalization_failure_count_total=finalization_failure_count_total,
        finalization_failure_count_avg=_avg_or_none(finalization_failure_count_total, metric_count),
    )

    return MasTestRunAnalyticsRead(
        run=MasTestRunRead.model_validate(run.__dict__),
        summary=summary,
        cases=analytics_cases,
    )


def stream_run(run_id: str, db: Session) -> StreamingResponse:
    run = mas_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    if run.status == "running":
        raise HTTPException(status_code=409, detail="Test run is already running")
    if run.status in {"succeeded", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail=f"Test run is already {run.status}")

    cases = mas_tests_repository.get_test_cases_by_ids(db, run.selected_case_ids_json)
    case_by_id = {case.id: case for case in cases}
    missing = [case_id for case_id in run.selected_case_ids_json if case_id not in case_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing test cases for run: {missing}")

    case_runs_by_case_id = mas_tests_repository.get_case_runs_by_case_id(db, run_id)
    evaluator = _workflow_evaluator_or_400(run.workflow_id)
    for case in cases:
        _validate_case_payload_or_400(
            workflow_id=case.workflow_id,
            input_json=case.input_json,
            expected_json=case.expected_json,
        )

    def _sse(event: str, data: dict[str, Any], event_id: Optional[int] = None) -> str:
        payload = json.dumps(data, ensure_ascii=False)
        lines = []
        if event_id is not None:
            lines.append(f"id: {event_id}")
        lines.append(f"event: {event}")
        lines.append(f"data: {payload}")
        return "\n".join(lines) + "\n\n"

    def _load_mas_result(mas_run_id: str) -> tuple[str, Optional[dict[str, Any]], Optional[int], Optional[str]]:
        result_db = SessionLocal()
        try:
            mas_run = mas_runs_repository.get_mas_run(result_db, mas_run_id)
            if mas_run is None:
                return "failed", None, None, "mas_run_missing"

            final_output_row = mas_final_outputs_repository.get_latest_mas_final_output_for_run(
                result_db,
                mas_run_id=mas_run_id,
            )
            final_output = (
                dict(final_output_row.output_json or {})
                if final_output_row is not None and final_output_row.output_json is not None
                else (
                    dict(mas_run.final_output_json or {})
                    if mas_run.final_output_json is not None
                    else None
                )
            )
            return mas_run.status, final_output, mas_run.duration_ms, mas_run.error_text
        finally:
            result_db.close()

    def _stream():
        nonlocal run
        model_id = _resolve_test_run_model_id(run)

        now = datetime.utcnow()
        run.status = "running"
        run.started_at = now
        run.updated_at = now
        mas_tests_repository.save_test_run(db, run)

        event_id = 1
        total_cases = len(run.selected_case_ids_json)
        case_backoff_s = max(0.0, float(settings.MAS_TEST_CASE_BACKOFF_S))
        yield _sse(
            "run_start",
            {
                "run_id": run.id,
                "workflow_id": run.workflow_id,
                "model_id": model_id,
                "total": total_cases,
            },
            event_id=event_id,
        )

        passed_count = 0
        exec_failed_count = 0
        missing_final_output_count = 0
        eval_results: list[EvalResult] = []

        for index, case_id in enumerate(run.selected_case_ids_json):
            test_case = case_by_id[case_id]
            case_run = case_runs_by_case_id.get(case_id)
            if case_run is None:
                case_run = MasTestCaseRun(
                    id=str(uuid.uuid4()),
                    test_run_id=run.id,
                    test_case_id=case_id,
                    mas_run_id=None,
                    status="created",
                    passed=None,
                    score=None,
                    diff_json=None,
                    metrics_json=None,
                    error_text=None,
                    started_at=None,
                    finished_at=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                mas_tests_repository.save_test_case_run(db, case_run)
                case_runs_by_case_id[case_id] = case_run

            start_ts = datetime.utcnow()
            case_run.status = "running"
            case_run.started_at = start_ts
            case_run.updated_at = start_ts
            mas_tests_repository.save_test_case_run(db, case_run)

            mas_run_id: Optional[str] = None
            actual_output: Optional[dict[str, Any]] = None
            duration_ms: Optional[int] = None
            error_text: Optional[str] = None
            mas_status = "failed"

            try:
                normalized_input = _normalize_runtime_input_or_400(
                    workflow_id=run.workflow_id,
                    input_json=test_case.input_json,
                )
                mas_run_id, normalized_input, _, workflow_version = mas_execution_service.create_and_start_mas_run(
                    workflow_id=run.workflow_id,
                    input_payload=normalized_input,
                    model_id=model_id,
                    metadata={
                        "source": "mas_tests",
                        "mas_test_run_id": run.id,
                        "mas_test_case_id": test_case.id,
                    },
                )
                case_run.mas_run_id = mas_run_id
                case_run.updated_at = datetime.utcnow()
                mas_tests_repository.save_test_case_run(db, case_run)

                event_id += 1
                yield _sse(
                    "case_start",
                    {
                        "index": index,
                        "test_case_id": case_id,
                        "test_case_name": test_case.name,
                        "swarm_run_id": mas_run_id,
                    },
                    event_id=event_id,
                )

                try:
                    asyncio.run(
                        mas_execution_service.execute_mas_run(
                            workflow_id=run.workflow_id,
                            workflow_version=workflow_version,
                            mas_run_id=mas_run_id,
                            case_info=normalized_input,
                            model_id=model_id,
                        )
                    )
                except Exception:
                    pass

                mas_status, actual_output, duration_ms, error_text = _load_mas_result(mas_run_id)
            except Exception as exc:
                error_text = str(exc)

            eval_result = evaluator.evaluate(
                test_case.expected_json,
                actual_output,
                mas_status=mas_status,
            )
            eval_results.append(eval_result)
            if eval_result.passed:
                passed_count += 1

            eval_metrics = dict(eval_result.metrics_json or {})
            if eval_metrics.get("exec_failed") is True:
                exec_failed_count += 1
            if eval_metrics.get("missing_final_output") is True:
                missing_final_output_count += 1

            end_ts = datetime.utcnow()
            diff_payload = _build_case_diff_payload(
                expected_answer=test_case.expected_json,
                actual_answer=actual_output,
                mas_status=mas_status,
                passed=eval_result.passed,
                evaluator_diff=eval_result.diff_json,
                error_text=error_text,
            )
            stream_diff_payload = _stream_legacy_swarm_diff_payload(diff_payload)
            failure_reason = None
            if eval_metrics.get("exec_failed") is True:
                failure_reason = "mas_failed"
            elif eval_metrics.get("missing_final_output") is True:
                failure_reason = "missing_final_output"
            elif not eval_result.passed:
                failure_reason = "expected_subset_mismatch"

            case_run.finished_at = end_ts
            case_run.updated_at = end_ts
            case_run.status = "failed" if (mas_status != "completed" or not eval_result.passed) else "succeeded"
            case_run.passed = eval_result.passed
            case_run.score = eval_result.score
            case_run.diff_json = diff_payload
            case_run.error_text = error_text
            case_run.metrics_json = {
                "mas_status": mas_status,
                "duration_ms": duration_ms,
                "final_output_present": actual_output is not None,
                "failure_reason": failure_reason,
                **eval_metrics,
            }
            mas_tests_repository.save_test_case_run(db, case_run)

            event_id += 1
            yield _sse(
                "case_done",
                {
                    "index": index,
                    "test_case_id": case_id,
                    "test_case_name": test_case.name,
                    "swarm_run_id": mas_run_id,
                    "swarm_status": mas_status,
                    "passed": eval_result.passed,
                    "score": eval_result.score,
                    "diff_json": stream_diff_payload,
                },
                event_id=event_id,
            )

            is_last_case = index >= (total_cases - 1)
            if not is_last_case and case_backoff_s > 0:
                event_id += 1
                yield _sse(
                    "case_backoff",
                    {
                        "seconds": case_backoff_s,
                        "next_index": index + 1,
                    },
                    event_id=event_id,
                )
                time.sleep(case_backoff_s)

        now = datetime.utcnow()
        total = total_cases
        pass_rate = round((passed_count / total), 4) if total else 0.0
        run.status = "succeeded" if (exec_failed_count == 0 and passed_count == total) else "failed"
        run.finished_at = now
        run.updated_at = now
        run.metrics_json = {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "execution_failed": exec_failed_count,
            "missing_final_output": missing_final_output_count,
            "pass_rate": pass_rate,
            "classification": evaluator.aggregate(eval_results),
        }
        mas_tests_repository.save_test_run(db, run)

        event_id += 1
        yield _sse(
            "run_done",
            {
                "run_id": run.id,
                "status": run.status,
                "metrics": run.metrics_json,
            },
            event_id=event_id,
        )
        yield "event: done\ndata: {}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_stream(), media_type="text/event-stream", headers=headers)
