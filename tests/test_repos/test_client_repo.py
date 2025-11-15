from datetime import datetime

import pytest
from bson import ObjectId
from pydantic_core._pydantic_core import ValidationError

# Adjust imports based on your project structure
from src.models.client import AddressUpdate, Client, ClientCreate, ClientUpdate
from src.repository.client import ClientRepo

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# ============================================================================
# FIXTURES - Database Setup and Async Configuration
# ============================================================================


@pytest.fixture(scope="function")
async def client_repository(init_db):
    """Fixture to provide a clean ClientRepo instance for each test."""
    return ClientRepo(init_db)  # init_db provides the db connection


@pytest.fixture(scope="function")
async def sample_client(init_db):
    """Fixture to create a sample client in the test DB."""
    client = Client(
        name="João Silva",
        nif="123456789",
        phone="+351912345678",
        email="joao.silva@email.com",
        address={"street": "Rua das Flores, 123", "city": "Lisboa", "zip_code": "1000-100"},
    )
    await client.save()
    return client


@pytest.fixture(scope="function")
async def sample_client_alternative(init_db):
    """Fixture to create an alternative sample client in the test DB."""
    client = Client(
        name="Maria Santos",
        nif="987654321",
        phone="+351923456789",
        email="maria.santos@email.com",
        address={"street": "Avenida da Liberdade, 456", "city": "Porto", "zip_code": "4000-200"},
    )
    await client.save()
    return client


# ============================================================================
# CREATE TESTS
# ============================================================================


async def test_create_client_success(client_repository):
    """
    Test successful creation of a new client.

    Expected behavior:
        - Client should be inserted into database
        - Method should return the created Client document with id
        - All fields should match the input data
        - created_at and updated_at timestamps should be set
    """
    # Act
    create_data = ClientCreate(
        name="João Silva",
        nif="123456789",
        phone="+351912345678",
        email="joao.silva@email.com",
        address={"street": "Rua das Flores, 123", "city": "Lisboa", "zip_code": "1000-100"},
    )

    created_client = await client_repository.create_client(create_data)

    # Assert
    assert created_client is not None, "Created client should not be None"
    assert created_client.id is not None, "Created client should have an id"
    assert isinstance(created_client.id, ObjectId), "id should be an ObjectId"
    assert created_client.name == create_data.name
    assert created_client.email == create_data.email
    assert created_client.phone == create_data.phone
    assert created_client.nif == create_data.nif
    assert created_client.address.street == create_data.address.street
    assert created_client.address.city == create_data.address.city
    assert created_client.created_at is not None
    assert created_client.updated_at is not None
    assert isinstance(created_client.created_at, datetime)

    # Verify it was actually saved to the DB
    found = await Client.get(created_client.id)
    assert found is not None
    assert found.nif == create_data.nif


async def test_create_client_duplicate_nif_fails(client_repository, sample_client):
    """
    Test that creating a client with a duplicate NIF fails.

    The NIF (tax identification number) must be unique per client.

    Expected behavior:
        - Should raise ValueError, DuplicateKeyError, or return None
        - Original client should remain unchanged in database
        - No new client should be created
    """
    # Arrange - inserted_client fixture already has the NIF in database
    duplicate_client_data = ClientCreate(
        name="Different Name",
        nif=sample_client.nif,  # Same NIF as existing client
        phone="+351999999999",
        email="different@email.com",
    )

    # --- Assertions ---
    with pytest.raises(Exception) as exc_info:
        await client_repository.create_client(duplicate_client_data)

    error_msg = str(exc_info.value).lower()
    assert "nif" in error_msg or "duplicate" in error_msg or "unique" in error_msg


async def test_create_client_missing_required_fields():
    """
    Test that creating a client with missing required fields fails validation.

    Expected behavior:
        - Should raise ValidationError from Pydantic
        - No client should be created in database
    """
    # --- Assertions ---
    with pytest.raises(ValidationError):
        ClientCreate(
            name="Invalid Client",
            phone="+351912345678",
            # Missing required: nif
        )


async def test_create_client_invalid_email():
    """
    Test that creating a client with invalid email fails validation.

    Expected behavior:
        - Should raise ValidationError for invalid EmailStr
        - No client should be created in database
    """
    # --- Assertions ---
    with pytest.raises(ValidationError) as exc_info:
        ClientCreate(name="Test Client", nif="123456789", phone="+351912345678", email="not-a-valid-email")

    assert "email" in str(exc_info.value).lower()


