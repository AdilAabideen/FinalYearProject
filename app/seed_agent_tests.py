from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_test_case import AgentTestCase


def ensure_seed_vitals_agent_test_cases(db: Session) -> None:
    """
    Idempotently seed 7 default test cases for the vitals agent into `agent_test_cases`.

    This is only for convenience in dev; it will not overwrite existing rows.
    """

    existing = db.execute(
        select(AgentTestCase).where(AgentTestCase.agent_name == "vitals_agent").limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def base_input(**overrides):
        payload = {
            "temperature": 98.6,
            "heartrate": 80.0,
            "resprate": 16.0,
            "o2sat": 98.0,
            "sbp": 120.0,
            "dbp": 80.0,
            "pain": 2.0,
            "subject_id": -1,
            "intime": "2026-01-01T12:00:00",
            "chiefcomplaint": "routine check",
            "age_years": 35.0,
        }
        payload.update(overrides)
        return payload

    seeded = [
        {
            "name": "Normal vitals (no uptriage)",
            "input_json": base_input(chiefcomplaint="ankle sprain", pain=3.0),
            "expected_json": {"recommendation": {"consider_uptriage": False}},
        },
        {
            "name": "Hard danger zone (SOB + low SpO2)",
            "input_json": base_input(
                heartrate=120.0,
                resprate=28.0,
                o2sat=88.0,
                sbp=110.0,
                dbp=70.0,
                temperature=101.0,
                chiefcomplaint="shortness of breath",
                age_years=45.0,
                pain=4.0,
            ),
            "expected_json": {"recommendation": {"consider_uptriage": True}},
        },
        {
            "name": "Shock index hard (tachy + hypotension)",
            "input_json": base_input(
                heartrate=130.0,
                sbp=85.0,
                dbp=55.0,
                resprate=22.0,
                o2sat=95.0,
                chiefcomplaint="dizziness",
                age_years=60.0,
                pain=1.0,
            ),
            "expected_json": {"recommendation": {"consider_uptriage": True}},
        },
        {
            "name": "Two soft flags (borderline SBP + soft shock index)",
            "input_json": base_input(
                heartrate=90.0,
                sbp=95.0,
                dbp=60.0,
                resprate=18.0,
                o2sat=98.0,
                temperature=99.1,
                chiefcomplaint="abdominal pain",
                age_years=40.0,
                pain=6.0,
            ),
            "expected_json": {"recommendation": {"consider_uptriage": True}},
        },
        {
            "name": "Hyperpyrexia (Temp >= 104F)",
            "input_json": base_input(
                temperature=104.5,
                heartrate=102.0,
                resprate=20.0,
                o2sat=97.0,
                sbp=118.0,
                dbp=76.0,
                chiefcomplaint="fever and chills",
                age_years=29.0,
                pain=5.0,
            ),
            "expected_json": {"recommendation": {"consider_uptriage": True}},
        },
        {
            "name": "Hypertensive emergency pattern (chest pain + very high BP)",
            "input_json": base_input(
                sbp=190.0,
                dbp=125.0,
                heartrate=95.0,
                resprate=20.0,
                o2sat=97.0,
                chiefcomplaint="chest pain",
                age_years=55.0,
                pain=7.0,
            ),
            "expected_json": {"recommendation": {"consider_uptriage": True}},
        },
        {
            "name": "Single soft flag only (mild tachycardia)",
            "input_json": base_input(
                heartrate=103.0,
                resprate=18.0,
                o2sat=99.0,
                sbp=130.0,
                dbp=85.0,
                chiefcomplaint="anxiety",
                age_years=25.0,
                pain=1.0,
            ),
            "expected_json": {"recommendation": {"consider_uptriage": False}},
        },
    ]

    for item in seeded:
        db.add(
            AgentTestCase(
                id=str(uuid.uuid4()),
                agent_name="vitals_agent",
                name=item["name"],
                enabled=True,
                input_json=item["input_json"],
                expected_json=item["expected_json"],
                notes="seeded",
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()

