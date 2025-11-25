import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

# Import models
from src.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate

# Import the repository to test
from src.repository.vehicle import VehicleRepo

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def vehicle_repo(init_db):
    """Fixture to provide a clean VehicleRepo instance for each test."""
    return VehicleRepo(init_db)  # init_db provides the db connection


@pytest.fixture(scope="function")
async def sample_vehicle(init_db):
    """Fixture to create a sample vehicle in the test DB."""
    vehicle = Vehicle(
        client_id=ObjectId(),
        license_plate="AA-00-BB",
        brand="Test",
        model="Model",
        kilometers=1000,
        vin="1234567890ABCDEFG",
        # ... other required Vehicle fields
    )
    await vehicle.save()
    return vehicle


async def test_create_vehicle_success(vehicle_repo):
    """Test creating a new vehicle successfully."""
    client_id = ObjectId()
    create_data = VehicleCreate(
        clientId=client_id,
        licensePlate="XX-99-YY",
        brand="Tesla",
        model="Model Y",
        kilometers=0,
        vin="12345678901234567",
    )

    vehicle = await vehicle_repo.create_vehicle(create_data)

    assert vehicle is not None
    assert vehicle.id is not None
    assert vehicle.client_id == client_id
    assert vehicle.license_plate == "XX-99-YY"

    # Verify it was actually saved to the DB
    found = await Vehicle.get(vehicle.id)
    assert found is not None
    assert found.license_plate == "XX-99-YY"


async def test_create_vehicle_duplicate_license_plate(vehicle_repo, sample_vehicle):
    """Test creating a vehicle with duplicate license plate fails."""
    create_data = VehicleCreate(
        clientId=ObjectId(),
        licensePlate=sample_vehicle.license_plate,
        brand="Other",
        model="Car",
        kilometers=10,
        vin="1234567890ABCDEFG",
    )

    with pytest.raises(DuplicateKeyError):
        await vehicle_repo.create_vehicle(create_data)


async def test_create_vehicle_duplicate_vin(vehicle_repo, sample_vehicle):
    """Test creating a vehicle with duplicate VIN fails."""
    create_data = VehicleCreate(
        clientId=ObjectId(),
        licensePlate="XX-99-YY",
        brand="Other",
        model="Car",
        kilometers=10,
        vin=sample_vehicle.vin,
    )

    with pytest.raises(DuplicateKeyError):
        await vehicle_repo.create_vehicle(create_data)


async def test_get_by_id_success(vehicle_repo, sample_vehicle):
    """Test retrieving a vehicle by ID."""
    found = await vehicle_repo.get_by_id(sample_vehicle.id)
    assert found is not None
    assert found.id == sample_vehicle.id


async def test_get_by_id_not_found(vehicle_repo):
    """Test retrieving a vehicle by non-existent ID."""
    found = await vehicle_repo.get_by_id(ObjectId())
    assert found is None


async def test_get_by_license_plate_success(vehicle_repo, sample_vehicle):
    """Test retrieving a vehicle by license plate."""
    found = await vehicle_repo.get_by_license_plate(sample_vehicle.license_plate)
    assert found is not None
    assert found.id == sample_vehicle.id


async def test_get_by_license_plate_not_found(vehicle_repo):
    """Test retrieving a vehicle by non-existent license plate."""
    found = await vehicle_repo.get_by_license_plate("ZZ-99-ZZ")
    assert found is None


async def test_get_by_client_id_returns_list(vehicle_repo, sample_vehicle):
    """Test retrieving vehicles by client ID."""
    vehicles = await vehicle_repo.get_by_client_id(sample_vehicle.client_id)
    assert len(vehicles) == 1
    assert vehicles[0].id == sample_vehicle.id


async def test_get_by_client_id_not_found(vehicle_repo):
    """Test retrieving vehicles for a client ID with no vehicles."""
    vehicles = await vehicle_repo.get_by_client_id(ObjectId())
    assert len(vehicles) == 0


async def test_update_vehicle_success(vehicle_repo, sample_vehicle):
    """Test updating a vehicle"""
    update_data = VehicleUpdate(kilometers=10000)
    updated_vehicle = await vehicle_repo.update(sample_vehicle.id, update_data)

    assert updated_vehicle is not None
    assert updated_vehicle.kilometers == 10000

    # Verify it was actually updated in the DB
    found = await Vehicle.get(updated_vehicle.id)
    assert found is not None
    assert found.kilometers == 10000


async def test_update_vehicle_not_found(vehicle_repo):
    """Test updating a vehicle that doesn't exist"""
    update_data = VehicleUpdate(kilometers=10000)
    updated_vehicle = await vehicle_repo.update(ObjectId(), update_data)

    assert updated_vehicle is None


async def test_delete_vehicle_success(vehicle_repo, sample_vehicle):
    """Test deleting a vehicle"""
    result = await vehicle_repo.delete(sample_vehicle.id)
    assert result is True

    # Verify it was actually deleted from the DB
    found = await Vehicle.get(sample_vehicle.id)
    assert found is None


async def test_delete_vehicle_not_found(vehicle_repo):
    """Test deleting a vehicle that doesn't exist"""
    result = await vehicle_repo.delete(ObjectId())
    assert result is False
