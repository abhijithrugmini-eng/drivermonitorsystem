"""Shared pytest fixtures — an isolated, in-memory SQLite DB per test (StaticPool
so every get_db() call shares the same in-memory connection) via FastAPI's
dependency-override mechanism, so nothing here touches app/config.py's real
storage/dms.db path.

Run from dms-backend/: pytest tests/
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.rule_agents import violation_rules


@pytest.fixture
def client():
    # violation_rules keeps its sliding windows in a module-level global keyed by
    # (DB-assigned) vehicle_id, which each test's fresh in-memory DB reassigns from
    # scratch — reset it so state can't leak between tests.
    violation_rules.reset_windows()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