# ============================================================================
# READ TESTS
# ============================================================================


async def test_get_client_by_id_success(client_repository, sample_client):
    """
    Test successful retrieval of a client by ID.

    Expected behavior:
        - Should return the Client document with matching id
        - All fields should match the inserted data
        - Return type should be Client (Beanie Document)
    """

    # Act
    retrieved_client = await client_repository.get_by_id(sample_client.id)

    # Assert
    assert retrieved_client is not None, "Retrieved client should not be None"
    assert retrieved_client.id == sample_client.id
    assert retrieved_client.name == sample_client.name
    assert retrieved_client.email == sample_client.email
    assert retrieved_client.nif == sample_client.nif
    assert retrieved_client.phone == sample_client.phone
    assert isinstance(retrieved_client, Client)


async def test_get_client_by_id_not_found(client_repository):
    """
    Test retrieval of a non-existent client by ID.

    Expected behavior:
        - Should return None when client doesn't exist
        - Should not raise an exception
    """
    # Arrange - create a valid ObjectId that doesn't exist in database
    non_existent_id = ObjectId()

    # Act
    retrieved_client = await client_repository.get_by_id(non_existent_id)

    # Assert
    assert retrieved_client is None, "Should return None for non-existent client"


async def test_get_client_by_id_invalid_id_format(client_repository):
    """
    Test retrieval with invalid ID format.

    Expected behavior:
        - Should raise ValueError or TypeError for invalid ID format
        - Should not cause application crash
    """
    # Arrange
    invalid_id = "invalid_id_format"

    # Act & Assert
    with pytest.raises((ValueError, TypeError, Exception)):
        await client_repository.get_by_id(invalid_id)


async def test_get_all_clients_success(client_repository, sample_client, sample_client_alternative):
    """
    Test successful retrieval of all clients.

    Expected behavior:
        - Should return a list of all Client documents
        - List should contain correct number of clients
        - Each client should have all required fields
    """

    # Act
    all_clients = await client_repository.get_all_clients()

    # Assert
    assert isinstance(all_clients, list)
    assert len(all_clients) == 2
    assert all(isinstance(client, Client) for client in all_clients)
    assert all(client.id is not None for client in all_clients)
    assert all(client.nif is not None for client in all_clients)


async def test_get_all_clients_empty_collection(client_repository):
    """
    Test retrieval of all clients when collection is empty.

    Expected behavior:
        - Should return an empty list
        - Should not raise an exception
    """
    # Act
    all_clients = await client_repository.get_all_clients()

    # Assert
    assert isinstance(all_clients, list), "Should return a list"
    assert len(all_clients) == 0, "Should return empty list for empty collection"


async def test_get_client_by_nif_success(client_repository, sample_client):
    """
    Test successful retrieval of a client by NIF.

    Expected behavior:
        - Should return the Client document with matching NIF
        - All fields should match the inserted data
    """
    # Act
    retrieved_client = await client_repository.get_by_nif(sample_client.nif)

    # Assert
    assert retrieved_client is not None, "Retrieved client should not be None"
    assert retrieved_client.nif == sample_client.nif
    assert retrieved_client.name == sample_client.name
    assert retrieved_client.id == sample_client.id


async def test_get_client_by_nif_not_found(client_repository):
    """
    Test retrieval of a non-existent client by NIF.

    Expected behavior:
        - Should return None when client with NIF doesn't exist
    """
    # Arrange
    non_existent_nif = "999999999"

    # Act
    retrieved_client = await client_repository.get_by_nif(non_existent_nif)

    # Assert
    assert retrieved_client is None, "Should return None for non-existent NIF"


# ============================================================================
# UPDATE TESTS
# ============================================================================


