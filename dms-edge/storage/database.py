"""Local SQLite store backing the Violation Detection Agent's sliding-window rule
state — the edge equivalent of dms-backend/app/db/database.py, same SQLAlchemy/
SQLite pattern. Single-vehicle scope only (see storage/models.py).

See .claude/skills/dms-edge-dev/SKILL.md "New: Local Storage".
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import LOCAL_DB_PATH

os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{LOCAL_DB_PATH}", connect_args={"check_same_thread": False})
# expire_on_commit=False: agents open/commit/close a session per run() call, then
# hand the returned ORM object to the next agent (Alarm Agent, Cloud Hub Agent) —
# it must stay readable after the session that created it is closed.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

Base = declarative_base()


def init_db() -> None:
    from storage import models  # noqa: F401 — register models on Base before create_all

    Base.metadata.create_all(bind=engine)
