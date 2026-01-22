from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from bson import ObjectId
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.dependencies import get_current_user_id
from src.main import app
from src.models.client import Client
from src.models.vehicle import Vehicle
from src.repository.vehicle import VehicleRepo

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
async def vehicle_repo(init_db):
    """Fixture to provide a clean VehicleRepo instance for each test."""
    return VehicleRepo(init_db)  # init_db provides the db connection


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
    """Fixture to create a sample vehicle in the test DB."""
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


# --- Tests ---


async def test_create_vehicle_success(client, sample_client):
    """Test creating a new vehicle successfully via the API."""

    payload = {
        "client_id": str(sample_client.id),
        "license_plate": "XX-99-YY",
        "brand": "Tesla",
        "model": "Model Y",
        "kilometers": 0,
        "vin": "12345678901234567",
    }
    response = await client.post("/vehicles/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    new_id = data["_id"]
    assert new_id is not None

    db_vehicle = await Vehicle.get(ObjectId(new_id))
    assert db_vehicle is not None


async def test_create_vehicle_duplicated(client, sample_vehicle, sample_client):
    """Test creating a vehicle with duplicate license plate via the API."""
    payload = {
        "client_id": str(sample_client.id),
        "license_plate": sample_vehicle.license_plate,
        "brand": sample_vehicle.brand,
        "model": sample_vehicle.model,
        "kilometers": sample_vehicle.kilometers,
        "vin": sample_vehicle.vin,
    }
    response = await client.post("/vehicles/", json=payload)

    assert response.status_code == status.HTTP_409_CONFLICT


async def test_get_vehicle_by_id_success(client, sample_vehicle):
    """Test retrieving a vehicle by ID via the API."""
    response = await client.get(f"/vehicles/{str(sample_vehicle.id)}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["_id"] is not None


async def test_get_vehicle_by_id_not_found(client):
    """Test retrieving a non-existent vehicle by ID via the API."""
    non_existent_id = str(ObjectId())
    response = await client.get(f"/vehicles/{non_existent_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_vehicle_by_license_plate_success(client, sample_vehicle):
    """Test retrieving a vehicle by license plate via the API."""
    license_plate = str(sample_vehicle.license_plate)

    response = await client.get(f"/vehicles/?license_plate={license_plate}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["_id"] is not None


async def test_get_vehicle_by_license_plate_not_found(client):
    """Test retrieving a non-existent vehicle by license plate via the API."""
    non_existent_license_plate = "ZZ-99-ZZ"
    response = await client.get(f"/vehicles/?license_plate={non_existent_license_plate}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_vehicles_by_client_id_success(client, sample_client):
    """Test retrieving vehicles by client ID via the API."""

    vehicle1 = Vehicle(
        client_id=sample_client.id,
        license_plate="CC-11-DD",
        brand="BrandA",
        model="ModelA",
        kilometers=5000,
        vin="VIN00000000000001",
    )
    vehicle2 = Vehicle(
        client_id=sample_client.id,
        license_plate="EE-22-FF",
        brand="BrandB",
        model="ModelB",
        kilometers=8000,
        vin="VIN00000000000002",
    )
    await vehicle1.save()
    await vehicle2.save()

    client_id = str(sample_client.id)

    response = await client.get(f"/vehicles/?client_id={client_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data) == 2
    ids = {vehicle["_id"] for vehicle in data}
    assert str(vehicle1.id) in ids
    assert str(vehicle2.id) in ids


async def test_get_vehicles_by_client_id_not_found(client):
    """Test retrieving vehicles for a client ID with no vehicles via the API."""
    non_existent_client_id = str(ObjectId())
    response = await client.get(f"/vehicles/?client_id={non_existent_client_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_all_vehicles_success(client, sample_vehicle):
    """Test retrieving all vehicles when no filter is provided."""

    # 1. Create a SECOND vehicle to ensure we verify a list return
    # (sample_vehicle creates the first one)
    second_vehicle = Vehicle(
        client_id=sample_vehicle.client_id,
        license_plate="ZZ-88-XX",
        brand="Ford",
        model="Focus",
        kilometers=50000,
        vin="VIN12345678901234",
    )
    await second_vehicle.save()

    # 2. Act: Call the endpoint with NO query parameters
    response = await client.get("/vehicles/")

    # 3. Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should be a list
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verify IDs are present
    returned_ids = [item["_id"] for item in data]
    assert str(sample_vehicle.id) in returned_ids
    assert str(second_vehicle.id) in returned_ids


async def test_get_all_vehicles_empty(client):
    """Test retrieving all vehicles when the DB is empty."""

    # Clean up the DB for this specific test
    await Vehicle.find_all().delete()

    response = await client.get("/vehicles/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 0


async def test_update_vehicle_success(client, sample_vehicle):
    """Test updating a vehicle via the API."""
    update_payload = {
        "kilometers": 20000,
    }

    response = await client.patch(f"/vehicles/{sample_vehicle.id}", json=update_payload)

    assert response.status_code == status.HTTP_200_OK

    db_vehicle = await Vehicle.get(sample_vehicle.id)
    assert db_vehicle is not None
    assert db_vehicle.kilometers == 20000


async def test_update_vehicle_not_found(client):
    """Test updating a non-existent vehicle via the API."""
    non_existent_id = str(ObjectId())
    update_payload = {
        "brand": "NonExistentBrand",
    }

    response = await client.patch(f"/vehicles/{non_existent_id}", json=update_payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_vehicle_success(client, sample_vehicle):
    """Test deleting a vehicle via the API."""
    response = await client.delete(f"/vehicles/{sample_vehicle.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    db_vehicle = await Vehicle.get(sample_vehicle.id)
    assert db_vehicle is None


async def test_delete_vehicle_not_found(client):
    """Test deleting a non-existent vehicle via the API."""
    non_existent_id = str(ObjectId())
    response = await client.delete(f"/vehicles/{non_existent_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
