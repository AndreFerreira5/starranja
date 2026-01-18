from datetime import UTC, datetime
from uuid import uuid4

import pytest
from bson import ObjectId
from bson.decimal128 import Decimal128  # Required for financial fields
from fastapi import HTTPException

from src.models.client import Address, Client
from src.models.invoices import (
    Invoice,
    InvoiceAddress,
    InvoiceClientDetails,
    InvoiceCreate,
    InvoiceStatus,
    InvoiceUpdate,
    InvoiceVehicleDetails,
)
from src.models.vehicle import Vehicle
from src.models.work_orders import WorkOrder, WorkOrderItem, WorkOrderStatus
from src.repository.invoices import InvoiceRepo

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def invoice_repo(init_db):
    """Fixture to provide a clean InvoiceRepo instance for each test."""
    return InvoiceRepo(init_db)


@pytest.fixture(scope="function")
async def sample_client(init_db):
    """Fixture to create a sample client in the test DB."""
    client = Client(
        name="Test Client",
        nif="123456789",
        phone="912345678",
        email="test@example.com",
        is_active=True,
        address=Address(street="Test St", city="Lisbon", zipCode="1000-001"),
    )
    await client.save()
    return client


@pytest.fixture(scope="function")
async def sample_vehicle(init_db, sample_client):
    """Fixture to create a sample vehicle linked to the sample client."""
    vehicle = Vehicle(
        client_id=sample_client.id,
        license_plate="AA-00-BB",
        brand="Toyota",
        model="Corolla",
        kilometers=1000,
        vin="1234567890ABCDEFG",
    )
    await vehicle.save()
    return vehicle


@pytest.fixture(scope="function")
async def sample_work_order(init_db, sample_client, sample_vehicle):
    """Fixture to create a sample work order linked to the sample client."""
    work_order = WorkOrder(
        work_order_number="WO-2025-0001",
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,
        created_by_id=uuid4(),
        mechanicsIds=[uuid4()],
        status=WorkOrderStatus.AWAITING_DIAGNOSTIC,
        is_active=True,
        # CHANGE: items must be a list []
        items=[
            WorkOrderItem(
                type="Labor",
                description="Brake Fix",
                reference="LAB-001",
                quantity=Decimal128("2.0"),
                unit_price_without_iva=Decimal128(
                    "50.00"
                ),  # Ensure field names match model definition (snake_case vs camelCase)
                iva_rate=Decimal128("0.23"),
                total_price_with_iva=Decimal128("123.00"),
            )
        ],
        final_total_price_without_iva=Decimal128("100.00"),
        final_total_iva=Decimal128("23.00"),
        final_total_price_with_iva=Decimal128("123.00"),
        entry_date=datetime.now(UTC),
    )
    await work_order.save()
    return work_order


@pytest.fixture(scope="function")
async def sample_invoice(init_db, sample_client, sample_work_order, sample_vehicle):
    """
    Fixture to create a COMPLETE sample invoice in the test DB.
    Includes snapshots of client, vehicle, and items.
    """

    vehicle_details = InvoiceVehicleDetails(
        licensePlate=sample_vehicle.license_plate, brand=sample_vehicle.brand, model=sample_vehicle.model
    )

    client_details = InvoiceClientDetails(
        name=sample_client.name,
        nif=sample_client.nif,
        address=InvoiceAddress(
            street=sample_client.address.street,
            city=sample_client.address.city,
            zipCode=sample_client.address.zip_code,
        ),
    )

    # 2. Create Invoice Document
    invoice = Invoice(
        invoice_number="FT 2025/1",
        invoice_date=datetime.now(UTC),
        status=InvoiceStatus.EMITTED,
        # References
        work_order_id=sample_work_order.id,
        client_id=sample_client.id,
        emitted_by_id=uuid4(),  # ID of the user generating the invoice
        # Snapshots
        client_details=client_details,
        vehicle_details=vehicle_details,
        items=sample_work_order.items,
        # Totals
        total_without_iva=sample_work_order.final_total_price_without_iva,
        total_iva=sample_work_order.final_total_iva,
        total_with_iva=sample_work_order.final_total_price_with_iva,
    )

    await invoice.save()
    return invoice


# --- Tests ---


