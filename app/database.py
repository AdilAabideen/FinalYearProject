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
                "tool_names_json": "JSON",
            }
            for name, sql_type in llm_required.items():
                if name not in llm_existing:
                    conn.execute(text(f"ALTER TABLE agent_llm_calls ADD COLUMN {name} {sql_type}"))

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
