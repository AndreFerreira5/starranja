from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from bson import ObjectId
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.dependencies import get_current_user_id
from src.main import app
from src.models.client import Client
from src.models.vehicle import Vehicle
from src.models.work_orders import (
    Quote,
    WorkOrder,
    WorkOrderStatus,
)
from src.repository.work_orders import WorkOrderRepo

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


# --- Fixtures ---


@pytest.fixture
async def client(init_db):
    """
    Integration Test Client using AsyncClient.
    Runs in the SAME event loop as the DB fixture.
    """
    # 1. Bypass Auth
    app.dependency_overrides[get_current_user_id] = lambda: UUID("00000000-0000-0000-0000-000000000000")

    # 2. Inject Test DB
    from src.db.connection import get_mongo_db

    app.dependency_overrides[get_mongo_db] = lambda: init_db

    # 3. Nuclear Patch (Class Methods) - Keeps main.py safe
    with (
        patch("src.db.connection.PostgreSQLDatabase.connect", new_callable=AsyncMock),
        patch("src.db.connection.PostgreSQLDatabase.disconnect", new_callable=AsyncMock),
        patch("src.db.connection.MongoDatabase.connect", new_callable=AsyncMock),
        patch("src.db.connection.MongoDatabase.disconnect", new_callable=AsyncMock),
    ):
        # 4. Use AsyncClient instead of TestClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def work_order_repo(init_db):
    """Fixture to provide a clean WorkOrderRepo instance for each test."""
    return WorkOrderRepo(init_db)  # init_db provides the db connection


@pytest.fixture(scope="function")
async def sample_client(init_db):
    """Fixture to create a sample client in the test DB."""
    client = Client(
        name="Test Client",
        nif="123456789",
        phone="912345678",
        # ... other required Client fields
    )
    await client.save()
    return client


@pytest.fixture(scope="function")
async def sample_vehicle(init_db, sample_client):
    """Fixture to create a sample vehicle linked to the sample client."""
    vehicle = Vehicle(
        client_id=sample_client.id,
        license_plate="AA-00-BB",
        brand="Test",
        model="Model",
        kilometers=1000,
        vin="1234567890ABCDEFG",
        # ... other required Vehicle fields
    )
    await vehicle.save()
    return vehicle


@pytest.fixture
async def sample_work_order(init_db, sample_client, sample_vehicle):
    """Creates a real WorkOrder in the test database."""
    wo = WorkOrder(
        id=ObjectId(),
        work_order_number="2025-0001",
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,
        created_by_id=uuid4(),
        status=WorkOrderStatus.AWAITING_DIAGNOSTIC,
        is_active=True,
        entry_date=datetime.now(UTC),
        quote=Quote(clientObservations="Original Issue"),
        items=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await wo.save()
    return wo


# --- Integration Tests ---


async def test_create_work_order_success(client):
    """Test that creating a work order persists it to the real DB."""
    payload = {
        "clientId": str(ObjectId()),
        "vehicleId": str(ObjectId()),
        "clientObservations": "Noise in engine",
        "entryDate": datetime.now(UTC).isoformat(),
    }

    # Act
    response = await client.post("/work-orders/", json=payload)

    if response.status_code == 422:
        print(response.json())

    # Assert API
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "workOrderNumber" in data
    new_id = data["_id"]

    # Assert Database (The REAL proof)
    db_wo = await WorkOrder.get(ObjectId(new_id))
    assert db_wo is not None
    assert db_wo.quote is not None
    assert db_wo.quote.client_observations == "Noise in engine"


async def test_create_work_order_active_exists(client, sample_work_order):
    """Test that the DB correctly blocks a duplicate active WO (Business Rule RB02)."""

    # Try to create a NEW WO for the SAME vehicle used in 'sample_work_order'
    payload = {
        "clientId": str(sample_work_order.client_id),
        "vehicleId": str(sample_work_order.vehicle_id),  # Same Vehicle ID
        "clientObservations": "New Request",
        "entryDate": datetime.now(UTC).isoformat(),
    }

    # Act
    response = await client.post("/work-orders/", json=payload)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "active_work_order_exists"


async def test_get_work_order_by_id_success(client, sample_work_order):
    """Test retrieving a real WO by ID."""
    wo_id = str(sample_work_order.id)

    response = await client.get(f"/work-orders/{wo_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["_id"] == wo_id


async def test_get_work_order_not_found(client):
    """Test 404 for missing ID in real DB."""
    wo_id = str(ObjectId())  # Random ID
    response = await client.get(f"/work-orders/{wo_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_list_work_orders_by_vehicle(client, sample_work_order):
    """Test filtering by vehicle ID."""
    v_id = str(sample_work_order.vehicle_id)

    response = await client.get(f"/work-orders/?vehicle_id={v_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["_id"] == str(sample_work_order.id)


async def test_update_work_order_status(client, sample_work_order):
    """Test updating status persists to DB."""
    wo_id = str(sample_work_order.id)
    payload = {"status": "InProgress"}

    # Act
    response = await client.patch(f"/work-orders/{wo_id}", json=payload)

    # Assert API
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "InProgress"

    # Assert Database
    db_wo = await WorkOrder.get(sample_work_order.id)
    assert db_wo.status == WorkOrderStatus.IN_PROGRESS


async def test_delete_work_order_success(client, sample_work_order):
    """Test deleting removes item from DB."""
    wo_id = str(sample_work_order.id)

    # Act
    response = await client.delete(f"/work-orders/{wo_id}")

    # Assert API
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Assert Database
    db_wo = await WorkOrder.get(sample_work_order.id)
    assert db_wo is None


async def test_update_work_order_calculates_totals(client, sample_work_order):
    """Test that adding items correctly updates the calculated total fields."""
    wo_id = str(sample_work_order.id)

    # Payload with 1 Part and 1 Labor item
    # Part: 100.00 * 2 = 200.00 (excl VAT)
    # Labor: 50.00 * 1 = 50.00 (excl VAT)
    # Total Excl VAT = 250.00
    # VAT (23%) = 57.50
    # Total Incl VAT = 307.50
    payload = {
        "items": [
            {
                "type": "Part",
                "description": "Brake Discs",
                "reference": "BD-01",
                "quantity": "2",
                "unitPriceWithoutIVA": "100.00",
                "ivaRate": "0.23",
                "totalPriceWithIVA": "246.00",  # Frontend usually estimates this
            },
            {
                "type": "Labor",
                "description": "Installation",
                "reference": "L-01",
                "quantity": "1",
                "unitPriceWithoutIVA": "50.00",
                "ivaRate": "0.23",
                "totalPriceWithIVA": "61.50",
            },
        ]
    }

    # Act
    response = await client.patch(f"/work-orders/{wo_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Check that the backend performed the summation correctly
    # Note: Compare as strings to verify precision
    assert data["finalTotalPriceWithoutIVA"] == "250.00"  # (100*2) + (50*1)
    # Depending on your backend logic, check if it calculated the grand total
    # If your backend logic for 'finalTotalPriceWithIVA' exists, assert it here:
    assert data["finalTotalPriceWithIVA"] == "307.50"
