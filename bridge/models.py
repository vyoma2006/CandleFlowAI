"""
bridge/models.py
────────────────
ORM table definitions for CandleFlow.

Tables:
  users       — one row per registered user
  portfolios  — one row per ticker per user (watchlist entries)
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from bridge.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=_new_uuid)
    username        = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # one user → many portfolio entries
    portfolio_entries = relationship(
        "Portfolio",
        back_populates="user",
        cascade="all, delete-orphan",   # deleting user removes their portfolio too
        lazy="select",
    )

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id       = Column(String, primary_key=True, default=_new_uuid)
    user_id  = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker   = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolio_entries")

    # Each user can only have a ticker once
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_user_ticker"),
    )

    def __repr__(self):
        return f"<Portfolio user_id={self.user_id} ticker={self.ticker}>"