from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from beanie import Document, Indexed
from bson import ObjectId
from bson.decimal128 import Decimal128
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel

# Importing the WorkOrderItem from work_orders.py
# This is crucial for the "snapshot" of items
if TYPE_CHECKING:
    from .work_orders import WorkOrderItem
else:
    try:
        from .work_orders import WorkOrderItem
    except ImportError:
        # Runtime fallback only; (mypy will ignore this)
        class WorkOrderItem(BaseModel):
            type: str
            description: str
            reference: str
            quantity: Decimal128
            unit_price_without_iva: Decimal128 = Field(..., alias="unitPriceWithoutIVA")
            iva_rate: Decimal128
            total_price_with_iva: Decimal128 = Field(..., alias="totalPriceWithIVA")
            model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


# --- Enums  ---
class InvoiceStatus(str, Enum):
    """Enumeration of possible invoice statuses."""

    EMITTED = "Emitted"
    PAID = "Paid"
    CANCELED = "Canceled"


# ---- Embedded Schemas ----
class InvoiceAddress(BaseModel):
    """Embedded snapshot of an address for an invoice."""

    street: str | None = None
    city: str | None = None
    zip_code: str | None = Field(None, alias="zipCode")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InvoiceClientDetails(BaseModel):
    """Embedded snapshot of client details for an invoice."""

    name: str
    nif: str
    address: InvoiceAddress

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InvoiceVehicleDetails(BaseModel):
    """Embedded snapshot of vehicle details for an invoice."""

    license_plate: str = Field(..., alias="licensePlate")
    brand: str
    model: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


# ---- Beanie Document (DB model) ----
class Invoice(Document):
    """
    Main Beanie document model for the 'invoices' collection.
    Represents a finalized, immutable billing record.
    """

    # --- Core Invoice Info ---
    invoice_number: str = Field(..., alias="invoiceNumber")
    invoice_date: Annotated[datetime, Indexed()] = Field(..., alias="invoiceDate")
    status: Annotated[InvoiceStatus, Indexed()] = Field(default=InvoiceStatus.EMITTED)

    # --- References ---
    work_order_id: Annotated[ObjectId, Indexed()] = Field(..., alias="workOrderId")
    client_id: Annotated[ObjectId, Indexed()] = Field(..., alias="clientId")
    emitted_by_id: UUID = Field(..., alias="emittedById")  # User (PostgreSQL) UUID

    # --- Snapshot Data ---
    client_details: InvoiceClientDetails = Field(..., alias="clientDetails")
    vehicle_details: InvoiceVehicleDetails = Field(..., alias="vehicleDetails")
    items: list[WorkOrderItem] = Field(...)  # Full copy of items from WorkOrder

    # --- Snapshot Totals ---
    total_without_iva: Decimal128 = Field(..., alias="totalWithoutIVA")
    total_iva: Decimal128 = Field(..., alias="totalIVA")
    total_with_iva: Decimal128 = Field(..., alias="totalWithIVA")

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,  # Required for Decimal128
    )

    class Settings:
        name = "invoices"
        # Define complex/unique indexes
        indexes = [
            # Ensures no duplicate invoice numbers (fiscal requirement)
            IndexModel([("invoiceNumber", 1)], unique=True),
            # Ensures a work order can only be invoiced once
            IndexModel([("workOrderId", 1)], unique=True),
        ]

    # Keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)


# ---- Pydantic Schemas (FastAPI I/O) ----
class InvoiceCreate(BaseModel):
    """
    Schema for creating a new Invoice.
    The backend service will take this WorkOrder ID,
    verify RB01, and perform the snapshot.
    """

    work_order_id: ObjectId = Field(..., alias="workOrderId")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InvoiceUpdate(BaseModel):
    """
    Schema for updating an Invoice.
    Typically, only the status is updatable (e.g., to 'Paid' or 'Canceled').
    """

    status: InvoiceStatus

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InvoiceOut(BaseModel):
    """Full Invoice schema for API responses."""

    id: str = Field(..., alias="_id")  # ObjectId serialized to string
    invoice_number: str = Field(..., alias="invoiceNumber")
    invoice_date: datetime = Field(..., alias="invoiceDate")
    status: InvoiceStatus

    work_order_id: str = Field(..., alias="workOrderId")
    client_id: str = Field(..., alias="clientId")
    emitted_by_id: UUID = Field(..., alias="emittedById")

    client_details: InvoiceClientDetails = Field(..., alias="clientDetails")
    vehicle_details: InvoiceVehicleDetails = Field(..., alias="vehicleDetails")
    items: list[WorkOrderItem]

    total_without_iva: Decimal128 = Field(..., alias="totalWithoutIVA")
    total_iva: Decimal128 = Field(..., alias="totalIVA")
    total_with_iva: Decimal128 = Field(..., alias="totalWithIVA")

    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,  # Allows Beanie doc to be mapped to this schema
        arbitrary_types_allowed=True,  # For Decimal128
    )
