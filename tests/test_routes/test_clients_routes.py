from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.client import Address, Client
from src.repository.client import ClientRepo

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


# --- Fixtures ---


@pytest.fixture
async def client_http(init_db):
    """
    Integration Test Client using AsyncClient.
    Runs in the SAME event loop as the DB fixture.
    """
    # Inject Test DB
    from src.db.connection import get_mongo_db

    app.dependency_overrides[get_mongo_db] = lambda: init_db

    # Nuclear Patch (Class Methods) - Keeps main.py safe
    with (
        patch("src.db.connection.PostgreSQLDatabase.connect", new_callable=AsyncMock),
        patch("src.db.connection.PostgreSQLDatabase.disconnect", new_callable=AsyncMock),
        patch("src.db.connection.MongoDatabase.connect", new_callable=AsyncMock),
        patch("src.db.connection.MongoDatabase.disconnect", new_callable=AsyncMock),
    ):
        # Use AsyncClient instead of TestClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client_repo(init_db):
    """Fixture to provide a clean ClientRepo instance for each test."""
    return ClientRepo(init_db)


@pytest.fixture(scope="function")
async def sample_client(init_db):
    """Fixture to create a sample client in the test DB."""
    client = Client(
        name="João Silva",
        nif="123456789",
        phone="912345678",
        email="joao.silva@example.com",
        address=Address(
            street="Rua de Santa Catarina, 123",
            city="Porto",
            zip_code="4000-442",
        ),
    )
    await client.save()
    return client


@pytest.fixture(scope="function")
async def sample_client_no_email(init_db):
    """Fixture to create a client without email."""
    client = Client(
        name="Maria Santos",
        nif="987654321",
        phone="913456789",
        email=None,
        address=None,
    )
    await client.save()
    return client


# --- Integration Tests ---


async def test_create_client_success(client_http):
    """Test that creating a client persists it to the real DB."""
    payload = {
        "name": "Ana Cacho Paulo",
        "nif": "111222333",
        "phone": "914567890",
        "email": "ana.cacho@example.com",
        "address": {
            "street": "Avenida da Boavista, 456",
            "city": "Porto",
            "zipCode": "4100-111",
        },
    }

    # Act
    response = await client_http.post("/clients/", json=payload)

    if response.status_code == 422:
        print(response.json())

    # Assert API
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Ana Cacho Paulo"
    assert data["nif"] == "111222333"
    assert "createdAt" in data
    assert "updatedAt" in data
    new_id = data["_id"]

    # Assert Database (The REAL proof)
    db_client = await Client.get(ObjectId(new_id))
    assert db_client is not None
    assert db_client.name == "Ana Cacho Paulo"
    assert db_client.email == "ana.cacho@example.com"
    assert db_client.address is not None
    assert db_client.address.city == "Porto"


async def test_create_client_minimal_fields(client_http):
    """Test creating a client with only required fields (no email/address)."""
    payload = {
        "name": "Ana Oliveira",
        "nif": "444555666",
        "phone": "915678901",
    }

    # Act
    response = await client_http.post("/clients/", json=payload)

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Ana Oliveira"
    assert data["email"] is None
    assert data["address"] is None


async def test_create_client_duplicate_nif(client_http, sample_client):
    """Test that creating a client with duplicate NIF returns 409 CONFLICT."""
    payload = {
        "name": "Different Name",
        "nif": sample_client.nif,  # Duplicate NIF
        "phone": "919999999",
        "email": "different@example.com",
    }

    # Act
    response = await client_http.post("/clients/", json=payload)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    error_data = response.json()["detail"]
    assert error_data["error"] == "duplicate_nif"
    assert error_data["nif"] == sample_client.nif


