from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.base import Base
import app.models  # noqa: F401

# Add SQLite-specific connection args if using SQLite
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    connect_args=connect_args
)

if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-redef]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def ensure_runtime_schema_upgrades() -> None:
    """
    Apply additive runtime schema upgrades for environments without migrations.
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "agent_llm_calls" in table_names:
            llm_existing = {col["name"] for col in inspector.get_columns("agent_llm_calls")}
            llm_required: dict[str, str] = {
                "iteration": "INTEGER",
                "had_tool_calls": "BOOLEAN",
                "tool_call_count": "INTEGER",
                "tool_call_parse_source": "VARCHAR",
                "text_recovered_tool_call_count": "INTEGER DEFAULT 0",
                "native_tool_call_count": "INTEGER DEFAULT 0",
                "tool_names_json": "JSON",
            }
            for name, sql_type in llm_required.items():
                if name not in llm_existing:
                    conn.execute(text(f"ALTER TABLE agent_llm_calls ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_agent_llm_calls_tool_call_parse_source "
                    "ON agent_llm_calls (tool_call_parse_source)"
                )
            )

        if "agent_run_metrics" in table_names:
            metrics_existing = {col["name"] for col in inspector.get_columns("agent_run_metrics")}
            metrics_required: dict[str, str] = {
                "reliability_issue_count": "INTEGER DEFAULT 0",
                "reliability_error_count": "INTEGER DEFAULT 0",
                "finalization_failure_count": "INTEGER DEFAULT 0",
                "tool_recovery_failure_count": "INTEGER DEFAULT 0",
            }
            for name, sql_type in metrics_required.items():
                if name not in metrics_existing:
                    conn.execute(text(f"ALTER TABLE agent_run_metrics ADD COLUMN {name} {sql_type}"))

        if "agent_runs" in table_names:
            agent_runs_existing = {col["name"] for col in inspector.get_columns("agent_runs")}
            agent_runs_required: dict[str, str] = {
                "mas_run_id": "VARCHAR",
                "workflow_id": "VARCHAR",
                "workflow_version": "VARCHAR",
                "sequence_index": "INTEGER",
                "parent_handoff_id": "VARCHAR",
                "outgoing_handoff_id": "VARCHAR",
                "is_final_agent": "BOOLEAN",
            }
            for name, sql_type in agent_runs_required.items():
                if name not in agent_runs_existing:
                    conn.execute(text(f"ALTER TABLE agent_runs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_agent_runs_mas_run_created_at "
                    "ON agent_runs (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_agent_runs_workflow_created_at "
                    "ON agent_runs (workflow_id, created_at)"
                )
            )

        if "agent_run_reliability_issues" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE agent_run_reliability_issues (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        run_id VARCHAR NOT NULL,
                        agent_name VARCHAR NOT NULL,
                        model_name VARCHAR,
                        iteration INTEGER,
                        call_index INTEGER,
                        issue_code VARCHAR NOT NULL,
                        severity VARCHAR NOT NULL,
                        stage VARCHAR NOT NULL,
                        message TEXT NOT NULL,
                        details_json JSON,
                        assistant_raw_text TEXT,
                        tool_call_id VARCHAR,
                        tool_name VARCHAR,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(run_id) REFERENCES agent_runs(id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_agent_rel_issues_run_created ON agent_run_reliability_issues (run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_agent_rel_issues_run_issue_code ON agent_run_reliability_issues (run_id, issue_code)"
                )
            )
            conn.execute(
                text("CREATE INDEX ix_agent_run_reliability_issues_issue_code ON agent_run_reliability_issues (issue_code)")
            )
            conn.execute(
                text("CREATE INDEX ix_agent_run_reliability_issues_severity ON agent_run_reliability_issues (severity)")
            )
            conn.execute(
                text("CREATE INDEX ix_agent_run_reliability_issues_stage ON agent_run_reliability_issues (stage)")
            )
            conn.execute(
                text("CREATE INDEX ix_agent_run_reliability_issues_tool_call_id ON agent_run_reliability_issues (tool_call_id)")
            )

        if "mas_runs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_runs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        workflow_id VARCHAR NOT NULL,
                        workflow_version VARCHAR,
                        status VARCHAR NOT NULL,
                        input_schema_name VARCHAR,
                        input_json JSON NOT NULL,
                        metadata_json JSON,
                        current_agent_run_id VARCHAR,
                        current_gate_id VARCHAR,
                        final_output_json JSON,
                        error_text TEXT,
                        started_at DATETIME,
                        finished_at DATETIME,
                        duration_ms INTEGER,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_runs_workflow_created_at ON mas_runs (workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_runs_status_created_at ON mas_runs (status, created_at)"
                )
            )
        else:
            mas_runs_existing = {col["name"] for col in inspector.get_columns("mas_runs")}
            mas_runs_required: dict[str, str] = {
                "workflow_id": "VARCHAR NOT NULL DEFAULT ''",
                "workflow_version": "VARCHAR",
                "status": "VARCHAR NOT NULL DEFAULT 'created'",
                "input_schema_name": "VARCHAR",
                "input_json": "JSON",
                "metadata_json": "JSON",
                "current_agent_run_id": "VARCHAR",
                "current_gate_id": "VARCHAR",
                "final_output_json": "JSON",
                "error_text": "TEXT",
                "started_at": "DATETIME",
                "finished_at": "DATETIME",
                "duration_ms": "INTEGER",
            }
            for name, sql_type in mas_runs_required.items():
                if name not in mas_runs_existing:
                    conn.execute(text(f"ALTER TABLE mas_runs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_runs_workflow_created_at "
                    "ON mas_runs (workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_runs_status_created_at "
                    "ON mas_runs (status, created_at)"
                )
            )
            conn.execute(text("DROP INDEX IF EXISTS idx_mas_runs_case_id_created_at"))
            if "case_id" in mas_runs_existing:
                try:
                    conn.execute(text("ALTER TABLE mas_runs DROP COLUMN case_id"))
                except Exception:
                    pass

        if "mas_handoffs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_handoffs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        mas_run_id VARCHAR NOT NULL,
                        from_agent_run_id VARCHAR NOT NULL,
                        from_agent_name VARCHAR NOT NULL,
                        to_agent_name VARCHAR NOT NULL,
                        to_agent_run_id VARCHAR,
                        handoff_name VARCHAR NOT NULL,
                        payload_schema VARCHAR,
                        payload_json JSON NOT NULL,
                        status VARCHAR NOT NULL,
                        accepted_at DATETIME,
                        latency_ms INTEGER,
                        metadata_json JSON,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_handoffs_mas_created_at "
                    "ON mas_handoffs (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_handoffs_from_run_created_at "
                    "ON mas_handoffs (from_agent_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_handoffs_to_agent_created_at "
                    "ON mas_handoffs (to_agent_name, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_handoffs_status_created_at "
                    "ON mas_handoffs (status, created_at)"
                )
            )
        else:
            mas_handoffs_existing = {col["name"] for col in inspector.get_columns("mas_handoffs")}
            mas_handoffs_required: dict[str, str] = {
                "mas_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "from_agent_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "from_agent_name": "VARCHAR NOT NULL DEFAULT ''",
                "to_agent_name": "VARCHAR NOT NULL DEFAULT ''",
                "to_agent_run_id": "VARCHAR",
                "handoff_name": "VARCHAR NOT NULL DEFAULT ''",
                "payload_schema": "VARCHAR",
                "payload_json": "JSON",
                "status": "VARCHAR NOT NULL DEFAULT 'created'",
                "accepted_at": "DATETIME",
                "latency_ms": "INTEGER",
                "metadata_json": "JSON",
            }
            for name, sql_type in mas_handoffs_required.items():
                if name not in mas_handoffs_existing:
                    conn.execute(text(f"ALTER TABLE mas_handoffs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_handoffs_mas_created_at "
                    "ON mas_handoffs (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_handoffs_from_run_created_at "
                    "ON mas_handoffs (from_agent_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_handoffs_to_agent_created_at "
                    "ON mas_handoffs (to_agent_name, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_handoffs_status_created_at "
                    "ON mas_handoffs (status, created_at)"
                )
            )

        if "mas_gate_evaluations" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_gate_evaluations (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        mas_run_id VARCHAR NOT NULL,
                        gate_id VARCHAR NOT NULL,
                        ready BOOLEAN NOT NULL,
                        satisfied_sources_json JSON NOT NULL,
                        missing_sources_json JSON NOT NULL,
                        next_target VARCHAR,
                        handoffs_to_target_json JSON,
                        metadata_json JSON,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_gate_evals_mas_created_at "
                    "ON mas_gate_evaluations (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_gate_evals_gate_created_at "
                    "ON mas_gate_evaluations (gate_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_gate_evals_ready_created_at "
                    "ON mas_gate_evaluations (ready, created_at)"
                )
            )
        else:
            mas_gate_evals_existing = {col["name"] for col in inspector.get_columns("mas_gate_evaluations")}
            mas_gate_evals_required: dict[str, str] = {
                "mas_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "gate_id": "VARCHAR NOT NULL DEFAULT ''",
                "ready": "BOOLEAN NOT NULL DEFAULT 0",
                "satisfied_sources_json": "JSON",
                "missing_sources_json": "JSON",
                "next_target": "VARCHAR",
                "handoffs_to_target_json": "JSON",
                "metadata_json": "JSON",
            }
            for name, sql_type in mas_gate_evals_required.items():
                if name not in mas_gate_evals_existing:
                    conn.execute(text(f"ALTER TABLE mas_gate_evaluations ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_gate_evals_mas_created_at "
                    "ON mas_gate_evaluations (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_gate_evals_gate_created_at "
                    "ON mas_gate_evaluations (gate_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_gate_evals_ready_created_at "
                    "ON mas_gate_evaluations (ready, created_at)"
                )
            )

        if "mas_final_outputs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_final_outputs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        mas_run_id VARCHAR NOT NULL,
                        final_agent_run_id VARCHAR NOT NULL,
                        workflow_id VARCHAR,
                        workflow_version VARCHAR,
                        output_json JSON NOT NULL,
                        metadata_json JSON,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_final_outputs_mas_created_at "
                    "ON mas_final_outputs (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_final_outputs_agent_created_at "
                    "ON mas_final_outputs (final_agent_run_id, created_at)"
                )
            )
        else:
            mas_final_outputs_existing = {col["name"] for col in inspector.get_columns("mas_final_outputs")}
            mas_final_outputs_required: dict[str, str] = {
                "mas_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "final_agent_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "workflow_id": "VARCHAR",
                "workflow_version": "VARCHAR",
                "output_json": "JSON",
                "metadata_json": "JSON",
            }
            for name, sql_type in mas_final_outputs_required.items():
                if name not in mas_final_outputs_existing:
                    conn.execute(text(f"ALTER TABLE mas_final_outputs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_final_outputs_mas_created_at "
                    "ON mas_final_outputs (mas_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_final_outputs_agent_created_at "
                    "ON mas_final_outputs (final_agent_run_id, created_at)"
                )
            )

        if "mas_events" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_events (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        mas_run_id VARCHAR NOT NULL,
                        seq INTEGER NOT NULL,
                        event_type VARCHAR NOT NULL,
                        workflow_id VARCHAR,
                        agent_run_id VARCHAR,
                        agent_name VARCHAR,
                        handoff_id VARCHAR,
                        gate_evaluation_id VARCHAR,
                        final_output_id VARCHAR,
                        status VARCHAR,
                        payload_json JSON,
                        payload_text TEXT,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX uq_mas_events_run_seq "
                    "ON mas_events (mas_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_events_run_seq "
                    "ON mas_events (mas_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_events_type_created_at "
                    "ON mas_events (event_type, created_at)"
                )
            )
        else:
            mas_events_existing = {col["name"] for col in inspector.get_columns("mas_events")}
            mas_events_required: dict[str, str] = {
                "mas_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "seq": "INTEGER NOT NULL DEFAULT 0",
                "event_type": "VARCHAR NOT NULL DEFAULT ''",
                "workflow_id": "VARCHAR",
                "agent_run_id": "VARCHAR",
                "agent_name": "VARCHAR",
                "handoff_id": "VARCHAR",
                "gate_evaluation_id": "VARCHAR",
                "final_output_id": "VARCHAR",
                "status": "VARCHAR",
                "payload_json": "JSON",
                "payload_text": "TEXT",
            }
            for name, sql_type in mas_events_required.items():
                if name not in mas_events_existing:
                    conn.execute(text(f"ALTER TABLE mas_events ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_mas_events_run_seq "
                    "ON mas_events (mas_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_events_run_seq "
                    "ON mas_events (mas_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_events_type_created_at "
                    "ON mas_events (event_type, created_at)"
                )
            )

        if "mas_run_metrics" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_run_metrics (
                        mas_run_id VARCHAR NOT NULL PRIMARY KEY,
                        status VARCHAR NOT NULL,
                        duration_ms INTEGER,
                        agent_run_count INTEGER NOT NULL DEFAULT 0,
                        handoff_count INTEGER NOT NULL DEFAULT 0,
                        gate_evaluation_count INTEGER NOT NULL DEFAULT 0,
                        completed_agent_count INTEGER NOT NULL DEFAULT 0,
                        failed_agent_count INTEGER NOT NULL DEFAULT 0,
                        input_tokens_total INTEGER NOT NULL DEFAULT 0,
                        output_tokens_total INTEGER NOT NULL DEFAULT 0,
                        tokens_total INTEGER NOT NULL DEFAULT 0,
                        llm_call_count_total INTEGER NOT NULL DEFAULT 0,
                        tool_call_count_total INTEGER NOT NULL DEFAULT 0,
                        tool_error_count_total INTEGER NOT NULL DEFAULT 0,
                        cost_usd_total FLOAT,
                        cost_usd_per_agent_run FLOAT,
                        agent_failure_count INTEGER NOT NULL DEFAULT 0,
                        reliability_issue_count INTEGER NOT NULL DEFAULT 0,
                        reliability_error_count INTEGER NOT NULL DEFAULT 0,
                        finalization_failure_count INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME,
                        FOREIGN KEY(mas_run_id) REFERENCES mas_runs(id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_run_metrics_status_created "
                    "ON mas_run_metrics (status, created_at)"
                )
            )
        else:
            mas_run_metrics_existing = {col["name"] for col in inspector.get_columns("mas_run_metrics")}
            mas_run_metrics_required: dict[str, str] = {
                "status": "VARCHAR NOT NULL DEFAULT 'created'",
                "duration_ms": "INTEGER",
                "agent_run_count": "INTEGER NOT NULL DEFAULT 0",
                "handoff_count": "INTEGER NOT NULL DEFAULT 0",
                "gate_evaluation_count": "INTEGER NOT NULL DEFAULT 0",
                "completed_agent_count": "INTEGER NOT NULL DEFAULT 0",
                "failed_agent_count": "INTEGER NOT NULL DEFAULT 0",
                "input_tokens_total": "INTEGER NOT NULL DEFAULT 0",
                "output_tokens_total": "INTEGER NOT NULL DEFAULT 0",
                "tokens_total": "INTEGER NOT NULL DEFAULT 0",
                "llm_call_count_total": "INTEGER NOT NULL DEFAULT 0",
                "tool_call_count_total": "INTEGER NOT NULL DEFAULT 0",
                "tool_error_count_total": "INTEGER NOT NULL DEFAULT 0",
                "cost_usd_total": "FLOAT",
                "cost_usd_per_agent_run": "FLOAT",
                "agent_failure_count": "INTEGER NOT NULL DEFAULT 0",
                "reliability_issue_count": "INTEGER NOT NULL DEFAULT 0",
                "reliability_error_count": "INTEGER NOT NULL DEFAULT 0",
                "finalization_failure_count": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, sql_type in mas_run_metrics_required.items():
                if name not in mas_run_metrics_existing:
                    conn.execute(text(f"ALTER TABLE mas_run_metrics ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_run_metrics_status_created "
                    "ON mas_run_metrics (status, created_at)"
                )
            )

        if "mas_test_cases" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_test_cases (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        workflow_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        enabled BOOLEAN NOT NULL,
                        input_json JSON NOT NULL,
                        expected_json JSON NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_test_cases_workflow_created_at "
                    "ON mas_test_cases (workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_test_cases_workflow_enabled "
                    "ON mas_test_cases (workflow_id, enabled)"
                )
            )
        else:
            mas_test_cases_existing = {col["name"] for col in inspector.get_columns("mas_test_cases")}
            mas_test_cases_required: dict[str, str] = {
                "workflow_id": "VARCHAR NOT NULL DEFAULT ''",
                "name": "VARCHAR NOT NULL DEFAULT ''",
                "enabled": "BOOLEAN NOT NULL DEFAULT 1",
                "input_json": "JSON",
                "expected_json": "JSON",
            }
            for name, sql_type in mas_test_cases_required.items():
                if name not in mas_test_cases_existing:
                    conn.execute(text(f"ALTER TABLE mas_test_cases ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_test_cases_workflow_created_at "
                    "ON mas_test_cases (workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_test_cases_workflow_enabled "
                    "ON mas_test_cases (workflow_id, enabled)"
                )
            )

        if "mas_test_runs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_test_runs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        workflow_id VARCHAR NOT NULL,
                        model_name VARCHAR,
                        name VARCHAR,
                        status VARCHAR NOT NULL,
                        selected_case_ids_json JSON NOT NULL,
                        metrics_json JSON,
                        started_at DATETIME,
                        finished_at DATETIME,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_test_runs_workflow_created_at "
                    "ON mas_test_runs (workflow_id, created_at)"
                )
            )
        else:
            mas_test_runs_existing = {col["name"] for col in inspector.get_columns("mas_test_runs")}
            mas_test_runs_required: dict[str, str] = {
                "workflow_id": "VARCHAR NOT NULL DEFAULT ''",
                "model_name": "VARCHAR",
                "name": "VARCHAR",
                "status": "VARCHAR NOT NULL DEFAULT 'created'",
                "selected_case_ids_json": "JSON",
                "metrics_json": "JSON",
                "started_at": "DATETIME",
                "finished_at": "DATETIME",
            }
            for name, sql_type in mas_test_runs_required.items():
                if name not in mas_test_runs_existing:
                    conn.execute(text(f"ALTER TABLE mas_test_runs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_test_runs_workflow_created_at "
                    "ON mas_test_runs (workflow_id, created_at)"
                )
            )

        if "mas_test_case_runs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE mas_test_case_runs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        test_run_id VARCHAR NOT NULL,
                        test_case_id VARCHAR NOT NULL,
                        mas_run_id VARCHAR,
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
                        FOREIGN KEY(test_run_id) REFERENCES mas_test_runs(id) ON DELETE CASCADE,
                        FOREIGN KEY(test_case_id) REFERENCES mas_test_cases(id) ON DELETE RESTRICT,
                        FOREIGN KEY(mas_run_id) REFERENCES mas_runs(id) ON DELETE RESTRICT
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX uq_mas_test_case_runs_run_case "
                    "ON mas_test_case_runs (test_run_id, test_case_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_mas_test_case_runs_run_created_at "
                    "ON mas_test_case_runs (test_run_id, created_at)"
                )
            )
        else:
            mas_test_case_runs_existing = {col["name"] for col in inspector.get_columns("mas_test_case_runs")}
            mas_test_case_runs_required: dict[str, str] = {
                "test_run_id": "VARCHAR",
                "test_case_id": "VARCHAR",
                "mas_run_id": "VARCHAR",
                "status": "VARCHAR NOT NULL DEFAULT 'created'",
                "passed": "BOOLEAN",
                "score": "FLOAT",
                "diff_json": "JSON",
                "metrics_json": "JSON",
                "error_text": "TEXT",
                "started_at": "DATETIME",
                "finished_at": "DATETIME",
            }
            for name, sql_type in mas_test_case_runs_required.items():
                if name not in mas_test_case_runs_existing:
                    conn.execute(text(f"ALTER TABLE mas_test_case_runs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_mas_test_case_runs_run_case "
                    "ON mas_test_case_runs (test_run_id, test_case_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mas_test_case_runs_run_created_at "
                    "ON mas_test_case_runs (test_run_id, created_at)"
                )
            )

def get_db():
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
