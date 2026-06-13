"""
bridge/auth.py
──────────────
JWT + bcrypt auth layer backed by SQLite via SQLAlchemy.
Replaces the old users.json approach entirely.

Deps:  pip install sqlalchemy passlib[bcrypt] python-jose[cryptography]
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from bridge.database import get_db
from bridge.models import User, Portfolio

# ── JWT config ─────────────────────────────────────────────────────────────────
# Set CANDLEFLOW_SECRET in your .env file.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("CANDLEFLOW_SECRET", "CHANGE_THIS_IN_PRODUCTION_SET_IN_DOT_ENV")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8   # 8-hour sessions

# ── Password hashing ───────────────────────────────────────────────────────────
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ──────────────────────────────────────────────────────────────────────────────
# USER CRUD
# ──────────────────────────────────────────────────────────────────────────────

def get_user_by_username(username: str, db: Session) -> Optional[User]:
    return db.query(User).filter(User.username == username.lower().strip()).first()


def create_user(username: str, password: str, db: Session) -> User:
    # normalize inputs
    key = username.lower().strip()
    password = password.strip()

    # validations
    if len(key) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters."
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters."
        )

    # bcrypt hard limit safety
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot exceed 72 bytes."
        )

    # duplicate user check
    if db.query(User).filter(User.username == key).first():
        raise HTTPException(
            status_code=409,
            detail="Username already taken."
        )

    # safe hash (IMPORTANT FIX)
    hashed_password = pwd_context.hash(password[:72])

    # create user
    user = User(
        username=key,
        hashed_password=hashed_password
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username, password, db):
    user = db.query(User).filter(User.username == username.lower().strip()).first()

    if not user:
        return None

    password = password.strip()

    if len(password.encode("utf-8")) > 72:
        return None

    if not pwd_context.verify(password[:72], user.hashed_password):
        return None

    return user


# ──────────────────────────────────────────────────────────────────────────────
# JWT
# ──────────────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── FastAPI dependency — decodes JWT and returns the User ORM object ───────────
def get_current_user(
    token: str       = Depends(oauth2_scheme),
    db:    Session   = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = get_user_by_username(username, db)
    if not user:
        raise credentials_error
    return user


# ──────────────────────────────────────────────────────────────────────────────
# PORTFOLIO CRUD
# ──────────────────────────────────────────────────────────────────────────────

def get_user_portfolio(user: User, db: Session) -> list[str]:
    """Returns a list of ticker strings for the user, ordered by when they were added."""
    entries = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.added_at.asc())
        .all()
    )
    return [e.ticker for e in entries]


def toggle_user_ticker(ticker: str, user: User, db: Session) -> list[str]:
    """
    If ticker is NOT in the user's portfolio → add it.
    If ticker IS already there → remove it.
    Returns the updated list of tickers.
    """
    existing = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id, Portfolio.ticker == ticker)
        .first()
    )

    if existing:
        db.delete(existing)
    else:
        db.add(Portfolio(user_id=user.id, ticker=ticker))

    db.commit()
    return get_user_portfolio(user, db)