"""
VitalGuard v2 — Async SQLite Database
Uses SQLAlchemy async with aiosqlite.
Schema designed for easy PostgreSQL migration.
"""

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

_db_path = Path(__file__).resolve().parent.parent / "vitalguard.db"
DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
