"""Migrate Agent Tests Add Fks script helpers."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Sequence

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.engine.url import make_url


def _repo_root() -> Path:
    """Handle root."""
    # Keep the main step clear.
    return Path(__file__).resolve().parents[1]


if str(_repo_root()) not in sys.path:
    sys.path.insert(0, str(_repo_root()))


from app.config import settings  # noqa: E402


def _resolve_database_url(database_url: str) -> str:
    """
    Ensure SQLite relative paths always point at the repo root.

    Without this, running the script from `scripts/` would create/use `scripts/app.db`
    for a URL like `sqlite:///app.db`.
    """
    # Pick the needed value.
    try:
        url = make_url(database_url)
    except Exception:  # noqa: BLE001
        return database_url

    if not url.drivername.startswith("sqlite"):
        return database_url
    if not url.database or url.database == ":memory:":
        return database_url

    db_path = Path(url.database)
    if db_path.is_absolute():
        return database_url

    abs_db_path = (_repo_root() / db_path).resolve()
    return str(url.set(database=str(abs_db_path)))


_DATABASE_URL = _resolve_database_url(settings.DATABASE_URL)
_CONNECT_ARGS = {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(_DATABASE_URL, connect_args=_CONNECT_ARGS, future=True)


TEST_TABLES: Sequence[str] = (
    "agent_test_cases",
    "agent_test_runs",
    "agent_test_case_runs",
)


def _table_exists(conn: Connection, table_name: str) -> bool:
    """Handle exists."""
    # Keep the main step clear.
    row = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _fk_list(conn: Connection, table_name: str) -> list[tuple]:
    """Handle list."""
    # Keep the main step clear.
    return conn.exec_driver_sql(f"PRAGMA foreign_key_list('{table_name}')").fetchall()


def _count_invalid_agent_run_refs(conn: Connection) -> int:
    """Count invalid agent run refs."""
    # Derive the needed value.
    row = conn.exec_driver_sql(
        """
        SELECT COUNT(*)
        FROM agent_test_case_runs
        WHERE agent_run_id IS NOT NULL
          AND agent_run_id NOT IN (SELECT id FROM agent_runs)
        """
    ).fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    """Handle the value."""
    # Keep the main step clear.
    if not settings.DATABASE_URL.startswith("sqlite"):
        print("This migration script is SQLite-only.")
        print(f"DATABASE_URL={settings.DATABASE_URL}")
        return 2

    with engine.connect() as conn:
        for t in TEST_TABLES:
            if not _table_exists(conn, t):
                print(f"Table '{t}' does not exist; nothing to migrate.")
                return 0

        if _fk_list(conn, "agent_test_case_runs"):
            print("Foreign keys already present on agent_test_case_runs; nothing to do.")
            return 0

        invalid_agent_run_refs = _count_invalid_agent_run_refs(conn)
        if invalid_agent_run_refs:
            print(
                "Aborting: found agent_test_case_runs.agent_run_id values that do not exist in agent_runs."
            )
            print(f"Invalid agent_run_id refs: {invalid_agent_run_refs}")
            print("Fix or delete those rows, then rerun this migration.")
            return 1

    backup_tag = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:8]
    backup_cases = f"agent_test_cases__backup_{backup_tag}"
    backup_runs = f"agent_test_runs__backup_{backup_tag}"
    backup_case_runs = f"agent_test_case_runs__backup_{backup_tag}"

    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

        for temp in ("agent_test_cases__new", "agent_test_runs__new", "agent_test_case_runs__new"):
            if _table_exists(conn, temp):
                raise RuntimeError(
                    f"Temp table '{temp}' already exists. Drop it manually before running migration again."
                )

        conn.exec_driver_sql(
            """
            CREATE TABLE agent_test_cases__new (
              id VARCHAR NOT NULL PRIMARY KEY,
              agent_name VARCHAR NOT NULL,
              name VARCHAR NOT NULL,
              enabled BOOLEAN NOT NULL,
              input_json JSON NOT NULL,
              expected_json JSON NOT NULL,
              notes TEXT,
              created_at DATETIME NOT NULL,
              updated_at DATETIME
            )
            """
        )

        conn.exec_driver_sql(
            """
            CREATE TABLE agent_test_runs__new (
              id VARCHAR NOT NULL PRIMARY KEY,
              agent_name VARCHAR NOT NULL,
              name VARCHAR,
              status VARCHAR NOT NULL,
              model_name VARCHAR,
              selected_case_ids_json JSON NOT NULL,
              metrics_json JSON,
              started_at DATETIME,
              finished_at DATETIME,
              created_at DATETIME NOT NULL,
              updated_at DATETIME
            )
            """
        )

        conn.exec_driver_sql(
            """
            CREATE TABLE agent_test_case_runs__new (
              id VARCHAR NOT NULL PRIMARY KEY,
              test_run_id VARCHAR NOT NULL,
              test_case_id VARCHAR NOT NULL,
              agent_run_id VARCHAR,
              status VARCHAR NOT NULL,
              passed BOOLEAN,
              score FLOAT,
              diff_json JSON,
              metrics_json JSON,
              error_text TEXT,
              started_at DATETIME,
              finished_at DATETIME,
              created_at DATETIME NOT NULL,
              updated_at DATETIME,
              CONSTRAINT uq_agent_test_case_runs_run_case UNIQUE (test_run_id, test_case_id),
              FOREIGN KEY(test_run_id) REFERENCES agent_test_runs(id) ON DELETE CASCADE,
              FOREIGN KEY(test_case_id) REFERENCES agent_test_cases(id) ON DELETE RESTRICT,
              FOREIGN KEY(agent_run_id) REFERENCES agent_runs(id) ON DELETE RESTRICT
            )
            """
        )

        conn.exec_driver_sql(
            """
            INSERT INTO agent_test_cases__new (
              id, agent_name, name, enabled, input_json, expected_json, notes, created_at, updated_at
            )
            SELECT
              id, agent_name, name, enabled, input_json, expected_json, notes, created_at, updated_at
            FROM agent_test_cases
            """
        )

        conn.exec_driver_sql(
            """
            INSERT INTO agent_test_runs__new (
              id, agent_name, name, status, model_name, selected_case_ids_json, metrics_json,
              started_at, finished_at, created_at, updated_at
            )
            SELECT
              id, agent_name, name, status, model_name, selected_case_ids_json, metrics_json,
              started_at, finished_at, created_at, updated_at
            FROM agent_test_runs
            """
        )

        conn.exec_driver_sql(
            """
            INSERT INTO agent_test_case_runs__new (
              id, test_run_id, test_case_id, agent_run_id, status, passed, score,
              diff_json, metrics_json, error_text, started_at, finished_at, created_at, updated_at
            )
            SELECT
              id, test_run_id, test_case_id, agent_run_id, status, passed, score,
              diff_json, metrics_json, error_text, started_at, finished_at, created_at, updated_at
            FROM agent_test_case_runs
            """
        )

        conn.exec_driver_sql(f"CREATE TABLE {backup_cases} AS SELECT * FROM agent_test_cases")
        conn.exec_driver_sql(f"CREATE TABLE {backup_runs} AS SELECT * FROM agent_test_runs")
        conn.exec_driver_sql(f"CREATE TABLE {backup_case_runs} AS SELECT * FROM agent_test_case_runs")

        conn.exec_driver_sql("DROP TABLE agent_test_case_runs")
        conn.exec_driver_sql("DROP TABLE agent_test_runs")
        conn.exec_driver_sql("DROP TABLE agent_test_cases")

        conn.exec_driver_sql("ALTER TABLE agent_test_cases__new RENAME TO agent_test_cases")
        conn.exec_driver_sql("ALTER TABLE agent_test_runs__new RENAME TO agent_test_runs")
        conn.exec_driver_sql("ALTER TABLE agent_test_case_runs__new RENAME TO agent_test_case_runs")

        conn.exec_driver_sql(
            "CREATE INDEX ix_agent_test_cases_agent_name ON agent_test_cases (agent_name)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX idx_agent_test_cases_agent_name_created_at ON agent_test_cases (agent_name, created_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX idx_agent_test_cases_agent_name_enabled ON agent_test_cases (agent_name, enabled)"
        )

        conn.exec_driver_sql(
            "CREATE INDEX ix_agent_test_runs_agent_name ON agent_test_runs (agent_name)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_agent_test_runs_status ON agent_test_runs (status)")
        conn.exec_driver_sql(
            "CREATE INDEX idx_agent_test_runs_agent_name_created_at ON agent_test_runs (agent_name, created_at)"
        )

        conn.exec_driver_sql(
            "CREATE INDEX ix_agent_test_case_runs_test_run_id ON agent_test_case_runs (test_run_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_agent_test_case_runs_test_case_id ON agent_test_case_runs (test_case_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_agent_test_case_runs_agent_run_id ON agent_test_case_runs (agent_run_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_agent_test_case_runs_status ON agent_test_case_runs (status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX idx_agent_test_case_runs_run_created_at ON agent_test_case_runs (test_run_id, created_at)"
        )

        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        violations = conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if violations:
            preview = "\n".join(str(v) for v in violations[:20])
            raise RuntimeError(
                "Foreign key violations after migration (showing up to 20):\n" + preview
            )

    print("Migration complete.")
    print(f"Backups: {backup_cases}, {backup_runs}, {backup_case_runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
