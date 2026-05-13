"""Doctoragenttests script helpers."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.database import SessionLocal
from app.models.agent_test_case import AgentTestCase


def _repo_root() -> Path:
    """Handle root."""
    # Keep the main step clear.
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    """Parse args."""
    # Keep the output consistent.
    parser = argparse.ArgumentParser(
        description="Initialize doctor agent test cases from JSON into agent_test_cases."
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=str(_repo_root() / "datasets" / "doctor_agent_test_cases.json"),
        help="Path to source JSON (default: datasets/doctor_agent_test_cases.json)",
    )
    parser.add_argument(
        "--agent-name",
        default="doctor_agent",
        help="Agent name to tag inserted cases (default: doctor_agent)",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete existing cases for this agent_name before inserting JSON rows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report actions without writing to DB.",
    )
    return parser.parse_args()


def _slugify(value: str) -> str:
    """Handle the value."""
    # Keep the main step clear.
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:40] or "case"


def _build_name(index: int, item: dict[str, Any]) -> str:
    """Build name."""
    # Build the next value.
    chiefcomplaint = str(item.get("chiefcomplaint") or "").strip()
    source_agent = str(item.get("source_agent") or "unknown").strip()
    return f"doctor_json_case_{index:02d}_{_slugify(chiefcomplaint)}_{_slugify(source_agent)}"


def _build_notes(index: int, item: dict[str, Any], json_name: str) -> str:
    """Build notes."""
    # Build the next value.
    source_agent = str(item.get("source_agent") or "unknown").strip()
    chiefcomplaint = str(item.get("chiefcomplaint") or "").strip()
    return (
        f"source_json={json_name};"
        f"row={index};"
        f"source_agent={source_agent};"
        f"chiefcomplaint={chiefcomplaint}"
    )


def _load_json_rows(json_path: Path) -> list[dict[str, Any]]:
    """Load json rows."""
    # Read the current value.
    with json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("JSON root must be a list of input_json objects")

    prepared: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Row {index} is not a JSON object")
        prepared.append(
            {
                "name": _build_name(index, item),
                "input_json": item,
                "expected_json": {},
                "notes": _build_notes(index, item, json_path.name),
            }
        )
    return prepared


def main() -> int:
    """Handle the value."""
    # Keep the main step clear.
    args = _parse_args()

    json_path = Path(args.json_path)
    if not json_path.is_absolute():
        json_path = (_repo_root() / json_path).resolve()
    if not json_path.exists():
        print(f"JSON not found: {json_path}", file=sys.stderr)
        return 1

    try:
        prepared_rows = _load_json_rows(json_path)
    except Exception as exc:
        print(f"Failed to parse JSON: {exc}", file=sys.stderr)
        return 1

    if not prepared_rows:
        print("No valid rows parsed from JSON. Nothing to insert.")
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
            f"[{mode}] agent_name={args.agent_name} json={json_path.name} "
            f"prepared={len(prepared_rows)} inserted={inserted} updated={updated} deleted={deleted}"
        )
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Failed to initialize doctor test cases: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
