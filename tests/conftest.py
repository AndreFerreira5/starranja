import os
from collections.abc import AsyncGenerator
from secrets import token_hex

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Load .env.test before other imports that use settings
load_dotenv(".env.test")

# Now import after loading env
from src.config import settings  # noqa: E402
from src.db.connection import get_auth_db  # noqa: E402
from src.main import app  # noqa: E402
from src.models.auth import Base  # noqa: E402

# Set PASETO secret key if not in environment
if "PASETO_SECRET_KEY" not in os.environ:
    settings.auth.PASETO_SECRET_KEY = token_hex(32)

# Test database URL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise ValueError("TEST_DATABASE_URL not found. Make sure .env.test exists and contains TEST_DATABASE_URL")


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Create a test database engine.
    Creates tables and initializes roles before each test, drops them after.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        # Enable uuid extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Initialize roles for each test
        await conn.execute(
            text("""
            INSERT INTO roles (name) VALUES
                ('mecanico'),
                ('mecanico_gerente'),
                ('gerente'),
                ('admin')
            ON CONFLICT (name) DO NOTHING;
        """)
        )

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """
    Create a test database session.
    Each test gets a fresh session.
    """
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """
    Create an async test client with database override.
    This ensures all API calls use the test database.
    """

    async def override_get_auth_db():
        """Override the get_auth_db dependency"""
        yield test_session

    # Override the dependency
    app.dependency_overrides[get_auth_db] = override_get_auth_db

    # Create test client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user registration data for tests"""
    return {
        "username": "testuser",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "email": "test@example.com",
        "role": "mecanico",
    }


@pytest.fixture
def sample_user_data_no_email():
    """Sample user registration data without email"""
    return {
        "username": "testuser_no_email",
        "password": "SecurePass123!",
        "full_name": "Test User No Email",
        "role": "mecanico",
    }


@pytest.fixture
def multiple_users_data():
    """Multiple users data for batch testing"""
    return [
        {
            "username": f"user{i}",
            "password": "SecurePass123!",
            "full_name": f"User Number {i}",
            "email": f"user{i}@example.com",
            "role": "mecanico",
        }
        for i in range(1, 4)
    ]


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, sample_user_data: dict):
    """
    Fixture that creates a registered user.
    Useful for testing login and other authenticated endpoints.
    """
    response = await client.post("/auth/register", json=sample_user_data)
    assert response.status_code == 201
    return {"user_data": sample_user_data, "response": response.json()}
