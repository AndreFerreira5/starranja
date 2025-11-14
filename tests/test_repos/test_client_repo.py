import pytest
import pytest_asyncio
from bson import ObjectId
from datetime import datetime, UTC
from beanie import init_beanie
from beanie.exceptions import RevisionIdWasChanged
from mongomock_motor import AsyncMongoMockClient

# Adjust imports based on your project structure
from src.models.client import Client, ClientCreate, ClientUpdate
from src.repository.client import (ClientRepo)


# ============================================================================
# FIXTURES - Database Setup and Async Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.
    Required for async fixtures with session scope.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    Fixture that provides a clean test database for each test.
    Uses mongomock_motor for in-memory MongoDB simulation.
    The database is cleared after each test to ensure isolation.

    Yields:
        Database instance for testing with Beanie initialized
    """
    # Create mock MongoDB client
    client = AsyncMongoMockClient()
    db = client.workshop_test_db

    # Initialize Beanie with the Client model
    await init_beanie(database=db, document_models=[Client])

    yield db

    # Cleanup: clear all clients after each test
    await Client.delete_all()


@pytest_asyncio.fixture(scope="function")
async def client_repository(test_db):
    """
    Fixture that provides a ClientRepository instance connected to test database.

    Args:
        test_db: Test database fixture

    Returns:
        ClientRepository instance
    """
    return ClientRepo(test_db)


@pytest.fixture
def sample_client_data():
    """
    Fixture providing valid client data for testing (as dict for flexibility).

    Returns:
        dict: Valid client data dictionary
    """
    return {
        "name": "João Silva",
        "email": "joao.silva@email.com",
        "phone": "+351912345678",
        "nif": "123456789",
        "address": {
            "street": "Rua das Flores, 123",
            "city": "Lisboa",
            "zip_code": "1000-100"
        }
    }


@pytest.fixture
def sample_client_create(sample_client_data):
    """
    Fixture providing ClientCreate Pydantic model instance.

    Returns:
        ClientCreate: Valid client creation model
    """
    return ClientCreate(**sample_client_data)


@pytest.fixture
def sample_client_data_alternative():
    """
    Fixture providing alternative valid client data for testing multiple clients.

    Returns:
        dict: Valid client data dictionary with different NIF
    """
    return {
        "name": "Maria Santos",
        "email": "maria.santos@email.com",
        "phone": "+351923456789",
        "nif": "987654321",
        "address": {
            "street": "Avenida da Liberdade, 456",
            "city": "Porto",
            "zip_code": "4000-200"
        }
    }


@pytest_asyncio.fixture
async def inserted_client(sample_client_data):
    """
    Fixture that inserts a client directly into the database for read/update/delete tests.

    Args:
        sample_client_data: Sample client data fixture

    Returns:
        Client: Inserted Beanie Client document
    """
    client = Client(**sample_client_data)
    await client.insert()
    return client


# ============================================================================
# CREATE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_client_success(client_repository, sample_client_create):
    """
    Test successful creation of a new client.

    Expected behavior:
        - Client should be inserted into database
        - Method should return the created Client document with id
        - All fields should match the input data
        - created_at and updated_at timestamps should be set
    """
    # Act
    created_client = await client_repository.create_client(sample_client_create)

    # Assert
    assert created_client is not None, "Created client should not be None"
    assert created_client.id is not None, "Created client should have an id"
    assert isinstance(created_client.id, ObjectId), "id should be an ObjectId"
    assert created_client.name == sample_client_create.name
    assert created_client.email == sample_client_create.email
    assert created_client.phone == sample_client_create.phone
    assert created_client.nif == sample_client_create.nif
    assert created_client.address.street == sample_client_create.address.street
    assert created_client.address.city == sample_client_create.address.city
    assert created_client.created_at is not None
    assert created_client.updated_at is not None
    assert isinstance(created_client.created_at, datetime)


@pytest.mark.asyncio
async def test_create_client_duplicate_nif_fails(client_repository, sample_client_create, inserted_client):
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
        nif=inserted_client.nif,  # Same NIF as existing client
        phone="+351999999999",
        email="different@email.com"
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:  # Could be ValueError or DuplicateKeyError
        await client_repository.create_client(duplicate_client_data)

    # Verify the exception is related to duplicate NIF
    error_msg = str(exc_info.value).lower()
    assert "nif" in error_msg or "duplicate" in error_msg or "unique" in error_msg


@pytest.mark.asyncio
async def test_create_client_missing_required_fields(client_repository):
    """
    Test that creating a client with missing required fields fails validation.

    Expected behavior:
        - Should raise ValidationError from Pydantic
        - No client should be created in database
    """
    # Arrange - invalid data missing required 'nif' field
    from pydantic import ValidationError

    # Act & Assert - Pydantic will raise ValidationError during model instantiation
    with pytest.raises(ValidationError) as exc_info:
        invalid_client = ClientCreate(
            name="Invalid Client",
            phone="+351912345678"
            # Missing required: nif
        )


@pytest.mark.asyncio
async def test_create_client_invalid_email(client_repository, sample_client_data):
    """
    Test that creating a client with invalid email fails validation.

    Expected behavior:
        - Should raise ValidationError for invalid EmailStr
        - No client should be created in database
    """
    from pydantic import ValidationError

    # Arrange
    sample_client_data["email"] = "not-a-valid-email"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        invalid_client = ClientCreate(**sample_client_data)

    assert "email" in str(exc_info.value).lower()


# ============================================================================
# READ TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_client_by_id_success(client_repository, inserted_client):
    """
    Test successful retrieval of a client by ID.

    Expected behavior:
        - Should return the Client document with matching id
        - All fields should match the inserted data
        - Return type should be Client (Beanie Document)
    """
    # Arrange
    client_id = inserted_client.id

    # Act
    retrieved_client = await client_repository.get_by_id(client_id)

    # Assert
    assert retrieved_client is not None, "Retrieved client should not be None"
    assert retrieved_client.id == client_id
    assert retrieved_client.name == inserted_client.name
    assert retrieved_client.email == inserted_client.email
    assert retrieved_client.nif == inserted_client.nif
    assert retrieved_client.phone == inserted_client.phone
    assert isinstance(retrieved_client, Client)


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_get_all_clients_success(client_repository, sample_client_data, sample_client_data_alternative):
    """
    Test successful retrieval of all clients.

    Expected behavior:
        - Should return a list of all Client documents
        - List should contain correct number of clients
        - Each client should have all required fields
    """
    # Arrange - insert multiple clients
    client1 = Client(**sample_client_data)
    client2 = Client(**sample_client_data_alternative)
    await client1.insert()
    await client2.insert()

    # Act
    all_clients = await client_repository.get_all_clients()

    # Assert
    assert isinstance(all_clients, list), "Should return a list"
    assert len(all_clients) == 2, "Should return all inserted clients"
    assert all(isinstance(client, Client) for client in all_clients), "All items should be Client documents"
    assert all(client.id is not None for client in all_clients), "All clients should have id"
    assert all(client.nif is not None for client in all_clients), "All clients should have nif"


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_get_client_by_nif_success(client_repository, inserted_client):
    """
    Test successful retrieval of a client by NIF.

    Expected behavior:
        - Should return the Client document with matching NIF
        - All fields should match the inserted data
    """
    # Arrange
    nif = inserted_client.nif

    # Act
    retrieved_client = await client_repository.get_by_nif(nif)

    # Assert
    assert retrieved_client is not None, "Retrieved client should not be None"
    assert retrieved_client.nif == nif
    assert retrieved_client.name == inserted_client.name
    assert retrieved_client.id == inserted_client.id


@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_update_client_success(client_repository, inserted_client):
    """
    Test successful update of an existing client.

    Expected behavior:
        - Client should be updated with new data
        - Should return the updated Client document
        - updated_at timestamp should be refreshed
        - id should remain unchanged
    """
    # Arrange
    client_id = inserted_client.id
    original_created_at = inserted_client.created_at

    update_data = ClientUpdate(
        name="João Silva Updated",
        email="joao.updated@email.com",
        phone="+351999999999"
    )

    # Act
    updated_client = await client_repository.update(client_id, update_data)

    # Assert
    assert updated_client is not None, "Update should return updated client"
    assert updated_client.id == client_id, "id should not change"
    assert updated_client.name == update_data.name
    assert updated_client.email == update_data.email
    assert updated_client.phone == update_data.phone
    assert updated_client.nif == inserted_client.nif, "NIF should not change when not in update"
    assert updated_client.created_at == original_created_at, "created_at should not change"
    assert updated_client.updated_at > inserted_client.updated_at, "updated_at should be refreshed"


@pytest.mark.asyncio
async def test_update_client_not_found(client_repository):
    """
    Test update of a non-existent client.

    Expected behavior:
        - Should return None indicating no update occurred
        - Should not raise an exception
        - Should not create a new client
    """
    # Arrange
    non_existent_id = ObjectId()
    update_data = ClientUpdate(name="Updated Name")

    # Act
    result = await client_repository.update(non_existent_id, update_data)

    # Assert
    assert result is None, "Should return None when client doesn't exist"


@pytest.mark.asyncio
async def test_update_client_partial_fields(client_repository, inserted_client):
    """
    Test partial update of client fields.

    Expected behavior:
        - Only specified fields should be updated
        - Other fields should remain unchanged
        - Should support updating nested fields (like address)
    """
    # Arrange
    client_id = inserted_client.id
    original_email = inserted_client.email
    original_name = inserted_client.name

    update_data = ClientUpdate(
        phone="+351888888888"
        # Not updating name or email
    )

    # Act
    updated_client = await client_repository.update(client_id, update_data)

    # Assert
    assert updated_client is not None
    assert updated_client.phone == update_data.phone
    assert updated_client.email == original_email, "Email should remain unchanged"
    assert updated_client.name == original_name, "Name should remain unchanged"


@pytest.mark.asyncio
async def test_update_client_address(client_repository, inserted_client):
    """
    Test updating nested address fields.

    Expected behavior:
        - Address fields should be updated
        - Other fields should remain unchanged
    """
    # Arrange
    client_id = inserted_client.id
    from src.models.client import AddressUpdate

    update_data = ClientUpdate(
        address=AddressUpdate(
            street="New Street, 999",
            city="Coimbra"
            # zip_code remains unchanged
        )
    )

    # Act
    updated_client = await client_repository.update(client_id, update_data)

    # Assert
    assert updated_client is not None
    assert updated_client.address.street == "New Street, 999"
    assert updated_client.address.city == "Coimbra"


@pytest.mark.asyncio
async def test_update_client_nif_duplicate_fails(client_repository, inserted_client, sample_client_data_alternative):
    """
    Test that updating a client's NIF to a duplicate value fails.

    Expected behavior:
        - Should raise ValueError or DuplicateKeyError
        - Original client should remain unchanged
    """
    # Arrange - insert second client
    client2 = Client(**sample_client_data_alternative)
    await client2.insert()

    client_id = inserted_client.id
    # Try to update first client's NIF to match second client's NIF
    update_data = ClientUpdate(nif=client2.nif)

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await client_repository.update(client_id, update_data)

    error_msg = str(exc_info.value).lower()
    assert "nif" in error_msg or "duplicate" in error_msg or "unique" in error_msg


# ============================================================================
# DELETE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_delete_client_success(client_repository, inserted_client):
    """
    Test successful deletion of a client.

    Expected behavior:
        - Client should be removed from database
        - Should return True or success indicator
        - Subsequent get_by_id should return None
    """
    # Arrange
    client_id = inserted_client.id

    # Act
    result = await client_repository.delete(client_id)

    # Assert
    assert result is True or result == 1, "Delete should return success indicator"

    # Verify client is actually deleted
    deleted_client = await Client.get(client_id)
    assert deleted_client is None, "Client should no longer exist in database"


@pytest.mark.asyncio
async def test_delete_client_not_found(client_repository):
    """
    Test deletion of a non-existent client.

    Expected behavior:
        - Should return False or 0 indicating no deletion occurred
        - Should not raise an exception
    """
    # Arrange
    non_existent_id = ObjectId()

    # Act
    result = await client_repository.delete(non_existent_id)

    # Assert
    assert result is False or result == 0, "Should indicate no client was deleted"


@pytest.mark.asyncio
async def test_delete_client_invalid_id(client_repository):
    """
    Test deletion with invalid ID format.

    Expected behavior:
        - Should raise ValueError or TypeError
        - Should not cause application crash
    """
    # Arrange
    invalid_id = "invalid_id_format"

    # Act & Assert
    with pytest.raises((ValueError, TypeError, Exception)):
        await client_repository.delete(invalid_id)


# ============================================================================
# ADDITIONAL EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_client_timestamps_auto_managed(sample_client_data):
    """
    Test that Beanie automatically manages created_at and updated_at timestamps.

    Expected behavior:
        - created_at should be set on insert
        - updated_at should be set on insert
        - updated_at should be updated on save
    """
    # Arrange & Act - Create and insert client
    client = Client(**sample_client_data)
    await client.insert()

    original_created_at = client.created_at
    original_updated_at = client.updated_at

    # Assert initial timestamps
    assert client.created_at is not None
    assert client.updated_at is not None
    assert isinstance(client.created_at, datetime)

    # Modify and save
    import asyncio
    await asyncio.sleep(0.1)  # Ensure time difference
    client.name = "Modified Name"
    await client.save()

    # Assert updated_at changed but created_at didn't
    assert client.created_at == original_created_at, "created_at should not change"
    assert client.updated_at > original_updated_at, "updated_at should be refreshed"


@pytest.mark.asyncio
async def test_client_with_optional_fields_null(client_repository):
    """
    Test creating a client with optional fields (email, address) as None.

    Expected behavior:
        - Should create client successfully
        - email and address should be None
    """
    # Arrange
    minimal_client_data = ClientCreate(
        name="Minimal Client",
        nif="111222333",
        phone="+351911111111"
        # email and address are optional
    )

    # Act
    created_client = await client_repository.create_client(minimal_client_data)

    # Assert
    assert created_client is not None
    assert created_client.name == "Minimal Client"
    assert created_client.email is None
    assert created_client.address is None


@pytest.mark.asyncio
async def test_client_nif_indexed_uniquely():
    """
    Test that NIF is properly indexed as unique at the database level.

    Expected behavior:
        - Attempting to insert duplicate NIF should fail
        - Error should be raised by database/Beanie
    """
    # Arrange
    client_data = {
        "name": "Test Client 1",
        "nif": "123456789",
        "phone": "+351912345678"
    }

    client1 = Client(**client_data)
    await client1.insert()

    # Act & Assert - try to insert with same NIF
    client2 = Client(
        name="Test Client 2",
        nif="123456789",  # Duplicate NIF
        phone="+351923456789"
    )

    with pytest.raises(Exception) as exc_info:
        await client2.insert()

    error_msg = str(exc_info.value).lower()
    assert "duplicate" in error_msg or "unique" in error_msg or "nif" in error_msg