async def test_update_client_success(client_repository, sample_client):
    """
    Test successful update of an existing client.

    Expected behavior:
        - Client should be updated with new data
        - Should return the updated Client document
        - updated_at timestamp should be refreshed
        - id should remain unchanged
    """
    # Arrange
    client_id = sample_client.id
    original_created_at = sample_client.created_at

    update_data = ClientUpdate(name="João Silva Updated", email="joao.updated@email.com", phone="+351999999999")

    # Act
    updated_client = await client_repository.update(client_id, update_data)

    # Assert
    assert updated_client is not None, "Update should return updated client"
    assert updated_client.id == client_id, "id should not change"
    assert updated_client.name == update_data.name
    assert updated_client.email == update_data.email
    assert updated_client.phone == update_data.phone
    assert updated_client.nif == sample_client.nif, "NIF should not change when not in update"
    assert updated_client.created_at == original_created_at, "created_at should not change"
    assert updated_client.updated_at > sample_client.updated_at, "updated_at should be refreshed"


async def test_update_client_not_found(client_repository):
    """Test updating a non-existent client."""

    non_existent_id = ObjectId()
    update_data = ClientUpdate(name="Updated Name")

    result = await client_repository.update(non_existent_id, update_data)

    # --- Assertions ---
    assert result is None


async def test_update_client_partial_fields(client_repository, sample_client):
    """Test partial update of client fields."""

    original_email = sample_client.email
    original_name = sample_client.name

    update_data = ClientUpdate(
        phone="+351888888888"
        # Not updating name or email
    )

    updated_client = await client_repository.update(sample_client.id, update_data)

    # --- Assertions ---
    assert updated_client is not None
    assert updated_client.phone == update_data.phone
    assert updated_client.email == original_email
    assert updated_client.name == original_name


async def test_update_client_address(client_repository, sample_client):
    """Test updating nested address fields."""

    update_data = ClientUpdate(address=AddressUpdate(street="New Street, 999", city="Coimbra"))

    updated_client = await client_repository.update(sample_client.id, update_data)

    # --- Assertions ---
    assert updated_client is not None
    assert updated_client.address.street == "New Street, 999"
    assert updated_client.address.city == "Coimbra"


async def test_update_client_nif_duplicate_fails(client_repository, sample_client, sample_client_alternative):
    """Test that updating a client's NIF to a duplicate value fails."""

    update_data = ClientUpdate(nif=sample_client_alternative.nif)

    # --- Assertions ---
    with pytest.raises(Exception) as exc_info:
        await client_repository.update(sample_client.id, update_data)

    error_msg = str(exc_info.value).lower()
    assert "nif" in error_msg or "duplicate" in error_msg or "unique" in error_msg


async def test_delete_client_success(client_repository, sample_client):
    """Test successfully deleting a client."""

    was_deleted = await client_repository.delete(sample_client.id)

    # --- Assertions ---
    assert was_deleted is True

    # Verify it's gone from the DB
    found = await Client.get(sample_client.id)
    assert found is None


async def test_delete_client_not_found(client_repository):
    """Test that deleting a non-existent ID returns False."""

    was_deleted = await client_repository.delete(ObjectId())

    # --- Assertions ---
    assert was_deleted is False


async def test_delete_client_invalid_id(client_repository):
    """Test deletion with invalid ID format."""

    invalid_id = "invalid_id_format"

    # --- Assertions ---
    with pytest.raises((ValueError, TypeError, Exception)):
        await client_repository.delete(invalid_id)


async def test_client_with_optional_fields_null(client_repository):
    """Test creating a client with optional fields (email, address) as None."""

    minimal_client_data = ClientCreate(
        name="Minimal Client",
        nif="111222333",
        phone="+351911111111",
        # email and address are optional
    )

    created_client = await client_repository.create_client(minimal_client_data)

    # --- Assertions ---
    assert created_client is not None
    assert created_client.name == "Minimal Client"
    assert created_client.email is None
    assert created_client.address is None


async def test_client_nif_indexed_uniquely(init_db):
    """Test that NIF is properly indexed as unique at the database level."""

    client1 = Client(
        name="Test Client 1",
        nif="555666777",  # Use unique NIF
        phone="+351912345678",
    )
    await client1.insert()

    # --- Assertions ---
    client2 = Client(
        name="Test Client 2",
        nif="555666777",  # Duplicate NIF
        phone="+351923456789",
    )

    with pytest.raises(Exception) as exc_info:
        await client2.insert()

    error_msg = str(exc_info.value).lower()
    assert "duplicate" in error_msg or "unique" in error_msg or "nif" in error_msg
