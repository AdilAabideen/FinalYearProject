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
                "swarm_run_id": "VARCHAR",
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
                    "CREATE INDEX IF NOT EXISTS idx_agent_runs_swarm_run_created_at "
                    "ON agent_runs (swarm_run_id, created_at)"
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

        if "swarm_runs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE swarm_runs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        workflow_id VARCHAR NOT NULL,
                        workflow_version VARCHAR,
                        status VARCHAR NOT NULL,
                        case_id VARCHAR,
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
                    "CREATE INDEX idx_swarm_runs_workflow_created_at ON swarm_runs (workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_runs_status_created_at ON swarm_runs (status, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_runs_case_id_created_at ON swarm_runs (case_id, created_at)"
                )
            )
        else:
            swarm_runs_existing = {col["name"] for col in inspector.get_columns("swarm_runs")}
            swarm_runs_required: dict[str, str] = {
                "workflow_id": "VARCHAR NOT NULL DEFAULT ''",
                "workflow_version": "VARCHAR",
                "status": "VARCHAR NOT NULL DEFAULT 'created'",
                "case_id": "VARCHAR",
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
            for name, sql_type in swarm_runs_required.items():
                if name not in swarm_runs_existing:
                    conn.execute(text(f"ALTER TABLE swarm_runs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_runs_workflow_created_at "
                    "ON swarm_runs (workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_runs_status_created_at "
                    "ON swarm_runs (status, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_runs_case_id_created_at "
                    "ON swarm_runs (case_id, created_at)"
                )
            )

        if "swarm_handoffs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE swarm_handoffs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        swarm_run_id VARCHAR NOT NULL,
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
                    "CREATE INDEX idx_swarm_handoffs_swarm_created_at "
                    "ON swarm_handoffs (swarm_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_handoffs_from_run_created_at "
                    "ON swarm_handoffs (from_agent_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_handoffs_to_agent_created_at "
                    "ON swarm_handoffs (to_agent_name, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_handoffs_status_created_at "
                    "ON swarm_handoffs (status, created_at)"
                )
            )
        else:
            swarm_handoffs_existing = {col["name"] for col in inspector.get_columns("swarm_handoffs")}
            swarm_handoffs_required: dict[str, str] = {
                "swarm_run_id": "VARCHAR NOT NULL DEFAULT ''",
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
            for name, sql_type in swarm_handoffs_required.items():
                if name not in swarm_handoffs_existing:
                    conn.execute(text(f"ALTER TABLE swarm_handoffs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_handoffs_swarm_created_at "
                    "ON swarm_handoffs (swarm_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_handoffs_from_run_created_at "
                    "ON swarm_handoffs (from_agent_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_handoffs_to_agent_created_at "
                    "ON swarm_handoffs (to_agent_name, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_handoffs_status_created_at "
                    "ON swarm_handoffs (status, created_at)"
                )
            )

        if "swarm_gate_evaluations" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE swarm_gate_evaluations (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        swarm_run_id VARCHAR NOT NULL,
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
                    "CREATE INDEX idx_swarm_gate_evals_swarm_created_at "
                    "ON swarm_gate_evaluations (swarm_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_gate_evals_gate_created_at "
                    "ON swarm_gate_evaluations (gate_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_gate_evals_ready_created_at "
                    "ON swarm_gate_evaluations (ready, created_at)"
                )
            )
        else:
            swarm_gate_evals_existing = {col["name"] for col in inspector.get_columns("swarm_gate_evaluations")}
            swarm_gate_evals_required: dict[str, str] = {
                "swarm_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "gate_id": "VARCHAR NOT NULL DEFAULT ''",
                "ready": "BOOLEAN NOT NULL DEFAULT 0",
                "satisfied_sources_json": "JSON",
                "missing_sources_json": "JSON",
                "next_target": "VARCHAR",
                "handoffs_to_target_json": "JSON",
                "metadata_json": "JSON",
            }
            for name, sql_type in swarm_gate_evals_required.items():
                if name not in swarm_gate_evals_existing:
                    conn.execute(text(f"ALTER TABLE swarm_gate_evaluations ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_gate_evals_swarm_created_at "
                    "ON swarm_gate_evaluations (swarm_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_gate_evals_gate_created_at "
                    "ON swarm_gate_evaluations (gate_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_gate_evals_ready_created_at "
                    "ON swarm_gate_evaluations (ready, created_at)"
                )
            )

        if "swarm_final_outputs" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE swarm_final_outputs (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        swarm_run_id VARCHAR NOT NULL,
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
                    "CREATE INDEX idx_swarm_final_outputs_swarm_created_at "
                    "ON swarm_final_outputs (swarm_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_final_outputs_agent_created_at "
                    "ON swarm_final_outputs (final_agent_run_id, created_at)"
                )
            )
        else:
            swarm_final_outputs_existing = {col["name"] for col in inspector.get_columns("swarm_final_outputs")}
            swarm_final_outputs_required: dict[str, str] = {
                "swarm_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "final_agent_run_id": "VARCHAR NOT NULL DEFAULT ''",
                "workflow_id": "VARCHAR",
                "workflow_version": "VARCHAR",
                "output_json": "JSON",
                "metadata_json": "JSON",
            }
            for name, sql_type in swarm_final_outputs_required.items():
                if name not in swarm_final_outputs_existing:
                    conn.execute(text(f"ALTER TABLE swarm_final_outputs ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_final_outputs_swarm_created_at "
                    "ON swarm_final_outputs (swarm_run_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_final_outputs_agent_created_at "
                    "ON swarm_final_outputs (final_agent_run_id, created_at)"
                )
            )

        if "swarm_events" not in table_names:
            conn.execute(
                text(
                    """
                    CREATE TABLE swarm_events (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        swarm_run_id VARCHAR NOT NULL,
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
                    "CREATE UNIQUE INDEX uq_swarm_events_run_seq "
                    "ON swarm_events (swarm_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_events_run_seq "
                    "ON swarm_events (swarm_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_swarm_events_type_created_at "
                    "ON swarm_events (event_type, created_at)"
                )
            )
        else:
            swarm_events_existing = {col["name"] for col in inspector.get_columns("swarm_events")}
            swarm_events_required: dict[str, str] = {
                "swarm_run_id": "VARCHAR NOT NULL DEFAULT ''",
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
            for name, sql_type in swarm_events_required.items():
                if name not in swarm_events_existing:
                    conn.execute(text(f"ALTER TABLE swarm_events ADD COLUMN {name} {sql_type}"))
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_swarm_events_run_seq "
                    "ON swarm_events (swarm_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_events_run_seq "
                    "ON swarm_events (swarm_run_id, seq)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_swarm_events_type_created_at "
                    "ON swarm_events (event_type, created_at)"
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
