from datetime import UTC, datetime
from uuid import uuid4

import pytest
from bson import ObjectId

from src.exceptions.work_orders import ActiveWorkOrderExistsError

# Import  models
from src.models.client import Client
from src.models.vehicle import Vehicle
from src.models.work_orders import Quote, WorkOrder, WorkOrderCreate, WorkOrderStatus, WorkOrderUpdate

# Import the repository to test
from src.repository.work_orders import WorkOrderRepo

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


# --- Fixtures ---
# (Might move db_client and init_db to a central conftest.py later)


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


@pytest.fixture(scope="function")
async def sample_work_order(init_db, sample_client, sample_vehicle):
    """Fixture to create a sample, active work order in the test DB."""
    wo = WorkOrder(
        work_order_number="2025-0001",
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,
        created_by_id=uuid4(),
        status=WorkOrderStatus.AWAITING_DIAGNOSTIC,
        is_active=True,
        entry_date=datetime.now(UTC),
    )
    await wo.save()
    return wo


# --- Tests ---


async def test_create_work_order_success(work_order_repo, sample_client, sample_vehicle):
    """Test creating a new work order successfully."""

    # Simulate a logged-in user's ID
    test_user_id = uuid4()

    create_data = WorkOrderCreate(
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,
        entry_date=datetime.now(UTC),
        client_observations="Test observation",
    )

    new_wo = await work_order_repo.create_work_order(create_data, created_by_id=test_user_id)

    # --- Assertions (for when implemented) ---
    assert new_wo is not None
    assert new_wo.id is not None
    assert new_wo.client_id == sample_client.id
    assert new_wo.status == WorkOrderStatus.AWAITING_DIAGNOSTIC  # Check default
    assert new_wo.is_active is True  # Check default

    # Verify it was actually saved to the DB
    found = await WorkOrder.get(new_wo.id)
    assert found is not None
    assert found.vehicle_id == sample_vehicle.id


async def test_get_work_order_by_id_success(work_order_repo, sample_work_order):
    """Test retrieving a work order by its ObjectId."""

    found_wo = await work_order_repo.get_by_id(sample_work_order.id)

    # --- Assertions ---
    assert found_wo is not None
    assert found_wo.id == sample_work_order.id
    assert found_wo.work_order_number == "2025-0001"


async def test_get_work_order_by_id_not_found(work_order_repo):
    """Test that retrieving a non-existent ObjectId returns None."""

    found_wo = await work_order_repo.get_by_id(ObjectId())  # Random, non-existent ID

    # --- Assertions ---
    assert found_wo is None


async def test_get_by_work_order_number_success(work_order_repo, sample_work_order):
    """Test retrieving a work order by its human-readable number."""

    found_wo = await work_order_repo.get_by_work_order_number("2025-0001")

    # --- Assertions ---
    assert found_wo is not None
    assert found_wo.id == sample_work_order.id


async def test_get_active_by_vehicle_id_success(work_order_repo, sample_work_order, sample_vehicle):
    """Test retrieving the active work order for a vehicle."""

    found_wo = await work_order_repo.get_active_by_vehicle_id(sample_vehicle.id)

    # --- Assertions  ---
    assert found_wo is not None
    assert found_wo.id == sample_work_order.id
    assert found_wo.is_active is True


async def test_get_all_work_orders_by_vehicle_id(work_order_repo, sample_work_order, sample_vehicle):
    """Test retrieving all work orders for a vehicle."""

    orders = await work_order_repo.get_by_vehicle_id(sample_vehicle.id)

    # --- Assertions ---
    assert isinstance(orders, list)
    assert len(orders) == 1
    assert orders[0].id == sample_work_order.id


async def test_get_work_orders_by_client_id(work_order_repo, sample_work_order, sample_client):
    """Test retrieving all work orders for a client."""

    orders = await work_order_repo.get_by_client_id(sample_client.id)

    # --- Assertions ---
    assert isinstance(orders, list)
    assert len(orders) == 1
    assert orders[0].id == sample_work_order.id


async def test_update_work_order_success(work_order_repo, sample_work_order):
    """Test updating a work order (e.g., adding a quote and changing status)."""
    update_data = WorkOrderUpdate(
        status=WorkOrderStatus.AWAITING_APPROVAL, quote=Quote(diagnostic="Needs new flux capacitor.")
    )

    updated_wo = await work_order_repo.update(sample_work_order.id, update_data)

    # --- Assertions ---
    assert updated_wo is not None
    assert updated_wo.id == sample_work_order.id
    assert updated_wo.status == WorkOrderStatus.AWAITING_APPROVAL
    assert updated_wo.quote.diagnostic == "Needs new flux capacitor."
    assert updated_wo.updated_at > sample_work_order.updated_at


async def test_delete_work_order_success(work_order_repo, sample_work_order):
    """Test successfully deleting a work order."""

    was_deleted = await work_order_repo.delete(sample_work_order.id)

    # --- Assertions ---
    assert was_deleted is True

    # Verify it's gone from the DB
    found = await WorkOrder.get(sample_work_order.id)
    assert found is None


async def test_delete_work_order_not_found(work_order_repo):
    """Test that deleting a non-existent ID returns False."""

    was_deleted = await work_order_repo.delete(ObjectId())

    # --- Assertions  ---
    assert was_deleted is False


async def test_create_work_order_fails_on_active_vehicle(
    work_order_repo, sample_work_order, sample_client, sample_vehicle
):
    """Test that creating a new active WO for a vehicle that already has one fails."""
    # This tests the partial unique index for RB02

    create_data = WorkOrderCreate(
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,  # Same vehicle as sample_work_order
        entry_date=datetime.now(UTC),
    )

    # Simulate a user ID for this new creation
    test_user_id = uuid4()

    # pytest.raises CATCH the expected exception
    # The repository method will raise a generic Exception
    with pytest.raises(ActiveWorkOrderExistsError) as exc_info:
        # Call the method with *both* arguments
        await work_order_repo.create_work_order(create_data, created_by_id=test_user_id)

    # Verify the exception details
    assert exc_info.value.vehicle_id == str(sample_vehicle.id)
    assert "RB02" in str(exc_info.value)
