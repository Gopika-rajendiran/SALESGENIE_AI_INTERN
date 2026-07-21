"""
database/connection.py
Central PostgreSQL connection for the whole SalesGenie AI project.
All modules (module1..module6) should import get_db / SessionLocal from here
so everyone shares ONE connection pool instead of opening their own.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/salesgenie",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables that don't exist yet.
    Safe to call multiple times (idempotent) — existing tables are left untouched.
    Import all models here so Base.metadata knows about them before create_all().
    """
    from database import models  # noqa: F401  (ensures models are registered)
    Base.metadata.create_all(bind=engine)
