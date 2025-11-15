import os
import uuid
from secrets import token_hex

import motor.motor_asyncio
import pytest_asyncio
from beanie import init_beanie

from src.config import settings
from src.models.appointments import Appointment
from src.models.client import Client
from src.models.invoices import Invoice
from src.models.vehicle import Vehicle
from src.models.work_orders import WorkOrder

if "PASETO_SECRET_KEY" not in os.environ:
    settings.auth.PASETO_SECRET_KEY = token_hex(32)


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

    db_name = uuid.uuid4().hex + uuid.uuid1().hex
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
