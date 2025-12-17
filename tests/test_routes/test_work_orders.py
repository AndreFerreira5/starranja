from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from bson import ObjectId
from fastapi import status
from fastapi.testclient import TestClient

from src.dependencies import get_current_user_id, get_database
from src.main import app
from src.models.work_orders import Quote, WorkOrder, WorkOrderStatus

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


# --- Fixtures ---


@pytest.fixture
def client(init_db):
    """
    Integration Test Client.
    - Uses REAL MongoDB (via init_db fixture).
    - Mocks Auth (via dependency override).
    - Mocks Postgres (via patch).
    """
    # Bypass Auth: Return a fake User ID
    app.dependency_overrides[get_current_user_id] = lambda: UUID("00000000-0000-0000-0000-000000000000")

    # Inject Test Database: Ensure Repo gets the test DB connection
    # 'init_db' fixture typically returns the AsyncIOMotorClient or DB object
    # Adjust '.db' or return value based on the actual conftest.py structure
    app.dependency_overrides[get_database] = lambda: init_db

    # Patch Startup: Prevent main.py from connecting to real Postgres/Mongo
    with (
        patch("src.main.auth_db_connect", new_callable=AsyncMock),
        patch("src.main.auth_db_disconnect", new_callable=AsyncMock),
    ):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_work_order(init_db):
    """Creates a real WorkOrder in the test database."""
    wo = WorkOrder(
        id=ObjectId(),
        work_order_number="2025-0001",
        client_id=ObjectId(),
        vehicle_id=ObjectId(),
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
    response = client.post("/work-orders/", json=payload)

    # Assert API
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "workOrderNumber" in data
    new_id = data["_id"]

    # Assert Database (The REAL proof)
    db_wo = await WorkOrder.get(ObjectId(new_id))
    assert db_wo is not None
    assert db_wo.client_observations == "Noise in engine"


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
    response = client.post("/work-orders/", json=payload)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "active_work_order_exists"


async def test_get_work_order_by_id_success(client, sample_work_order):
    """Test retrieving a real WO by ID."""
    wo_id = str(sample_work_order.id)

    response = client.get(f"/work-orders/{wo_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["_id"] == wo_id


async def test_get_work_order_not_found(client):
    """Test 404 for missing ID in real DB."""
    wo_id = str(ObjectId())  # Random ID
    response = client.get(f"/work-orders/{wo_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_list_work_orders_by_vehicle(client, sample_work_order):
    """Test filtering by vehicle ID."""
    v_id = str(sample_work_order.vehicle_id)

    response = client.get(f"/work-orders/?vehicle_id={v_id}")

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
    response = client.patch(f"/work-orders/{wo_id}", json=payload)

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
    response = client.delete(f"/work-orders/{wo_id}")

    # Assert API
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Assert Database
    db_wo = await WorkOrder.get(sample_work_order.id)
    assert db_wo is None
