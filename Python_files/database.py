"""
database.py
===========
Handles the database connection.

For local development  → SQLite (labh_offset.db file in project folder)
For production server  → PostgreSQL (set DATABASE_URL environment variable)

You never need to change any other file when switching databases.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── DATABASE URL ──────────────────────────────────────────────────────────────
# Reads from environment variable DATABASE_URL if set (Render / VPS)
# Falls back to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///labh_offset.db")

# ── ENGINE ────────────────────────────────────────────────────────────────────
if DATABASE_URL.startswith("sqlite"):
    # SQLite needs connect_args for threading (FastAPI runs multiple threads)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True to see all SQL queries in terminal (useful for debugging)
    )

    # Enable foreign key enforcement for SQLite (off by default)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrent read performance

else:
    # PostgreSQL — no special args needed
    engine = create_engine(DATABASE_URL, echo=False)

# ── SESSION FACTORY ───────────────────────────────────────────────────────────
# Each API request gets its own session (database connection)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── BASE CLASS ────────────────────────────────────────────────────────────────
# All ORM models inherit from this
class Base(DeclarativeBase):
    pass

# ── DEPENDENCY ────────────────────────────────────────────────────────────────
# FastAPI injects this into every route that needs database access
# It automatically closes the session after the request is done
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
