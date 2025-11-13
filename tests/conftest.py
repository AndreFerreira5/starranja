import asyncio
import os
import sys
import uuid
from collections.abc import AsyncGenerator
from secrets import token_hex

# Configure Windows event loop FIRST
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set PASETO key BEFORE any other imports
if "PASETO_SECRET_KEY" not in os.environ:
    os.environ["PASETO_SECRET_KEY"] = token_hex(32)

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Load test environment variables
if not load_dotenv(".env.test", override=False):
    load_dotenv(".env", override=False)

# Import after environment is configured
from src.db.connection import get_auth_db
from src.main import app
from src.models.auth import Base


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine connected to the remote test database.
    Creates tables ONCE at the start of test session.
    """
    test_db_url = os.getenv("AUTH_TEST_DATABASE_URL")
    if not test_db_url:
        raise ValueError("AUTH_TEST_DATABASE_URL not found in environment. Please set it in .env.test file.")

    engine = create_async_engine(
        f"{test_db_url}/{uuid.uuid4().hex}",
        poolclass=NullPool,
        echo=False,
        connect_args={
            "timeout": 10,
            "command_timeout": 10,
        },
    )

    # Setup: Create tables and initialize roles ONCE
    async with engine.begin() as conn:
        # Enable uuid extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Drop all tables first (clean slate)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        # Initialize roles
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

    # Teardown: Drop all tables after ALL tests complete
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """
    Create a test database session WITHOUT transaction rollback.
    Each test gets a fresh session and data persists.
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
        # Don't rollback - let data persist for other tests to see
        # Tests are isolated because each test creates unique usernames


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """
    Create an async test client with database dependency override.
    All API calls in tests will use the test database.
    """

    async def override_get_auth_db():
        """Override the get_auth_db dependency to use test session"""
        yield test_session

    # Override the database dependency
    app.dependency_overrides[get_auth_db] = override_get_auth_db

    # Create test client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        timeout=30.0,
    ) as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user registration data for tests - unique per test"""
    import random
    import string

    # Generate unique username to avoid conflicts
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    return {
        "username": f"testuser_{random_suffix}",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "email": f"test_{random_suffix}@example.com",
        "role": "mecanico",
    }


@pytest.fixture
def sample_user_data_no_email():
    """Sample user registration data without email"""
    import random
    import string

    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    return {
        "username": f"testuser_no_email_{random_suffix}",
        "password": "SecurePass123!",
        "full_name": "Test User No Email",
        "role": "mecanico",
    }


@pytest.fixture
def multiple_users_data():
    """Multiple users data for batch testing"""
    import random
    import string

    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    return [
        {
            "username": f"user{i}_{random_suffix}",
            "password": "SecurePass123!",
            "full_name": f"User Number {i}",
            "email": f"user{i}_{random_suffix}@example.com",
            "role": "mecanico",
        }
        for i in range(1, 4)
    ]


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, sample_user_data: dict):
    """
    Fixture that creates a registered user.
    Posts to /auth/register which is public in test environment.
    """
    # Register user at /auth/register (matches main.py prefix)
    response = await client.post("/auth/register", json=sample_user_data)

    # Better error message if registration fails
    assert response.status_code == 201, f"Registration failed with {response.status_code}: {response.text}"

    return {
        "user_data": sample_user_data,  # Contains original password
        "response": response.json(),
    }


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient):
    """
    Fixture that creates an admin user and returns authentication token.
    Useful for testing protected endpoints that require admin role.
    """
    import random
    import string

    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    admin_data = {
        "username": f"admin_user_{random_suffix}",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "email": f"admin_{random_suffix}@example.com",
        "role": "admin",
    }

    # Register admin user
    reg_response = await client.post("/auth/register", json=admin_data)
    assert reg_response.status_code == 201, f"Admin registration failed: {reg_response.text}"

    # Login to get token
    login_response = await client.post(
        "/auth/login", json={"username": admin_data["username"], "password": admin_data["password"]}
    )
    assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"

    token = login_response.json()["access_token"]
    return {"token": token, "user_data": admin_data}
