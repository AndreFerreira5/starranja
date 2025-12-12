import asyncio
import os
import random
import string
import sys
import uuid
from collections.abc import AsyncGenerator
from secrets import token_hex

import asyncpg
import motor.motor_asyncio
import pytest
import pytest_asyncio
from beanie import init_beanie
from sqlalchemy import select

from src.authentication.services.password import PasswordService
from src.config import settings
from src.models.auth import Role, User

# Configure Windows event loop FIRST
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Set PASETO key BEFORE any other imports
if "PASETO_SECRET_KEY" not in os.environ:
    settings.auth.PASETO_SECRET_KEY = token_hex(32)
    os.environ["PASETO_SECRET_KEY"] = settings.auth.PASETO_SECRET_KEY

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.db.connection import get_auth_db
from src.main import app
from src.models.appointments import Appointment
from src.models.auth import Base
from src.models.client import Client
from src.models.invoices import Invoice
from src.models.vehicle import Vehicle
from src.models.work_orders import WorkOrder

# Configure Windows event loop FIRST
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Load test environment variables FIRST (.env.test preferred)
if not load_dotenv(".env.test", override=False):
    load_dotenv(".env", override=False)

# Set PASETO key BEFORE tests that might use it
env_auth_paseto = os.getenv("AUTH__PASETO_SECRET_KEY")
env_paseto = os.getenv("PASETO_SECRET_KEY")

if env_auth_paseto:
    settings.auth.PASETO_SECRET_KEY = env_auth_paseto.strip()
    os.environ["PASETO_SECRET_KEY"] = settings.auth.PASETO_SECRET_KEY
elif env_paseto:
    settings.auth.PASETO_SECRET_KEY = env_paseto.strip()
else:
    settings.auth.PASETO_SECRET_KEY = token_hex(32)
    os.environ["PASETO_SECRET_KEY"] = settings.auth.PASETO_SECRET_KEY


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine connected to the remote test database.
    Creates tables ONCE at the start of test session.
    """
    test_base_db_url = os.getenv("AUTH_TEST_DATABASE_URL")
    if not test_base_db_url:
        raise ValueError("AUTH_TEST_DATABASE_URL not found in environment. Please set it in .env.test file.")

    unique_db_name = uuid.uuid4().hex

    asyncpg_base_url = test_base_db_url.replace("postgresql+asyncpg://", "postgresql://")
    admin_url = f"{asyncpg_base_url}/postgres"
    admin_conn = await asyncpg.connect(admin_url)
    try:
        await admin_conn.execute(f'CREATE DATABASE "{unique_db_name}"')
    finally:
        await admin_conn.close()

    test_db_url = f"{test_base_db_url}/{unique_db_name}"
    engine = create_async_engine(
        test_db_url,
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

    await engine.dispose()
    admin_conn = await asyncpg.connect(admin_url)
    try:
        # force drop to terminate any remaining connections
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{unique_db_name}" WITH (FORCE)')
    finally:
        await admin_conn.close()


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
async def registered_user(
    client: AsyncClient,
    sample_user_data: dict,
    admin_token: dict,
) -> dict:
    """
    Create a regular user by calling the protected /auth/register endpoint
    with valid admin credentials. Returns both user payload and admin info.
    """
    headers = {"Authorization": f"Bearer {admin_token['token']}"}

    response = await client.post(
        "/auth/register",
        json=sample_user_data,
        headers=headers,
    )
    assert response.status_code == 201, f"Registration failed with {response.status_code}: {response.text}"

    # Preserve both created user and admin info for downstream tests
    return {
        "user_data": sample_user_data,
        "admin": admin_token["user_data"],
    }


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> dict:
    """
    - In non-production (e.g. ENVIRONMENT=test), uses /auth/bootstrap-admin.
    - If bootstrap is forbidden (ENVIRONMENT=production), RBAC auth tests
      are skipped instead of failing the whole suite.
    """
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    admin_data = {
        "username": f"admin_user_{random_suffix}",
        "password": "AdminPass123!",
        "full_name": "Admin User",
        "email": f"admin_{random_suffix}@example.com",
        "role": "admin",
    }

    # 1) Try to bootstrap admin
    resp_boot = await client.post("/auth/bootstrap-admin", json=admin_data)

    if resp_boot.status_code == 403:
        # Environment explicitly forbids bootstrap (e.g. production CI).
        pytest.skip(
            "Admin bootstrap not allowed in this environment (ENVIRONMENT=production). Skipping RBAC auth tests."
        )

    assert resp_boot.status_code in (200, 201), f"Admin bootstrap failed: {resp_boot.status_code} {resp_boot.text}"

    # 2) Login via the real /auth/login endpoint to obtain a token
    resp_login = await client.post(
        "/auth/login",
        json={
            "username": admin_data["username"],
            "password": admin_data["password"],
        },
    )
    assert resp_login.status_code == 200, f"Admin login failed: {resp_login.status_code} {resp_login.text}"

    token_data = resp_login.json()
    assert "access_token" in token_data

    return {
        "token": token_data["access_token"],
        "user_data": admin_data,
    }


@pytest_asyncio.fixture(scope="function")
async def init_db():
    """
    Fixture to initialize a clean test database for each test function.
    It reads the database URL from the MONGO_TEST_DATABASE_URL env var.
    """

    # 1. Get the test database URL from the environment
    test_db_base_url = os.getenv("MONGO_TEST_DATABASE_URL")

    # 2. Add a guard clause to fail fast if the .env file is missing
    if not test_db_base_url:
        raise ValueError(
            "MONGO_TEST_DATABASE_URL is not set. Ensure you have a .env file and pytest-dotenv is installed."
        )

    db_name = uuid.uuid4().hex
    test_db_url = f"{test_db_base_url}/{db_name}"

    # 3. Create the client
    client = motor.motor_asyncio.AsyncIOMotorClient(test_db_url)

    db = client[db_name]

    await client.drop_database(db_name)

    # 5. Initialize Beanie with all your document models
    await init_beanie(database=db, document_models=[Client, Vehicle, WorkOrder, Invoice, Appointment])

    try:
        # 6. Yield the database for the test to use
        yield db
    finally:
        # 7. Teardown: Drop the entire test database after the test is done
        try:
            await client.drop_database(db_name)
        finally:
            client.close()


@pytest.fixture
def password_service():
    """Provides the PasswordService instance."""
    return PasswordService()


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession, password_service: PasswordService):
    """
    Creates a dedicated user for refresh token testing.
    Uses 'test_session' to ensure it's in the same DB transaction.
    """
    import uuid

    unique_id = uuid.uuid4().hex[:8]

    # Create the user
    new_user = User(
        username=f"refresh_test_{unique_id}",
        email=f"refresh_{unique_id}@example.com",
        password_hash=password_service.hash_password("SecurePass123!"),
        full_name="Refresh Test User",
    )

    test_session.add(new_user)
    # Don't flush yet, wait until we add roles so we can do it all at once

    # Fetch the role to assign
    result = await test_session.execute(select(Role).where(Role.name == "mecanico"))
    role = result.scalar_one_or_none()

    if role:
        new_user.roles.append(role)

    await test_session.commit()
    await test_session.refresh(new_user)

    return new_user
