import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_db_ready = False


def _create_engine() -> AsyncEngine:
    # Created lazily: importing the driver (aiosqlite needs the sqlite3 module,
    # which some serverless Python runtimes lack) must never break app import.
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db() -> bool:
    """Creates tables. A missing or broken database must not take down the
    stateless endpoints (chords, explore, analyze), so failures are logged."""
    global _db_ready
    if _db_ready:
        return True
    try:
        async with _create_engine().begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        _db_ready = True
    except Exception:  # noqa: BLE001 - missing driver, network or auth errors
        logger.exception("Database initialisation failed; persistence endpoints will return 503")
    return _db_ready


async def get_session() -> AsyncIterator[AsyncSession]:
    if not await init_db() or _sessionmaker is None:
        raise HTTPException(status_code=503, detail="La base de datos no está disponible")
    async with _sessionmaker() as session:
        yield session
