from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.endpoints.agent_runs import _append_event as _append_agent_event
from app.api.endpoints.agent_runs import _get_last_seq as _get_last_agent_seq
from app.api.endpoints.agent_runs import _run_agent_and_persist as _run_agent_and_persist
from app.config import settings
from app.database import get_db
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

router = APIRouter()


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


@router.get("/cases", response_model=list[AgentTestCaseRead])
def list_test_cases(
    agent_name: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    stmt = select(AgentTestCase)
    if agent_name:
        stmt = stmt.where(AgentTestCase.agent_name == agent_name)
    if enabled is not None:
        stmt = stmt.where(AgentTestCase.enabled == enabled)

    if order == "asc":
        stmt = stmt.order_by(AgentTestCase.created_at.asc(), AgentTestCase.id.asc())
    else:
        stmt = stmt.order_by(AgentTestCase.created_at.desc(), AgentTestCase.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [AgentTestCaseRead.model_validate(r.__dict__) for r in rows]


@router.post("/cases", response_model=AgentTestCaseRead, status_code=status.HTTP_201_CREATED)
def create_test_case(payload: AgentTestCaseCreateRequest, db: Session = Depends(get_db)):
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
    db.add(row)
    db.commit()
    db.refresh(row)
    return AgentTestCaseRead.model_validate(row.__dict__)


@router.put("/cases/{case_id}", response_model=AgentTestCaseRead)
def update_test_case(case_id: str, payload: AgentTestCaseUpdateRequest, db: Session = Depends(get_db)):
    row = db.get(AgentTestCase, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Test case not found")

    if payload.name is not None:
        row.name = payload.name
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.input_json is not None:
        row.input_json = payload.input_json
    if payload.expected_json is not None:
        row.expected_json = payload.expected_json
    if payload.notes is not None:
        row.notes = payload.notes

    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return AgentTestCaseRead.model_validate(row.__dict__)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(case_id: str, db: Session = Depends(get_db)):
    row = db.get(AgentTestCase, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    db.delete(row)
    db.commit()
    return None


@router.post("/runs/start", response_model=AgentTestRunRead, status_code=status.HTTP_201_CREATED)
def start_test_run(payload: AgentTestRunStartRequest, db: Session = Depends(get_db)):
    if not payload.case_ids:
        raise HTTPException(status_code=400, detail="case_ids must be non-empty")

    stmt = (
        select(AgentTestCase)
        .where(AgentTestCase.id.in_(payload.case_ids))
    )
    cases = db.execute(stmt).scalars().all()
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

    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = AgentTestRun(
        id=run_id,
        agent_name=payload.agent_name,
        name=payload.name,
        status="created",
        model_name=settings.OPENAI_MODEL,
        selected_case_ids_json=payload.case_ids,
        metrics_json=None,
        started_at=None,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(run)

    for case_id in payload.case_ids:
        db.add(
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
    db.commit()
    db.refresh(run)

    return AgentTestRunRead.model_validate(run.__dict__)


@router.get("/runs", response_model=list[AgentTestRunRead])
def list_test_runs(
    agent_name: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    stmt = select(AgentTestRun)
    if agent_name:
        stmt = stmt.where(AgentTestRun.agent_name == agent_name)

    if order == "asc":
        stmt = stmt.order_by(AgentTestRun.created_at.asc(), AgentTestRun.id.asc())
    else:
        stmt = stmt.order_by(AgentTestRun.created_at.desc(), AgentTestRun.id.desc())

    stmt = stmt.offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [AgentTestRunRead.model_validate(r.__dict__) for r in rows]


@router.get("/runs/{run_id}", response_model=AgentTestRunDetailRead)
def get_test_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AgentTestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    stmt = select(AgentTestCaseRun).where(AgentTestCaseRun.test_run_id == run_id)
    case_runs = db.execute(stmt).scalars().all()
    by_case_id = {cr.test_case_id: cr for cr in case_runs}
    ordered = [by_case_id[cid] for cid in run.selected_case_ids_json if cid in by_case_id]

    return AgentTestRunDetailRead(
        run=AgentTestRunRead.model_validate(run.__dict__),
        case_runs=[AgentTestCaseRunRead.model_validate(cr.__dict__) for cr in ordered],
    )


@router.get("/runs/{run_id}/stream")
def stream_test_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = db.get(AgentTestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Test run not found")

    if run.status == "running":
        raise HTTPException(status_code=409, detail="Test run is already running")
    if run.status in {"succeeded", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail=f"Test run is already {run.status}")

    # Preload cases and case-run rows (so we fail fast before starting).
    cases = db.execute(
        select(AgentTestCase).where(AgentTestCase.id.in_(run.selected_case_ids_json))
    ).scalars().all()
    case_by_id = {c.id: c for c in cases}
    missing = [cid for cid in run.selected_case_ids_json if cid not in case_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing test cases for run: {missing}")

    cr_rows = db.execute(
        select(AgentTestCaseRun).where(AgentTestCaseRun.test_run_id == run_id)
    ).scalars().all()
    cr_by_case_id = {cr.test_case_id: cr for cr in cr_rows}

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
        db.add(run)
        db.commit()

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

        for idx, case_id in enumerate(run.selected_case_ids_json):
            test_case = case_by_id[case_id]
            case_run = cr_by_case_id.get(case_id)
            if case_run is None:
                # Should not happen, but keep the run usable.
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
                db.add(case_run)
                db.commit()
                cr_by_case_id[case_id] = case_run

            start_ts = datetime.utcnow()
            case_run.status = "running"
            case_run.started_at = start_ts
            case_run.updated_at = start_ts
            db.add(case_run)
            db.commit()

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
            db.add(agent_run)
            db.commit()

            case_run.agent_run_id = agent_run_id
            case_run.updated_at = datetime.utcnow()
            db.add(case_run)
            db.commit()

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

            agent_seq = 1
            _append_agent_event(
                db=db,
                run=agent_run,
                seq=agent_seq,
                event_type="run_start",
                payload_json={"input": agent_run.input_json},
            )

            output_json: Optional[dict] = None
            agent_status = "failed"
            error_text: Optional[str] = None
            try:
                agent_seq, output_json = _run_agent_and_persist(db, agent_run, agent_seq)

                now = datetime.utcnow()
                agent_run.status = "succeeded"
                agent_run.output_json = output_json
                agent_run.finished_at = now
                agent_run.updated_at = now
                db.add(agent_run)
                db.commit()

                agent_seq += 1
                _append_agent_event(
                    db=db,
                    run=agent_run,
                    seq=agent_seq,
                    event_type="run_end",
                    payload_json={"status": agent_run.status},
                )
                agent_status = agent_run.status
            except Exception as e:
                now = datetime.utcnow()
                agent_run.status = "failed"
                agent_run.error_text = str(e)
                agent_run.finished_at = now
                agent_run.updated_at = now
                db.add(agent_run)
                db.commit()

                error_text = str(e)

                agent_seq = _get_last_agent_seq(db, agent_run_id)
                agent_seq += 1
                _append_agent_event(
                    db=db,
                    run=agent_run,
                    seq=agent_seq,
                    event_type="error",
                    status="error",
                    payload_text=str(e),
                )
                agent_seq += 1
                _append_agent_event(
                    db=db,
                    run=agent_run,
                    seq=agent_seq,
                    event_type="run_end",
                    payload_json={"status": agent_run.status},
                )
                agent_status = agent_run.status

            passed, score, diff_json = _evaluate_expected_subset(test_case.expected_json, output_json)
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
            }
            db.add(case_run)
            db.commit()

            if agent_status == "failed":
                exec_failed_count += 1
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
            "pass_rate": round(pass_rate, 4),
        }
        db.add(run)
        db.commit()

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
