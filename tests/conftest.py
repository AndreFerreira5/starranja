import os
from secrets import token_hex

import motor.motor_asyncio
import pytest_asyncio
from beanie import init_beanie

from src.config import settings

if "PASETO_SECRET_KEY" not in os.environ:
    settings.auth.PASETO_SECRET_KEY = token_hex(32)


from src.models.client import Client
from src.models.invoices import Invoice
from src.models.vehicle import Vehicle
from src.models.work_orders import WorkOrder


@pytest_asyncio.fixture(scope="function")
async def init_db():
    """
    Fixture to initialize a clean test database for each test function.
    """
    # Use a test database URL (e.g., from an env var or default to local)
    test_db_url = os.getenv("MONGO_TEST_DATABASE_URL")
    test_db_name = "starranja_test_db"  # Make sure this matches the URL

    # 1. Create a fresh client and database
    client = motor.motor_asyncio.AsyncIOMotorClient(test_db_url)
    db = client[test_db_name]

    # 2. Initialize Beanie with all your document models
    await init_beanie(
        database=db,
        document_models=[
            Client,
            Vehicle,
            WorkOrder,
            Invoice,
        ],
    )

    try:
        # 3. Yield the database for the test to use
        yield db
    finally:
        # 4. Teardown: Drop the entire test database after the test is done
        await client.drop_database(test_db_name)
        client.close()
