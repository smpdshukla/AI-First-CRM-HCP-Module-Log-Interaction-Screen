"""
db.py
-----
SQLAlchemy setup for persisting interaction state to Postgres, replacing
the in-memory SESSIONS dict.

We keep the schema deliberately simple: one row per interaction, storing
the entire InteractionState as a JSON blob in a single column. This
mirrors what SESSIONS[interaction_id] = state was doing, just persisted
to disk instead of RAM. A fully normalized schema (separate tables for
attendees, materials, etc.) is unnecessary for this assignment's scope
and would slow you down without adding value to the grade.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Add it to your .env file, e.g.\n"
        "DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/hcp_crm"
    )

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class InteractionRecord(Base):
    """One row per interaction. `state` holds the full InteractionState dict,
    including chat history (serialized as plain JSON-safe dicts by main.py's
    _serialize(), then reconstructed back into LangChain message objects on
    load) so the agent retains conversation memory across requests."""

    __tablename__ = "interactions"

    interaction_id = Column(String, primary_key=True, index=True)
    state = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def init_db():
    """Create tables if they don't exist yet. Call this once on app startup."""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Simple session factory. Caller is responsible for closing the session
    (we use a `with` pattern in main.py rather than FastAPI Depends, to keep
    this close to your existing SESSIONS-dict style and minimize the diff)."""
    return SessionLocal()


# --- convenience helpers used by main.py --------------------------------

def save_interaction(interaction_id: str, state: dict) -> None:
    """Insert or update the interaction's state (upsert)."""
    db = get_db_session()
    try:
        record = db.get(InteractionRecord, interaction_id)
        if record:
            record.state = state
        else:
            record = InteractionRecord(interaction_id=interaction_id, state=state)
            db.add(record)
        db.commit()
    finally:
        db.close()


def load_interaction(interaction_id: str) -> dict | None:
    """Return the stored state dict, or None if not found."""
    db = get_db_session()
    try:
        record = db.get(InteractionRecord, interaction_id)
        return record.state if record else None
    finally:
        db.close()