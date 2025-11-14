import logging
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

logger = logging.getLogger(__name__)


class PostgreSQLDatabase:
    def __init__(self):
        self._engine = None
        self._session_factory = None

    async def connect(self):
        if self._engine is None:
            try:
                db_url = str(settings.database.AUTH_DATABASE_URL)
                if db_url.startswith("postgresql://"):
                    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

                self._engine = create_async_engine(
                    db_url, pool_pre_ping=True, pool_recycle=3600, pool_size=10, max_overflow=20
                )

                async with self._engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))

                self._session_factory = async_sessionmaker(
                    self._engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
                )
                async with self._engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to PostgreSQL")
            except SQLAlchemyError as e:
                logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
                raise

    async def disconnect(self):
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("PostgreSQL connection closed")

    @property
    def session_factory(self):
        return self._session_factory


auth_db = PostgreSQLDatabase()


async def auth_db_connect():
    await auth_db.connect()


async def auth_db_disconnect():
    await auth_db.disconnect()


async def get_auth_db():
    async with auth_db.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_auth_session():
    async with auth_db.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
