from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agentic.model_registry import validate_model_for_agent
from app.agentic.agents.agents import get_agent_spec, supported_agent_names
from app.config import settings
from app.models.agent_run import AgentRun
from app.models.agent_test_case import AgentTestCase
from app.models.agent_test_case_run import AgentTestCaseRun
from app.models.agent_test_run import AgentTestRun
from app.schemas.agent_tests import (
    AgentTestCaseRunMetricRead,
    AgentTestCaseCreateRequest,
    AgentTestCaseRead,
    AgentTestCaseRunRead,
    AgentTestCaseUpdateRequest,
    AgentTestRunBatchMetricsRead,
    AgentTestRunDetailRead,
    AgentTestRunMetricsSummaryRead,
    AgentTestRunRead,
    AgentTestRunStartRequest,
)

from app.api.services.agent_runs_service import execute_agent_run_and_persist
from app.api.repository import agent_metrics_repository, agent_tests_repository


def _get_spec_or_400(agent_name: str):
    try:
        return get_agent_spec(agent_name)
    except KeyError:
        supported = sorted(supported_agent_names())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported agent_name '{agent_name}'. Supported: {supported}",
        )


def _evaluate_expected_subset(
    expected: dict[str, Any],
    actual: Optional[dict[str, Any]],
) -> tuple[bool, float, dict[str, Any]]:
    if actual is None:
        return False, 0.0, {"error": "actual_json_missing"}

    diffs: list[dict[str, Any]] = []

    def _walk(exp: Any, act: Any, path: str) -> None:
        if isinstance(exp, dict):
            if not isinstance(act, dict):
                diffs.append({"path": path, "expected": exp, "actual": act})
                return
            for k, v in exp.items():
                if k not in act:
                    diffs.append(
                        {
                            "path": f"{path}.{k}" if path else k,
                            "expected": v,
                            "actual": "__missing__",
                        }
                    )
                    continue
                _walk(v, act.get(k), f"{path}.{k}" if path else k)
            return

        if exp != act:
            diffs.append({"path": path, "expected": exp, "actual": act})

    _walk(expected, actual, "")
    passed = len(diffs) == 0
    score = 1.0 if passed else 0.0
    return passed, score, {"diffs": diffs}


def _build_case_diff_payload(
    *,
    expected_answer: dict[str, Any],
    agent_answer: Optional[dict[str, Any]],
    agent_status: str,
    passed: bool,
    evaluator_diff: Optional[dict[str, Any]],
    agent_error_text: Optional[str],
) -> dict[str, Any]:
    """
    Build a frontend-friendly diff payload for `case_done`.

    Keeps evaluator-provided diff keys at top level for backward compatibility,
    while always exposing both expected and actual outputs for rendering.
    """
    payload: dict[str, Any] = {
        "expected_answer": expected_answer,
        "agent_answer": agent_answer,
        "agent_status": agent_status,
    }
    if agent_error_text:
        payload["agent_error_text"] = agent_error_text
    if isinstance(evaluator_diff, dict):
        payload.update(evaluator_diff)
    # Backend verdict is authoritative for frontend rendering.
    payload["passed"] = passed
    return payload


