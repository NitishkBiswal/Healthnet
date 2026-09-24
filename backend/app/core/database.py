from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Declarative Base class for SQLAlchemy models."""

    metadata = MetaData()


async def init_db() -> None:
    """Initialize database engine and session maker."""
    global engine, async_session_maker
    if engine is None:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True,
        )
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )


async def close_db() -> None:
    """Close the database engine."""
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized")
    async with async_session_maker() as session:
        yield session
