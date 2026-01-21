import logging
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient
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


class MongoDatabase:
    def __init__(self):
        self._client = None
        self._database = None

    async def connect(self):
        if self._client is None:
            try:
                logger.info("Connecting to MongoDB...")
                self._client = AsyncIOMotorClient(settings.database.MONGO_DATABASE_URL, serverSelectionTimeoutMS=5000)

                await self._client.server_info()

                db_name = getattr(settings.database, "MONGO_DB_NAME", "starranja")
                self._database = self._client[db_name]

                logger.info(f"Successfully connected to MongoDB: {db_name}")

            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise

    async def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed")

    @property
    def database(self):
        return self._database


# Singleton Instance
mongo_db = MongoDatabase()


async def mongo_db_connect():
    """Wrapper to connect to MongoDB (calls the class method)."""
    await mongo_db.connect()


async def mongo_db_disconnect():
    """Wrapper to disconnect from MongoDB."""
    await mongo_db.disconnect()


def get_mongo_db():
    """Dependency to retrieve the MongoDB database object."""
    return mongo_db.database
