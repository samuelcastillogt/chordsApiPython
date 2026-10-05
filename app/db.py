import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
_db_ready = False


async def init_db() -> bool:
    """Creates tables on startup. A broken database must not take down the
    stateless endpoints (chords, explore, analyze), so failures are logged."""
    global _db_ready
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        _db_ready = True
    except Exception:  # noqa: BLE001 - any driver/network error
        logger.exception("Database initialisation failed; persistence endpoints will return 503")
        _db_ready = False
    return _db_ready


async def get_session() -> AsyncIterator[AsyncSession]:
    if not _db_ready and not await init_db():
        raise HTTPException(status_code=503, detail="La base de datos no está disponible")
    async with SessionLocal() as session:
        yield session
