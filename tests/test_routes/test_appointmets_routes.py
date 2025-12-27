from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from bson import ObjectId
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.dependencies import get_current_user_id
from src.main import app
from src.models.appointments import Appointment, AppointmentStatus
from src.models.client import Client
from src.models.vehicle import Vehicle
from src.repository.appointments import AppointmentRepo

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
async def appointment_repo(init_db):
    """Fixture to provide a clean AppointmentRepo instance for each test."""
    return AppointmentRepo(init_db)  # init_db provides the db connection


@pytest.fixture(scope="function")
async def sample_client(init_db):
    """Fixture to create a sample client in the test DB."""
    client = Client(
        name="Test Client",
        nif="123456789",
        phone="912345678",
        email="test@client.com",
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
    )
    await vehicle.save()
    return vehicle


@pytest.fixture(scope="function")
async def sample_appointment(init_db, sample_client, sample_vehicle):
    """Fixture to create a sample appointment in the test DB."""
    appointment = Appointment(
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.SCHEDULED,
    )
    await appointment.save()
    return appointment


# --- Integration Tests ---


async def test_create_appointment_success(client, sample_client):
    """Test that creating a appointment persists it to the real DB."""
    payload = {
        # FIX: Use the ID of the client that actually exists in the DB
        "clientId": str(sample_client.id),
        # FIX: Match the AppointmentCreate model field names (alias)
        "notes": "Noise in engine",
        "appointmentDate": datetime.now(UTC).isoformat(),
        # Note: vehicleId is NOT in AppointmentCreate schema, so we omit it
    }

    # Act
    response = await client.post("/appointments/", json=payload)

    if response.status_code == 422:
        print(response.json())

    # Assert API
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["clientId"] == payload["clientId"]
    new_id = data["_id"]
    # Assert Database
    db_appointment = await Appointment.get(ObjectId(new_id))
    assert db_appointment is not None
    assert str(db_appointment.client_id) == payload["clientId"]


async def test_create_appointment_failed(client):
    """Test that creating a appointment with invalid data fails."""
    payload = {
        "clientId": "invalid-object-id",  # Invalid ObjectId
        "appointmentDate": datetime.now(UTC).isoformat(),
    }

    # Act
    response = await client.post("/appointments/", json=payload)

    # Assert API
    # Should return 422 Unprocessable Entity because validation happens before Repo check
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_get_appointment_by_id_success(client, sample_appointment):
    """Test retrieving a real Appointment by ID."""
    appointment_id = str(sample_appointment.id)

    response = await client.get(f"/appointments/{appointment_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["_id"] == appointment_id


async def test_get_appointment_not_found(client):
    """Test 404 for missing ID in real DB."""
    appointment_id = str(ObjectId())  # Random ID
    response = await client.get(f"/appointments/{appointment_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_list_appointments_by_vehicle(client, sample_appointment):
    """Test filtering by vehicle ID."""
    v_id = str(sample_appointment.vehicle_id)

    response = await client.get(f"/appointments/?vehicle_id={v_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["_id"] == str(sample_appointment.id)


async def test_update_appointment_status(client, sample_appointment):
    """Test updating status persists to DB."""
    appointment_id = str(sample_appointment.id)
    payload = {"status": "Completed"}

    # Act
    response = await client.patch(f"/appointments/{appointment_id}", json=payload)

    # Assert API
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "Completed"

    # Assert Database
    db_appointment = await Appointment.get(sample_appointment.id)
    assert db_appointment.status == "Completed"


async def test_delete_appointment_success(client, sample_appointment):
    """Test deleting removes item from DB."""
    apointment_id = str(sample_appointment.id)

    # Act
    response = await client.delete(f"/appointments/{apointment_id}")

    # Assert API
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Assert Database
    db_appointment = await Appointment.get(sample_appointment.id)
    assert db_appointment is None
