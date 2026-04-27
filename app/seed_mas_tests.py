from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.mas_test_case import MasTestCase
from app.models.mas_test_case_run import MasTestCaseRun
from app.models.mas_test_run import MasTestRun


WORKFLOW_ID = "esi_swarm_v1"
RAW_CASES_PATH = Path(__file__).with_name("seed_mas_tests_esi_swarm_v1.jsonish")


def _load_raw_cases() -> list[dict]:
    raw = RAW_CASES_PATH.read_text(encoding="utf-8")
    normalized = raw
    normalized = normalized.replace('"arrival_transport"MBULANCE",', '"arrival_transport": "AMBULANCE",')
    normalized = re.sub(r'(?m)^(\s*)([A-Za-z_][A-Za-z0-9_]*)":', r'\1"\2":', normalized)
    return json.loads(normalized)


def ensure_seed_esi_swarm_v1_mas_test_cases(db: Session) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = _load_raw_cases()

    case_ids = db.execute(
        select(MasTestCase.id).where(MasTestCase.workflow_id == WORKFLOW_ID)
    ).scalars().all()
    run_ids = db.execute(
        select(MasTestRun.id).where(MasTestRun.workflow_id == WORKFLOW_ID)
    ).scalars().all()

    if run_ids:
        db.execute(delete(MasTestCaseRun).where(MasTestCaseRun.test_run_id.in_(run_ids)))
        db.execute(delete(MasTestRun).where(MasTestRun.id.in_(run_ids)))
    if case_ids:
        db.execute(delete(MasTestCaseRun).where(MasTestCaseRun.test_case_id.in_(case_ids)))
        db.execute(delete(MasTestCase).where(MasTestCase.id.in_(case_ids)))
    if run_ids or case_ids:
        db.commit()

    for index, item in enumerate(rows, start=1):
        input_json = dict(item["input"])
        expected_json = dict(item["output"])
        chiefcomplaint = str(input_json.get("chiefcomplaint") or "case").strip()
        tiragecase = str(input_json.get("tiragecase") or "case").strip()
        db.add(
            MasTestCase(
                id=str(uuid.uuid4()),
                workflow_id=WORKFLOW_ID,
                name=f"Seed {index:02d} - {chiefcomplaint}",
                enabled=True,
                input_json=input_json,
                expected_json=expected_json,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()