async def test_create_invoice_success(invoice_repo, sample_client, sample_work_order):
    """
    Test creating an invoice.
    Note: The InvoiceCreate model only accepts work_order_id.
    The Repository logic (not shown in provided files) is responsible for fetching
    Client/Vehicle/Items and calculating totals to create the full Invoice document.
    """
    create_data = InvoiceCreate(
        work_order_id=sample_work_order.id,
    )

    # Since the repository implementation wasn't provided in the prompt context,
    # this call relies on your Repo correctly implementing the snapshot logic.
    # If the repo isn't implemented yet, this will fail with NotImplementedError (as expected).
    new_invoice = await invoice_repo.create_invoice(create_data)

    assert new_invoice is not None
    assert new_invoice.id is not None
    assert new_invoice.client_id == sample_client.id
    assert new_invoice.work_order_id == sample_work_order.id
    # Check that snapshot data exists
    assert new_invoice.client_details.nif == sample_client.nif
    assert new_invoice.status == InvoiceStatus.EMITTED


async def test_create_invoice_failed(invoice_repo):
    """Test creating an invoice with invalid Work Order ID fails."""
    create_data = InvoiceCreate(
        work_order_id=ObjectId(),  # Random ID
    )

    with pytest.raises(HTTPException) as exc_info:
        await invoice_repo.create_invoice(create_data)

    # Assuming repository raises 404 if Work Order not found
    assert exc_info.value.status_code == 404


async def test_get_invoice_by_id_success(invoice_repo, sample_invoice):
    """Test retrieving an invoice by its ObjectId."""
    found_invoice = await invoice_repo.get_invoice_by_id(sample_invoice.id)

    assert found_invoice is not None
    assert found_invoice.id == sample_invoice.id
    assert found_invoice.invoice_number == "FT 2025/1"
    assert found_invoice.total_with_iva == Decimal128("123.00")


async def test_get_invoice_by_id_not_found(invoice_repo):
    """Test retrieving a non-existent invoice by its ObjectId."""
    non_existent_id = ObjectId()
    found_invoice = await invoice_repo.get_invoice_by_id(non_existent_id)

    assert found_invoice is None


async def test_get_invoices_by_client_id_success(invoice_repo, sample_client, sample_invoice):
    """Test retrieving invoices by client ID."""
    found_invoices = await invoice_repo.get_invoices_by_client_id(sample_client.id)

    assert found_invoices is not None
    assert len(found_invoices) >= 1
    assert any(invoice.id == sample_invoice.id for invoice in found_invoices)
    # Validate embedded data access
    assert found_invoices[0].client_details.nif == sample_client.nif


async def test_get_invoices_by_client_id_not_found(invoice_repo):
    """Test retrieving invoices for a client ID with no invoices."""
    non_existent_client_id = ObjectId()
    found_invoices = await invoice_repo.get_invoices_by_client_id(non_existent_client_id)

    assert not found_invoices  # Should be empty list or None depending on implementation


async def test_get_invoices_by_work_order_id_success(invoice_repo, sample_work_order, sample_invoice):
    """Test retrieving invoices by work order ID."""
    found_invoices = await invoice_repo.get_invoices_by_work_order_id(sample_work_order.id)

    assert found_invoices is not None
    assert len(found_invoices) >= 1
    assert any(invoice.id == sample_invoice.id for invoice in found_invoices)


async def test_get_invoices_by_work_order_id_not_found(invoice_repo):
    """Test retrieving invoices for a work order ID with no invoices."""
    non_existent_work_order_id = ObjectId()
    found_invoices = await invoice_repo.get_invoices_by_work_order_id(non_existent_work_order_id)

    assert not found_invoices


async def test_update_invoice_success(invoice_repo, sample_invoice):
    """Test updating an existing invoice status."""
    update_data = InvoiceUpdate(status=InvoiceStatus.PAID)

    updated_invoice = await invoice_repo.update_invoice(sample_invoice.id, update_data)

    assert updated_invoice is not None
    assert updated_invoice.id == sample_invoice.id
    assert updated_invoice.status == InvoiceStatus.PAID

    # Verify persistence
    found = await Invoice.get(sample_invoice.id)
    assert found is not None
    assert found.status == InvoiceStatus.PAID


async def test_update_invoice_not_found(invoice_repo):
    """Test updating a non-existent invoice."""
    non_existent_id = ObjectId()
    update_data = InvoiceUpdate(status=InvoiceStatus.PAID)

    updated_invoice = await invoice_repo.update_invoice(non_existent_id, update_data)
    assert updated_invoice is None


async def test_delete_invoice_success(invoice_repo, sample_invoice):
    """Test deleting an existing invoice."""
    deleted = await invoice_repo.delete_invoice(sample_invoice.id)

    assert deleted is True

    # Verify it's actually deleted
    found_invoice = await Invoice.get(sample_invoice.id)
    assert found_invoice is None


async def test_delete_invoice_not_found(invoice_repo):
    """Test deleting a non-existent invoice."""
    non_existent_id = ObjectId()
    deleted = await invoice_repo.delete_invoice(non_existent_id)

    assert deleted is False
