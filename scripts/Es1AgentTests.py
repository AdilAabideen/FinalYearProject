from __future__ import annotations

import argparse
import csv
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

# Ensure `import app...` works when executed as `python scripts/Es1AgentTests.py`.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.database import SessionLocal
from app.models.agent_test_case import AgentTestCase


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize ES1 agent test cases from CSV into agent_test_cases."
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=str(_repo_root() / "datasets" / "validation_es1_test_cases_retain_final.csv"),
        help="Path to source CSV (default: datasets/validation_es1_test_cases_retain_final.csv)",
    )
    parser.add_argument(
        "--agent-name",
        default="esi1_agent",
        help="Agent name to tag inserted cases (default: esi1_agent)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of rows to load from CSV.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete existing cases for this agent_name before inserting CSV rows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report actions without writing to DB.",
    )
    return parser.parse_args()


def _normalize_row(raw: dict[str, Any]) -> dict[str, str]:
    return {str(k).strip().lower(): ("" if v is None else str(v).strip()) for k, v in raw.items()}


def _parse_age(value: str) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _parse_acuity(value: str) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        as_float = float(s)
    except Exception:
        return None
    if int(as_float) != as_float:
        return None
    acuity = int(as_float)
    if acuity < 1 or acuity > 5:
        return None
    return acuity


def _build_input_json(row: dict[str, str]) -> Optional[dict[str, Any]]:
    age = _parse_age(row.get("age", ""))
    if age is None:
        return None

    required = ("gender", "race", "arrival_transport", "pain", "chiefcomplaint", "tiragecase")
    values: dict[str, str] = {}
    for key in required:
        val = row.get(key, "").strip()
        if not val:
            return None
        values[key] = val

    return {
        "gender": values["gender"],
        "race": values["race"],
        "arrival_transport": values["arrival_transport"],
        "pain": values["pain"],
        "chiefcomplaint": values["chiefcomplaint"],
        "age": age,
        "tiragecase": values["tiragecase"],
    }


def _load_csv_rows(csv_path: Path, limit: Optional[int]) -> tuple[list[dict[str, Any]], list[str]]:
    prepared: list[dict[str, Any]] = []
    skipped: list[str] = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, raw in enumerate(reader):
            if limit is not None and idx >= limit:
                break

            row = _normalize_row(raw)
            row_id = row.get("", "") or str(idx)
            acuity = _parse_acuity(row.get("acuity", ""))
            if acuity is None:
                skipped.append(f"row={row_id}: invalid acuity")
                continue

            input_json = _build_input_json(row)
            if input_json is None:
                skipped.append(f"row={row_id}: missing/invalid required input field(s)")
                continue

            subject_id = row.get("subject_id", "")
            stay_id = row.get("stay_id", "")
            case_name = f"es1_csv_case_{row_id}"
            expected_json = {"acuity": acuity}
            notes = (
                "source_csv=validation_es1_test_cases_retain_final.csv;"
                f"row={row_id};subject_id={subject_id};stay_id={stay_id};acuity={acuity}"
            )
            prepared.append(
                {
                    "name": case_name,
                    "input_json": input_json,
                    "expected_json": expected_json,
                    "notes": notes,
                }
            )
    return prepared, skipped


def main() -> int:
    args = _parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.is_absolute():
        csv_path = (_repo_root() / csv_path).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    prepared_rows, skipped = _load_csv_rows(csv_path, args.limit)
    if not prepared_rows:
        print("No valid rows parsed from CSV. Nothing to insert.")
        if skipped:
            print(f"Skipped rows: {len(skipped)}")
            for msg in skipped[:20]:
                print(f"  - {msg}")
        return 1

    db = SessionLocal()
    inserted = 0
    updated = 0
    deleted = 0
    try:
        if args.replace_existing:
            existing_rows = db.execute(
                select(AgentTestCase).where(AgentTestCase.agent_name == args.agent_name)
            ).scalars().all()
            deleted = len(existing_rows)
            for row in existing_rows:
                db.delete(row)
            if not args.dry_run:
                db.flush()

        existing_by_name = {
            row.name: row
            for row in db.execute(
                select(AgentTestCase).where(AgentTestCase.agent_name == args.agent_name)
            ).scalars().all()
        }

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for item in prepared_rows:
            existing = existing_by_name.get(item["name"])
            if existing is None:
                db.add(
                    AgentTestCase(
                        id=str(uuid.uuid4()),
                        agent_name=args.agent_name,
                        name=item["name"],
                        enabled=True,
                        input_json=item["input_json"],
                        expected_json=item["expected_json"],
                        notes=item["notes"],
                        created_at=now,
                        updated_at=now,
                    )
                )
                inserted += 1
            else:
                existing.enabled = True
                existing.input_json = item["input_json"]
                existing.expected_json = item["expected_json"]
                existing.notes = item["notes"]
                existing.updated_at = now
                updated += 1

        if args.dry_run:
            db.rollback()
            mode = "DRY RUN"
        else:
            db.commit()
            mode = "COMMITTED"

        print(
            f"[{mode}] agent_name={args.agent_name} csv={csv_path.name} "
            f"prepared={len(prepared_rows)} inserted={inserted} updated={updated} deleted={deleted} skipped={len(skipped)}"
        )
        if skipped:
            print("Skipped rows (first 20):")
            for msg in skipped[:20]:
                print(f"  - {msg}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Failed to initialize ES1 test cases: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
