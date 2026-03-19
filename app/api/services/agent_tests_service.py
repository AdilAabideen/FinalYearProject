from __future__ import annotations

import json
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
    AgentTestCaseCreateRequest,
    AgentTestCaseRead,
    AgentTestCaseRunRead,
    AgentTestCaseUpdateRequest,
    AgentTestRunDetailRead,
    AgentTestRunRead,
    AgentTestRunStartRequest,
)

from app.api.services.agent_runs_service import execute_agent_run_and_persist
from app.api.repository import agent_tests_repository


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
            requires_structured_output=spec.output_model is not None,
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
            requires_structured_output=spec.output_model is not None,
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
        yield _sse(
            "run_start",
            {
                "run_id": run.id,
                "agent_name": run.agent_name,
                "total": len(run.selected_case_ids_json),
            },
            event_id=event_id,
        )

        passed_count = 0
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
            case_run.diff_json = diff_json
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
                    "diff_json": diff_json,
                },
                event_id=event_id,
            )

        total = len(run.selected_case_ids_json)
        pass_rate = (passed_count / total) if total else 0.0
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
