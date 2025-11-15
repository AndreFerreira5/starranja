# In your conftest.py

# You can keep your PASETO_SECRET_KEY logic if needed
import os
from secrets import token_hex

import pytest_asyncio
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient  # <-- Use this client

from src.config import settings

# --- IMPORT ALL YOUR MODELS ---
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
    Fixture to initialize a clean, *in-memory* test database
    using mongomock_motor for each test function.
    """

    # 1. Create the mock client (no URL needed)
    client = AsyncMongoMockClient()
    db = client["test_db"]  # Any name works here

    # 2. Initialize Beanie with all your document models
    await init_beanie(database=db, document_models=[Client, Vehicle, WorkOrder, Invoice, Appointment])

    try:
        # 3. Yield the database for the test to use
        yield db
    finally:
        # 4. Teardown: Clear collections (safer for mongomock)
        await Client.delete_all()
        await Vehicle.delete_all()
        await WorkOrder.delete_all()
        await Invoice.delete_all()
        await Appointment.delete_all()

        client.close()
