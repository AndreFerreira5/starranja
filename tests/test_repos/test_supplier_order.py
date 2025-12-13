from datetime import UTC, datetime
from uuid import uuid4

import pytest
from bson import ObjectId

from src.models.supplier_order import (
    SupplierOrder,
    SupplierOrderCreate,
    SupplierOrderStatus,
    SupplierOrderUpdate,
)

# Import the repository to test
from src.repository.supplier_order import SupplierOrderRepo

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


# --- Fixtures ---


@pytest.fixture(scope="function")
async def supplier_order_repo(init_db):
    """Fixture to provide a clean SupplierOrderRepo instance for each test."""
    return SupplierOrderRepo(init_db)


@pytest.fixture(scope="function")
async def sample_user_id():
    """Generates a random UUID for the user ID."""
    return uuid4()


@pytest.fixture(scope="function")
async def sample_supplier_order(init_db, sample_user_id):
    """Fixture to create a sample 'Pending' supplier order in the test DB."""
    order = SupplierOrder(
        supplierName="Standard Parts Co",
        description="Weekly Restock",
        workOrderId=None,  # General supply order
        createdById=sample_user_id,
        status=SupplierOrderStatus.PENDING,
        orderDate=datetime.now(UTC),
    )
    await order.save()
    return order


# --- Tests ---


async def test_create_supplier_order_general_success(supplier_order_repo, sample_user_id):
    """Test creating a general supply order (no work_order_id) successfully."""

    create_data = SupplierOrderCreate(
        supplierName="General Parts Co", description="Monthly restock of gloves and cleaning supplies", workOrderId=None
    )

    new_order = await supplier_order_repo.create_supplier_order(create_data, created_by_id=sample_user_id)

    # --- Assertions ---
    assert new_order is not None
    assert new_order.id is not None
    assert new_order.supplier_name == "General Parts Co"
    assert new_order.work_order_id is None
    assert new_order.created_by_id == sample_user_id
    assert new_order.status == SupplierOrderStatus.PENDING  # Default

    # Verify items were saved
    assert len(new_order.items) == 1
    assert new_order.items[0].reference == "GLOVE-L"

    # Verify persistence
    found = await SupplierOrder.get(new_order.id)
    assert found is not None


async def test_create_supplier_order_linked_success(supplier_order_repo, sample_user_id):
    """Test creating an order linked to a specific Work Order."""

    work_order_id = ObjectId()

    create_data = SupplierOrderCreate(
        supplierName="Brake Specialists Ltd", description="Brake pads for WO-123", workOrderId=work_order_id
    )

    new_order = await supplier_order_repo.create_supplier_order(create_data, created_by_id=sample_user_id)

    # --- Assertions ---
    assert new_order is not None
    assert new_order.work_order_id == work_order_id
    assert new_order.supplier_name == "Brake Specialists Ltd"

    # Verify sparse index logic implicitly (DB should accept it)
    found = await SupplierOrder.find_one(SupplierOrder.work_order_id == work_order_id)
    assert found is not None
    assert found.id == new_order.id


async def test_get_supplier_order_by_id_success(supplier_order_repo, sample_supplier_order):
    """Test retrieving an existing order by ID."""

    found_order = await supplier_order_repo.get_by_id(sample_supplier_order.id)

    # --- Assertions ---
    assert found_order is not None
    assert found_order.id == sample_supplier_order.id
    assert found_order.supplier_name == "Standard Parts Co"


async def test_get_supplier_order_by_id_not_found(supplier_order_repo):
    """Test retrieving a non-existent ID returns None."""

    result = await supplier_order_repo.get_by_id(ObjectId())
    assert result is None


async def test_get_by_work_order_id_returns_list(supplier_order_repo, sample_user_id):
    """Test filtering orders by Work Order ID."""
    target_wo_id = ObjectId()
    other_wo_id = ObjectId()

    # Create two orders for target WO
    await supplier_order_repo.create_supplier_order(
        SupplierOrderCreate(supplierName="V1", description="Part A", workOrderId=target_wo_id), sample_user_id
    )
    await supplier_order_repo.create_supplier_order(
        SupplierOrderCreate(supplierName="V2", description="Part B", workOrderId=target_wo_id), sample_user_id
    )
    # Create one order for a different WO
    await supplier_order_repo.create_supplier_order(
        SupplierOrderCreate(supplierName="V3", description="Part C", workOrderId=other_wo_id), sample_user_id
    )

    # Act
    results = await supplier_order_repo.get_by_work_order_id(target_wo_id)

    # Assert
    assert isinstance(results, list)
    assert len(results) == 2
    assert all(o.work_order_id == target_wo_id for o in results)


async def test_get_by_status_returns_list(supplier_order_repo, sample_user_id):
    """Test filtering orders by status."""

    # Create a Pending order
    await supplier_order_repo.create_supplier_order(
        SupplierOrderCreate(supplierName="Pending Vendor", description="Pending", workOrderId=None), sample_user_id
    )

    # Create an order and manually update it to RECEIVED (simulating existing data state)
    received_order = SupplierOrder(
        supplierName="Received Vendor",
        description="Received",
        workOrderId=None,
        createdById=sample_user_id,
        status=SupplierOrderStatus.RECEIVED,
    )
    await received_order.save()

    # Act: Retrieve PENDING only
    results = await supplier_order_repo.get_by_status(SupplierOrderStatus.PENDING)

    # Assert
    # We expect at least the one we created above (plus maybe fixtures depending on setup)
    assert len(results) >= 1
    assert all(o.status == SupplierOrderStatus.PENDING for o in results)

    # Verify we don't see the received one
    ids = [o.id for o in results]
    assert received_order.id not in ids


async def test_get_by_supplier_name(supplier_order_repo, sample_user_id):
    """Test retrieving orders for a specific supplier."""

    await supplier_order_repo.create_supplier_order(
        SupplierOrderCreate(supplierName="Bosch", description="Parts", workOrderId=None), sample_user_id
    )

    results = await supplier_order_repo.get_by_supplier_name("Bosch")

    assert len(results) >= 1
    assert results[0].supplier_name == "Bosch"


async def test_update_supplier_order_status(supplier_order_repo, sample_supplier_order):
    """Test updating the status of an order."""

    # Act: Change status to ORDERED
    update_data = SupplierOrderUpdate(status=SupplierOrderStatus.ORDERED)
    updated_order = await supplier_order_repo.update(sample_supplier_order.id, update_data)

    # Assert
    assert updated_order is not None
    assert updated_order.id == sample_supplier_order.id
    assert updated_order.status == SupplierOrderStatus.ORDERED
    assert updated_order.updated_at > sample_supplier_order.updated_at

    # Double check persistence
    fetched = await SupplierOrder.get(sample_supplier_order.id)
    assert fetched.status == SupplierOrderStatus.ORDERED


async def test_delete_supplier_order_success(supplier_order_repo, sample_supplier_order):
    """Test successfully deleting an order."""

    was_deleted = await supplier_order_repo.delete(sample_supplier_order.id)

    # --- Assertions ---
    assert was_deleted is True

    # Verify it's gone
    found = await SupplierOrder.get(sample_supplier_order.id)
    assert found is None


async def test_delete_supplier_order_not_found(supplier_order_repo):
    """Test deleting a non-existent ID returns False."""

    was_deleted = await supplier_order_repo.delete(ObjectId())
    assert was_deleted is False
