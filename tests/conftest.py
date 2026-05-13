"""Conftest test coverage."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

TESTS_ROOT = Path(__file__).resolve().parent
FIXTURES_ROOT = TESTS_ROOT / "fixtures"
REPO_ROOT = TESTS_ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app.models  # noqa: E402,F401
from app.api.api import api_router  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models.base import Base  # noqa: E402


@pytest.fixture
def load_json_fixture():
    """Load json fixture."""
    # Read the current value.
    def _load(relative_path: str) -> dict | list:
        """Load the value."""
        # Read the current value.
        return json.loads((FIXTURES_ROOT / relative_path).read_text())

    return _load


@pytest.fixture
def sqlite_url(tmp_path: Path) -> str:
    """Handle url."""
    # Keep the main step clear.
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def db_engine(sqlite_url: str):
    """Handle engine."""
    # Keep the main step clear.
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    """Handle factory."""
    # Keep the main step clear.
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture
def db_session(session_factory) -> Iterator[Session]:
    """Handle session."""
    # Keep the main step clear.
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_app(session_factory) -> FastAPI:
    """Handle app."""
    # Keep the main step clear.
    app = FastAPI()
    app.include_router(api_router, prefix="/api")

    @app.get("/")
    def root():
        """Handle the value."""
        # Keep the main step clear.
        return {"message": "Welcome to Emergency Severity Index Multi Agent V Monolithic Agent System"}

    @app.get("/health")
    def health_check():
        """Handle check."""
        # Keep the main step clear.
        return {"status": "healthy"}

    def _override_get_db():
        """Handle get db."""
        # Keep the main step clear.
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    """Handle the value."""
    # Keep the main step clear.
    with TestClient(test_app) as test_client:
        yield test_client