async def test_create_client_duplicate_email(client_http, sample_client):
    """Test that creating a client with duplicate email returns 409 CONFLICT."""
    payload = {
        "name": "Different Name",
        "nif": "999888777",  # Different NIF
        "phone": "919999999",
        "email": sample_client.email,  # Duplicate Email
    }

    # Act
    response = await client_http.post("/clients/", json=payload)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    error_data = response.json()["detail"]
    assert error_data["error"] == "duplicate_email"
    assert error_data["email"] == sample_client.email


async def test_get_client_by_id_success(client_http, sample_client):
    """Test retrieving a real client by ID."""
    client_id = str(sample_client.id)

    # Act
    response = await client_http.get(f"/clients/{client_id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["_id"] == client_id
    assert data["name"] == sample_client.name
    assert data["nif"] == sample_client.nif


async def test_get_client_by_id_invalid_format(client_http):
    """Test 400 for invalid ObjectId format."""
    # Act
    response = await client_http.get("/clients/invalid-id-format")

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid ObjectId format" in response.json()["detail"]


async def test_get_client_by_id_not_found(client_http):
    """Test 404 for missing ID in real DB."""
    client_id = str(ObjectId())  # Random ID

    # Act
    response = await client_http.get(f"/clients/{client_id}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


async def test_list_all_clients(client_http, sample_client, sample_client_no_email):
    """Test retrieving all clients when no query params are provided."""
    # Act
    response = await client_http.get("/clients/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verify both sample clients are in the list
    client_ids = [c["_id"] for c in data]
    assert str(sample_client.id) in client_ids
    assert str(sample_client_no_email.id) in client_ids


async def test_list_clients_filter_by_nif(client_http, sample_client):
    """Test filtering clients by NIF returns single client."""
    # Act
    response = await client_http.get(f"/clients/?nif={sample_client.nif}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should return single client (not wrapped in list based on router implementation)
    assert data["_id"] == str(sample_client.id)
    assert data["nif"] == sample_client.nif


async def test_list_clients_filter_by_email(client_http, sample_client):
    """Test filtering clients by email returns single client."""
    # Act
    response = await client_http.get(f"/clients/?email={sample_client.email}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should return single client
    assert data["_id"] == str(sample_client.id)
    assert data["email"] == sample_client.email


async def test_list_clients_filter_by_nif_not_found(client_http):
    """Test filtering by non-existent NIF returns 404."""
    # Act
    response = await client_http.get("/clients/?nif=000000000")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_list_clients_filter_by_email_not_found(client_http):
    """Test filtering by non-existent email returns 404."""
    # Act
    response = await client_http.get("/clients/?email=nonexistent@example.com")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_list_clients_nif_priority_over_email(client_http, sample_client, sample_client_no_email):
    """Test that NIF filter takes priority over email filter."""
    # Act - Provide both nif and email query params
    response = await client_http.get(f"/clients/?nif={sample_client_no_email.nif}&email={sample_client.email}")

    # Assert - Should return the client matching NIF (not email)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["_id"] == str(sample_client_no_email.id)
    assert data["nif"] == sample_client_no_email.nif


async def test_update_client_name(client_http, sample_client):
    """Test updating client name persists to DB."""
    client_id = str(sample_client.id)
    payload = {"name": "João Silva Updated"}

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert API
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "João Silva Updated"

    # Original fields should remain unchanged
    assert data["nif"] == sample_client.nif
    assert data["email"] == sample_client.email

    # Assert Database
    db_client = await Client.get(sample_client.id)
    assert db_client.name == "João Silva Updated"


async def test_update_client_phone_and_email(client_http, sample_client):
    """Test updating multiple fields at once."""
    client_id = str(sample_client.id)
    payload = {
        "phone": "966777888",
        "email": "joao.updated@example.com",
    }

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert API
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["phone"] == "966777888"
    assert data["email"] == "joao.updated@example.com"

    # Assert Database
    db_client = await Client.get(sample_client.id)
    assert db_client.phone == "966777888"
    assert db_client.email == "joao.updated@example.com"


async def test_update_client_address(client_http, sample_client):
    """Test updating client address."""
    client_id = str(sample_client.id)
    payload = {
        "address": {
            "street": "Rua Nova, 999",
            "city": "Lisboa",
            "zipCode": "1000-001",
        }
    }

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert API
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["address"]["city"] == "Lisboa"
    assert data["address"]["zipCode"] == "1000-001"

    # Assert Database
    db_client = await Client.get(sample_client.id)
    assert db_client.address.city == "Lisboa"


async def test_update_client_invalid_id(client_http):
    """Test 400 for invalid ObjectId format in update."""
    payload = {"name": "Test"}

    # Act
    response = await client_http.patch("/clients/invalid-id", json=payload)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_update_client_not_found(client_http):
    """Test 404 for updating non-existent client."""
    client_id = str(ObjectId())
    payload = {"name": "Test"}

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_update_client_duplicate_nif(client_http, sample_client, sample_client_no_email):
    """Test that updating to duplicate NIF returns 409 CONFLICT."""
    client_id = str(sample_client_no_email.id)
    payload = {"nif": sample_client.nif}  # Try to use existing NIF

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    error_data = response.json()["detail"]
    assert error_data["error"] == "duplicate_nif"


async def test_update_client_duplicate_email(client_http, sample_client, sample_client_no_email):
    """Test that updating to duplicate email returns 409 CONFLICT."""
    client_id = str(sample_client_no_email.id)
    payload = {"email": sample_client.email}  # Try to use existing email

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    error_data = response.json()["detail"]
    assert error_data["error"] == "duplicate_email"


async def test_update_client_timestamps(client_http, sample_client):
    """Test that updated_at timestamp is refreshed on update."""
    client_id = str(sample_client.id)
    original_updated_at = sample_client.updated_at

    # Wait a small amount to ensure timestamp difference
    import asyncio

    await asyncio.sleep(0.1)

    payload = {"phone": "999999999"}

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK

    # Verify timestamp was updated
    db_client = await Client.get(sample_client.id)
    assert db_client.updated_at > original_updated_at


async def test_delete_client_success(client_http, sample_client):
    """Test deleting removes client from DB."""
    client_id = str(sample_client.id)

    # Act
    response = await client_http.delete(f"/clients/{client_id}")

    # Assert API
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Assert Database
    db_client = await Client.get(sample_client.id)
    assert db_client is None


async def test_delete_client_invalid_id(client_http):
    """Test 400 for invalid ObjectId format in delete."""
    # Act
    response = await client_http.delete("/clients/invalid-id")

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_delete_client_not_found(client_http):
    """Test 404 for deleting non-existent client."""
    client_id = str(ObjectId())

    # Act
    response = await client_http.delete(f"/clients/{client_id}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_client_idempotency(client_http, sample_client):
    """Test that deleting the same client twice returns 404 on second attempt."""
    client_id = str(sample_client.id)

    # First delete
    response1 = await client_http.delete(f"/clients/{client_id}")
    assert response1.status_code == status.HTTP_204_NO_CONTENT

    # Second delete (should fail)
    response2 = await client_http.delete(f"/clients/{client_id}")
    assert response2.status_code == status.HTTP_404_NOT_FOUND


async def test_client_created_at_immutable(client_http, sample_client):
    """Test that created_at timestamp doesn't change on update."""
    client_id = str(sample_client.id)
    original_created_at = sample_client.created_at

    payload = {"name": "Updated Name"}

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK

    # Verify created_at remains unchanged
    db_client = await Client.get(sample_client.id)
    assert db_client.created_at == original_created_at


async def test_partial_address_update(client_http, sample_client):
    """Test updating only part of the address."""
    client_id = str(sample_client.id)

    # Update only the city
    payload = {
        "address": {
            "city": "Braga",
        }
    }

    # Act
    response = await client_http.patch(f"/clients/{client_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # City should be updated
    assert data["address"]["city"] == "Braga"