def list_cases(
    *,
    agent_name: Optional[str],
    enabled: Optional[bool],
    limit: int,
    offset: int,
    order: str,
    db: Session,
) -> list[AgentTestCaseRead]:
    rows = agent_tests_repository.list_test_cases(
        db,
        agent_name=agent_name,
        enabled=enabled,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [AgentTestCaseRead.model_validate(r.__dict__) for r in rows]


def create_case(payload: AgentTestCaseCreateRequest, db: Session) -> AgentTestCaseRead:
    spec = _get_spec_or_400(payload.agent_name)
    if spec.evaluator is not None:
        try:
            spec.evaluator.validate_expected(payload.expected_json)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    case_id = str(uuid.uuid4())
    now = datetime.utcnow()
    row = AgentTestCase(
        id=case_id,
        agent_name=payload.agent_name,
        name=payload.name,
        enabled=payload.enabled,
        input_json=payload.input_json,
        expected_json=payload.expected_json,
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    agent_tests_repository.save_test_case(db, row, refresh=True)
    return AgentTestCaseRead.model_validate(row.__dict__)


def update_case(
    case_id: str,
    payload: AgentTestCaseUpdateRequest,
    db: Session,
) -> AgentTestCaseRead:
    row = agent_tests_repository.get_test_case(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Test case not found")

    spec = _get_spec_or_400(row.agent_name)

    if payload.name is not None:
        row.name = payload.name
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.input_json is not None:
        row.input_json = payload.input_json
    if payload.expected_json is not None:
        if spec.evaluator is not None:
            try:
                spec.evaluator.validate_expected(payload.expected_json)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        row.expected_json = payload.expected_json
    if payload.notes is not None:
        row.notes = payload.notes

    row.updated_at = datetime.utcnow()
    agent_tests_repository.save_test_case(db, row, refresh=True)
    return AgentTestCaseRead.model_validate(row.__dict__)


def delete_case(case_id: str, db: Session) -> None:
    row = agent_tests_repository.get_test_case(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    row.enabled = False
    row.updated_at = datetime.utcnow()
    agent_tests_repository.save_test_case(db, row)


def start_run(payload: AgentTestRunStartRequest, db: Session) -> AgentTestRunRead:
    if not payload.case_ids:
        raise HTTPException(status_code=400, detail="case_ids must be non-empty")

    spec = _get_spec_or_400(payload.agent_name)
    model_id = payload.model_id or settings.OPENAI_MODEL
    try:
        validate_model_for_agent(
            model_id=model_id,
            agent_name=payload.agent_name,
            requires_tools=bool(spec.tools),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cases = agent_tests_repository.get_test_cases_by_ids(db, payload.case_ids)
    case_by_id = {c.id: c for c in cases}

    missing = [cid for cid in payload.case_ids if cid not in case_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown test case ids: {missing}")

    wrong_agent = [c.id for c in cases if c.agent_name != payload.agent_name]
    if wrong_agent:
        raise HTTPException(status_code=400, detail=f"Test cases do not match agent_name: {wrong_agent}")

    disabled = [c.id for c in cases if not c.enabled]
    if disabled:
        raise HTTPException(status_code=400, detail=f"Selected test cases are disabled: {disabled}")

    if spec.evaluator is not None:
        for c in cases:
            try:
                spec.evaluator.validate_expected(c.expected_json)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid expected_json for case_id={c.id}: {e}")

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentTestRun(
        id=run_id,
        agent_name=payload.agent_name,
        name=payload.name,
        status="created",
        model_name=model_id,
        selected_case_ids_json=payload.case_ids,
        metrics_json=None,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )

    case_runs: list[AgentTestCaseRun] = []
    for case_id in payload.case_ids:
        case_runs.append(
            AgentTestCaseRun(
                id=str(uuid.uuid4()),
                test_run_id=run_id,
                test_case_id=case_id,
                agent_run_id=None,
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
        )

    agent_tests_repository.create_test_run_with_case_runs(db, run, case_runs)
    return AgentTestRunRead.model_validate(run.__dict__)


def list_runs(
    *,
    agent_name: Optional[str],
    limit: int,
    offset: int,
    order: str,
    db: Session,
) -> list[AgentTestRunRead]:
    rows = agent_tests_repository.list_test_runs(
        db,
        agent_name=agent_name,
        limit=limit,
        offset=offset,
        order=order,
    )
    return [AgentTestRunRead.model_validate(r.__dict__) for r in rows]


def get_run(run_id: str, db: Session) -> AgentTestRunDetailRead:
    run = agent_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    case_runs = agent_tests_repository.get_case_runs_for_test_run(db, run_id)
    by_case_id = {cr.test_case_id: cr for cr in case_runs}
    ordered = [by_case_id[cid] for cid in run.selected_case_ids_json if cid in by_case_id]

    return AgentTestRunDetailRead(
        run=AgentTestRunRead.model_validate(run.__dict__),
        case_runs=[AgentTestCaseRunRead.model_validate(cr.__dict__) for cr in ordered],
    )


def _avg_or_none(total: float, count: int, ndigits: int = 4) -> Optional[float]:
    if count <= 0:
        return None
    return round(total / count, ndigits)


def get_run_metrics(run_id: str, db: Session) -> AgentTestRunBatchMetricsRead:
    run = agent_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    case_runs = agent_tests_repository.get_case_runs_for_test_run(db, run_id)
    by_case_id = {cr.test_case_id: cr for cr in case_runs}
    ordered = [by_case_id[cid] for cid in run.selected_case_ids_json if cid in by_case_id]
    if len(ordered) < len(case_runs):
        selected_ids = set(run.selected_case_ids_json)
        ordered.extend([cr for cr in case_runs if cr.test_case_id not in selected_ids])

    case_ids = [cr.test_case_id for cr in ordered]
    case_rows = agent_tests_repository.get_test_cases_by_ids(db, case_ids) if case_ids else []
    case_name_by_id = {c.id: c.name for c in case_rows}

    run_ids = [cr.agent_run_id for cr in ordered if cr.agent_run_id]
    metrics_rows = agent_metrics_repository.list_run_metrics_by_run_ids(db, run_ids) if run_ids else []
    metrics_by_run_id = {m.run_id: m for m in metrics_rows}

    successful_runs = 0
    failed_runs = 0
    missing_metrics_count = 0
    llm_call_count_total = 0
    tool_call_count_total = 0
    tool_error_count_total = 0
    input_tokens_total = 0
    output_tokens_total = 0
    tokens_total = 0
    duration_ms_total = 0
    cost_usd_total_value = 0.0
    cost_rows_count = 0
    successful_cost_total = 0.0
    successful_cost_count = 0
    avg_denominator = 0
    failure_reason_counts: dict[str, int] = {}
    case_metrics: list[AgentTestCaseRunMetricRead] = []

    for cr in ordered:
        metrics_row = metrics_by_run_id.get(cr.agent_run_id) if cr.agent_run_id else None
        if metrics_row is not None:
            avg_denominator += 1
            if metrics_row.status == "succeeded":
                successful_runs += 1
            elif metrics_row.status in {"failed", "canceled"}:
                failed_runs += 1

            llm_call_count_total += int(metrics_row.llm_call_count or 0)
            tool_call_count_total += int(metrics_row.tool_call_count or 0)
            tool_error_count_total += int(metrics_row.tool_error_count or 0)
            input_tokens_total += int(metrics_row.input_tokens_total or 0)
            output_tokens_total += int(metrics_row.output_tokens_total or 0)
            tokens_total += int(metrics_row.tokens_total or 0)
            duration_ms_total += int(metrics_row.duration_ms or 0)

            if metrics_row.failure_reason:
                failure_reason_counts[metrics_row.failure_reason] = (
                    failure_reason_counts.get(metrics_row.failure_reason, 0) + 1
                )

            if metrics_row.cost_usd_total is not None:
                cost_usd_total_value += float(metrics_row.cost_usd_total)
                cost_rows_count += 1
                if metrics_row.status == "succeeded":
                    successful_cost_total += float(metrics_row.cost_usd_total)
                    successful_cost_count += 1
        else:
            if cr.agent_run_id:
                missing_metrics_count += 1

        row_status = cr.status
        if metrics_row is not None and metrics_row.status in {"created", "running", "succeeded", "failed"}:
            row_status = metrics_row.status

        case_metrics.append(
            AgentTestCaseRunMetricRead(
                test_case_id=cr.test_case_id,
                test_case_name=case_name_by_id.get(cr.test_case_id),
                agent_run_id=cr.agent_run_id,
                status=row_status,
                failure_reason=(
                    metrics_row.failure_reason
                    if metrics_row is not None
                    else ("metrics_missing" if cr.agent_run_id else None)
                ),
                llm_call_count=(int(metrics_row.llm_call_count) if metrics_row is not None else None),
                tool_call_count=(int(metrics_row.tool_call_count) if metrics_row is not None else None),
                tool_error_count=(int(metrics_row.tool_error_count) if metrics_row is not None else None),
                input_tokens_total=(
                    int(metrics_row.input_tokens_total) if metrics_row is not None else None
                ),
                output_tokens_total=(
                    int(metrics_row.output_tokens_total) if metrics_row is not None else None
                ),
                tokens_total=(int(metrics_row.tokens_total) if metrics_row is not None else None),
                duration_ms=(int(metrics_row.duration_ms) if metrics_row is not None else None),
                latency_ms=(int(metrics_row.duration_ms) if metrics_row is not None else None),
                cost_usd_total=(
                    float(metrics_row.cost_usd_total)
                    if (metrics_row is not None and metrics_row.cost_usd_total is not None)
                    else None
                ),
            )
        )

    total_runs = len(ordered)
    runs_with_agent_run = len(run_ids)
    success_rate = round((successful_runs / runs_with_agent_run), 4) if runs_with_agent_run else 0.0

    summary = AgentTestRunMetricsSummaryRead(
        total_runs=total_runs,
        runs_with_agent_run=runs_with_agent_run,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        missing_metrics_count=missing_metrics_count,
        llm_call_count_total=llm_call_count_total,
        tool_call_count_total=tool_call_count_total,
        tool_error_count_total=tool_error_count_total,
        input_tokens_total=input_tokens_total,
        output_tokens_total=output_tokens_total,
        tokens_total=tokens_total,
        duration_ms_total=duration_ms_total,
        cost_usd_total=(round(cost_usd_total_value, 6) if cost_rows_count > 0 else None),
        llm_call_count_avg=_avg_or_none(llm_call_count_total, avg_denominator),
        tool_call_count_avg=_avg_or_none(tool_call_count_total, avg_denominator),
        tool_error_count_avg=_avg_or_none(tool_error_count_total, avg_denominator),
        input_tokens_avg=_avg_or_none(input_tokens_total, avg_denominator),
        output_tokens_avg=_avg_or_none(output_tokens_total, avg_denominator),
        tokens_avg=_avg_or_none(tokens_total, avg_denominator),
        duration_ms_avg=_avg_or_none(duration_ms_total, avg_denominator),
        cost_usd_avg=_avg_or_none(cost_usd_total_value, cost_rows_count, ndigits=6),
        cost_usd_avg_successful=_avg_or_none(successful_cost_total, successful_cost_count, ndigits=6),
        failure_reason_counts=failure_reason_counts,
    )

    return AgentTestRunBatchMetricsRead(
        run=AgentTestRunRead.model_validate(run.__dict__),
        summary=summary,
        cases=case_metrics,
    )


def stream_run(run_id: str, db: Session) -> StreamingResponse:
    run = agent_tests_repository.get_test_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    if run.status == "running":
        raise HTTPException(status_code=409, detail="Test run is already running")
    if run.status in {"succeeded", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail=f"Test run is already {run.status}")

    cases = agent_tests_repository.get_test_cases_by_ids(db, run.selected_case_ids_json)
    case_by_id = {c.id: c for c in cases}
    missing = [cid for cid in run.selected_case_ids_json if cid not in case_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing test cases for run: {missing}")

    cr_by_case_id = agent_tests_repository.get_case_runs_by_case_id(db, run_id)

    spec = _get_spec_or_400(run.agent_name)
    evaluator = spec.evaluator
    if evaluator is not None:
        for c in cases:
            try:
                evaluator.validate_expected(c.expected_json)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid expected_json for case_id={c.id}: {e}")

    model_id = run.model_name or settings.OPENAI_MODEL
    try:
        validate_model_for_agent(
            model_id=model_id,
            agent_name=run.agent_name,
            requires_tools=bool(spec.tools),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    def _sse(event: str, data: dict, event_id: Optional[int] = None) -> str:
        payload = json.dumps(data, ensure_ascii=False)
        lines = []
        if event_id is not None:
            lines.append(f"id: {event_id}")
        lines.append(f"event: {event}")
        lines.append(f"data: {payload}")
        return "\n".join(lines) + "\n\n"

    def _stream():
        nonlocal run

        now = datetime.utcnow()
        run.status = "running"
        run.started_at = now
        run.updated_at = now
        agent_tests_repository.save_test_run(db, run)

        event_id = 1
        total_cases = len(run.selected_case_ids_json)
        case_backoff_s = max(0.0, float(settings.TEST_CASE_BACKOFF_S))
        yield _sse(
            "run_start",
            {
                "run_id": run.id,
                "agent_name": run.agent_name,
                "total": total_cases,
            },
            event_id=event_id,
        )

        passed_count = 0
        warning_count = 0
        exec_failed_count = 0
        invalid_pred_count = 0
        eval_results = []

        for idx, case_id in enumerate(run.selected_case_ids_json):
            test_case = case_by_id[case_id]
            case_run = cr_by_case_id.get(case_id)
            if case_run is None:
                case_run = AgentTestCaseRun(
                    id=str(uuid.uuid4()),
                    test_run_id=run.id,
                    test_case_id=case_id,
                    agent_run_id=None,
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
                agent_tests_repository.save_test_case_run(db, case_run)
                cr_by_case_id[case_id] = case_run

            start_ts = datetime.utcnow()
            case_run.status = "running"
            case_run.started_at = start_ts
            case_run.updated_at = start_ts
            agent_tests_repository.save_test_case_run(db, case_run)

            agent_run_id = str(uuid.uuid4())
            agent_run = AgentRun(
                id=agent_run_id,
                agent_name=run.agent_name,
                status="running",
                model_name=run.model_name or settings.OPENAI_MODEL,
                input_json=test_case.input_json,
                output_json=None,
                error_text=None,
                started_at=start_ts,
                finished_at=None,
                created_at=start_ts,
                updated_at=start_ts,
            )
            agent_tests_repository.save_agent_run(db, agent_run)

            case_run.agent_run_id = agent_run_id
            case_run.updated_at = datetime.utcnow()
            agent_tests_repository.save_test_case_run(db, case_run)

            event_id += 1
            yield _sse(
                "case_start",
                {
                    "index": idx,
                    "test_case_id": case_id,
                    "test_case_name": test_case.name,
                    "agent_run_id": agent_run_id,
                },
                event_id=event_id,
            )

            output_json = execute_agent_run_and_persist(db, agent_run)
            agent_status = agent_run.status
            error_text = agent_run.error_text

            if evaluator is not None:
                try:
                    eval_result = evaluator.evaluate(
                        test_case.expected_json,
                        output_json,
                        agent_status=agent_status,
                    )
                except ValueError as e:
                    eval_result = None
                    passed = False
                    score = 0.0
                    diff_json = {"error": "invalid_expected_json", "detail": str(e)}
                    eval_metrics = {"exec_failed": False, "invalid_pred": False}
                else:
                    eval_results.append(eval_result)
                    passed = eval_result.passed
                    score = eval_result.score
                    diff_json = eval_result.diff_json
                    eval_metrics = eval_result.metrics_json

                if eval_metrics.get("exec_failed") is True:
                    exec_failed_count += 1
                if eval_metrics.get("invalid_pred") is True:
                    invalid_pred_count += 1
                if eval_metrics.get("warning") is True:
                    warning_count += 1
            else:
                passed, score, diff_json = _evaluate_expected_subset(
                    test_case.expected_json, output_json
                )
                eval_metrics = {}
                if agent_status == "failed":
                    exec_failed_count += 1

            end_ts = datetime.utcnow()

            case_run.finished_at = end_ts
            case_run.updated_at = end_ts
            case_run.status = "failed" if (agent_status == "failed" or not passed) else "succeeded"
            case_run.passed = passed
            case_run.score = score
            diff_payload = _build_case_diff_payload(
                expected_answer=test_case.expected_json,
                agent_answer=output_json,
                agent_status=agent_status,
                passed=passed,
                evaluator_diff=diff_json,
                agent_error_text=error_text,
            )
            case_run.diff_json = diff_payload
            case_run.error_text = error_text
            case_run.metrics_json = {
                "latency_ms": int((end_ts - start_ts).total_seconds() * 1000),
                "agent_status": agent_status,
                **(eval_metrics or {}),
            }
            agent_tests_repository.save_test_case_run(db, case_run)

            if passed:
                passed_count += 1

            event_id += 1
            yield _sse(
                "case_done",
                {
                    "index": idx,
                    "test_case_id": case_id,
                    "test_case_name": test_case.name,
                    "agent_run_id": agent_run_id,
                    "agent_status": agent_status,
                    "passed": passed,
                    "score": score,
                    "diff_json": diff_payload,
                },
                event_id=event_id,
            )

            is_last_case = idx >= (total_cases - 1)
            if not is_last_case and case_backoff_s > 0:
                event_id += 1
                yield _sse(
                    "case_backoff",
                    {
                        "seconds": case_backoff_s,
                        "next_index": idx + 1,
                    },
                    event_id=event_id,
                )
                time.sleep(case_backoff_s)

        total = total_cases
        pass_rate = (passed_count / total) if total else 0.0
        warning_rate = (warning_count / total) if total else 0.0
        now = datetime.utcnow()

        run.status = "succeeded" if (exec_failed_count == 0 and passed_count == total) else "failed"
        run.finished_at = now
        run.updated_at = now
        run.metrics_json = {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "exec_failed": exec_failed_count,
            "invalid_pred": invalid_pred_count,
            "pass_rate": round(pass_rate, 4),
            "warning_count": warning_count,
            "warning_rate": round(warning_rate, 4),
        }
        if evaluator is not None:
            run.metrics_json["classification"] = evaluator.aggregate(eval_results)
        agent_tests_repository.save_test_run(db, run)

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
