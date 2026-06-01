"""
bridge/database.py
──────────────────
SQLAlchemy engine + session setup for CandleFlow.
Database file lives at bridge/data/candleflow.db
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ── DB file path — always relative to this file (bridge/) ─────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "candleflow.db")
DB_URL   = f"sqlite:///{DB_PATH}"

# ── Engine ─────────────────────────────────────────────────────────────────────
# check_same_thread=False is required for SQLite with FastAPI
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,   # set True to log all SQL statements during dev
)

# ── Session factory ────────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Base class for all ORM models ──────────────────────────────────────────────
Base = declarative_base()


# ── FastAPI dependency — yields a DB session, always closes after request ──────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()