from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import Settings


class Base(DeclarativeBase):
    pass


def _normalize_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return database_url


def _ensure_sqlite_dir(url: str) -> None:
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return
    raw = url[len(prefix) :]
    path = Path.cwd() / raw[2:] if raw.startswith("./") else Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)


class Database:
    """Async SQLAlchemy engine wrapper. Works against PostgreSQL (asyncpg) in
    production and SQLite (aiosqlite) for local dev/tests, using the same models."""

    def __init__(self, settings: Settings):
        url = _normalize_url(settings.database_url)
        _ensure_sqlite_dir(url)
        self.url = url
        self.engine = create_async_engine(url, echo=False, future=True, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session
