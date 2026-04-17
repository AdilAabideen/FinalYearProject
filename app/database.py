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
    if "agent_llm_calls" not in table_names:
        return

    existing = {col["name"] for col in inspector.get_columns("agent_llm_calls")}
    required: dict[str, str] = {
        "iteration": "INTEGER",
        "had_tool_calls": "BOOLEAN",
        "tool_call_count": "INTEGER",
        "tool_names_json": "JSON",
    }

    missing = [(name, sql_type) for name, sql_type in required.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, sql_type in missing:
            conn.execute(text(f"ALTER TABLE agent_llm_calls ADD COLUMN {name} {sql_type}"))

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
