"""
bridge/init_db.py
─────────────────
Run this ONCE to create the SQLite database and all tables.

Usage:
    cd CandleFlow          # project root
    python bridge/init_db.py

Safe to re-run — CREATE TABLE IF NOT EXISTS means it won't wipe existing data.
"""

import os
import sys

# Ensure project root is on path so imports resolve
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bridge.database import engine, DB_PATH, Base
from bridge.models import User, Portfolio   # noqa: F401 — imported so Base knows about them
from bridge.auth import create_user
from bridge.database import SessionLocal


def init():
    # Create the data/ directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Create all tables (safe — skips existing tables)
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialised at: {DB_PATH}")
    print(f"   Tables created: {list(Base.metadata.tables.keys())}")

    # ── Optional: migrate existing users.json into the DB ────────────────────
    old_json = os.path.join(os.path.dirname(__file__), "data", "users.json")
    if os.path.exists(old_json):
        import json
        with open(old_json, "r") as f:
            old_users = json.load(f)

        db = SessionLocal()
        migrated = 0
        for username, data in old_users.items():
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                user = User(
                    id=data.get("id", None),
                    username=username,
                    hashed_password=data["hashed_password"],
                )
                db.add(user)
                db.flush()

                for ticker in data.get("portfolio", []):
                    db.add(Portfolio(user_id=user.id, ticker=ticker))

                migrated += 1

        db.commit()
        db.close()
        if migrated:
            print(f"✅ Migrated {migrated} users from users.json → SQLite")
        else:
            print("ℹ️  users.json found but all users already exist in DB — skipped.")
    else:
        print("ℹ️  No users.json found — starting with empty user table.")

    print("\n🚀 Ready. Start your server with:")
    print("   uvicorn brain.main:app --reload --port 8000")


if __name__ == "__main__":
    init()