from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from beanie import Document, Indexed
from bson import Decimal128, ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel

# Importing the WorkOrderItem from workOrders.py
# This is crucial for the "snapshot" of items
try:
    from .workOrders import WorkOrderItem
except ImportError:
    # Handle standalone execution or define a placeholder if needed
    class WorkOrderItem(BaseModel):
        type: str
        description: str
        reference: str
        quantity: Decimal128
        unit_price_without_iva: Decimal128 = Field(..., alias="unitPriceWithoutIVA")
        iva_rate: Decimal128
        total_price_with_iva: Decimal128 = Field(..., alias="totalPriceWithIVA")
        model_config = ConfigDict(populate_by_name=True)


# --- Enums  ---
class InvoiceStatus(str, Enum):
    """Enumeration of possible invoice statuses."""
    EMITTED = "Emitted"
    PAID = "Paid"
    CANCELED = "Canceled"


# ---- Embedded Schemas ----
class InvoiceAddress(BaseModel):
    """Embedded snapshot of an address for an invoice."""
    street: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = Field(None, alias="zipCode")

    model_config = ConfigDict(populate_by_name=True)


class InvoiceClientDetails(BaseModel):
    """Embedded snapshot of client details for an invoice."""
    name: str
    nif: str
    address: InvoiceAddress

    model_config = ConfigDict(populate_by_name=True)


class InvoiceVehicleDetails(BaseModel):
    """Embedded snapshot of vehicle details for an invoice."""
    license_plate: str = Field(..., alias="licensePlate")
    brand: str
    model: str

    model_config = ConfigDict(populate_by_name=True)


# ---- Beanie Document (DB model) ----
class Invoice(Document):
    """
    Main Beanie document model for the 'invoices' collection.
    Represents a finalized, immutable billing record.
    """
    # --- Core Invoice Info ---
    invoice_number: Indexed(str, unique=True) = Field(..., alias="invoiceNumber")
    invoice_date: Indexed(datetime) = Field(..., alias="invoiceDate")
    status: Indexed(InvoiceStatus) = Field(default=InvoiceStatus.EMITTED)

    # --- References ---
    work_order_id: Indexed(ObjectId, unique=True) = Field(..., alias="workOrderId")
    client_id: Indexed(ObjectId) = Field(..., alias="clientId")
    emitted_by_id: UUID = Field(..., alias="emittedById") # User UUID

    # --- Snapshot Data ---
    client_details: InvoiceClientDetails = Field(..., alias="clientDetails")
    vehicle_details: InvoiceVehicleDetails = Field(..., alias="vehicleDetails")
    items: List[WorkOrderItem] = Field(...) # Full copy of items from WorkOrder

    # --- Snapshot Totals ---
    total_without_iva: Decimal128 = Field(..., alias="totalWithoutIVA")
    total_iva: Decimal128 = Field(..., alias="totalIVA")
    total_with_iva: Decimal128 = Field(..., alias="totalWithIVA")

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True # Required for Decimal128
    )

    class Settings:
        name = "invoices"
        # Indexes are defined above using Indexed() wrapper.
        # No complex compound indexes were specified other than the unique ones.

    # Keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)