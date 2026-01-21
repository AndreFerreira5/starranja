from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.dependencies import get_current_user_id
from src.main import app
from src.models.client import Address, Client
from src.models.invoices import (
    Invoice,
    InvoiceAddress,
    InvoiceClientDetails,
    InvoiceStatus,
    InvoiceVehicleDetails,
)
from src.models.vehicle import Vehicle
from src.models.work_orders import (
    WorkOrder,
    WorkOrderItem,
    WorkOrderStatus,
)
from src.repository.invoices import InvoiceRepo

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


async def test_create_invoice_success(client, sample_work_order):
    """Test creating an invoice successfully."""
    payload = {"workOrderId": str(sample_work_order.id)}

    response = await client.post("/invoices/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert "_id" in response.json()


async def test_create_invoice_work_order_not_found(client):
    """Test creating an invoice with a non-existent work order."""
    non_existent_wo_id = str(ObjectId())
    payload = {"workOrderId": non_existent_wo_id}

    response = await client.post("/invoices/", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_create_invoice_missing_address(client, sample_work_order, sample_client):
    """Test creating an invoice when the client address is missing."""
    # Remove address from sample client
    sample_client.address = None
    await sample_client.save()

    payload = {"workOrderId": str(sample_work_order.id)}

    response = await client.post("/invoices/", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT


async def test_get_invoice_by_id_success(client, sample_invoice):
    """Test retrieving an invoice by ID successfully."""
    invoice_id = str(sample_invoice.id)
    response = await client.get(f"/invoices/{invoice_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["_id"] == str(sample_invoice.id)


async def test_get_invoice_by_id_failed(client):
    """Test retrieving an invoice with an invalid ID format."""
    non_existent_id = str(ObjectId())

    response = await client.get(f"/invoices/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_invoices_by_client_id_success(client, sample_invoice):
    """Test listing invoices filtered by client ID."""
    client_id = str(sample_invoice.client_id)

    response = await client.get(f"/invoices/?client_id={client_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["_id"] == str(sample_invoice.id)


async def test_get_invoice_by_client_id_failed(client):
    """Test retrieving a non-existent invoice by ID."""
    non_existent_id = str(ObjectId())

    response = await client.get(f"/invoices/?client_id={non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_invoices_by_work_order_id_success(client, sample_invoice):
    """Test listing invoices filtered by work order ID."""
    wo_id = str(sample_invoice.work_order_id)

    response = await client.get(f"/invoices/?work_order_id={wo_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["_id"] == str(sample_invoice.id)


async def test_get_invoices_by_work_order_id_failed(client):
    """Test listing invoices with invalid work order ID."""
    non_existent_id = str(ObjectId())

    response = await client.get(f"/invoices/?work_order_id={non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_all_invoices_no_filter(client, sample_invoice):
    """Test retrieving all invoices when no filters are applied."""

    # 1. Create a SECOND invoice
    # Reuse sample_invoice's dependencies for simplicity,
    # but create a new invoice document
    second_invoice = Invoice(
        invoice_number="FT 2025/2",
        invoice_date=datetime.now(UTC),
        status=InvoiceStatus.PAID,
        work_order_id=ObjectId(),  # Random IDs for distinctness
        client_id=sample_invoice.client_id,
        emitted_by_id=sample_invoice.emitted_by_id,
        client_details=sample_invoice.client_details,
        vehicle_details=sample_invoice.vehicle_details,
        items=sample_invoice.items,
        total_without_iva=sample_invoice.total_without_iva,
        total_iva=sample_invoice.total_iva,
        total_with_iva=sample_invoice.total_with_iva,
    )
    await second_invoice.save()

    # 2. Act: Call the endpoint with NO query params
    response = await client.get("/invoices/")

    # 3. Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should be a list
    assert isinstance(data, list)
    # Should contain at least our 2 invoices
    assert len(data) >= 2

    # Verify IDs are present
    returned_ids = [item["_id"] for item in data]
    assert str(sample_invoice.id) in returned_ids
    assert str(second_invoice.id) in returned_ids


async def test_update_invoice_success(client, sample_invoice):
    """Test updating an invoice successfully."""
    invoice_id = str(sample_invoice.id)
    payload = {"status": "Paid"}

    response = await client.patch(f"/invoices/{invoice_id}", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "Paid"

    db_invoice = await Invoice.get(sample_invoice.id)
    assert db_invoice.status == InvoiceStatus.PAID


async def test_update_invoice_failed(client):
    """Test updating a non-existent invoice."""
    non_existent_id = str(ObjectId())
    payload = {"status": InvoiceStatus.PAID}

    response = await client.patch(f"/invoices/{non_existent_id}", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_invoice_success(client, sample_invoice):
    """Test deleting an invoice successfully."""
    invoice_id = str(sample_invoice.id)

    response = await client.delete(f"/invoices/{invoice_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    db_invoice = await Invoice.get(sample_invoice.id)
    assert db_invoice is None


async def test_delete_invoice_failed(client):
    """Test deleting a non-existent invoice."""
    non_existent_id = str(ObjectId())

    response = await client.delete(f"/invoices/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
