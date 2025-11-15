from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from beanie import Document, Indexed
from bson import ObjectId
from bson.decimal128 import Decimal128
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel


# --- Enums ---
class WorkOrderStatus(str, Enum):
    """Enumeration of possible work order statuses."""

    AWAITING_DIAGNOSTIC = "AwaitingDiagnostic"
    AWAITING_APPROVAL = "AwaitingApproval"
    APPROVED = "Approved"
    AWAITING_PARTS = "AwaitingParts"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    INVOICED = "Invoiced"
    DELIVERED = "Delivered"

    DECLINED = "Declined"  # Customer refused the quote
    CANCELLED = "Cancelled"  # Work stopped for any other reason


class WorkOrderItemType(str, Enum):
    """Enumeration of work order item types."""

    PART = "Part"
    LABOR = "Labor"


# ---- Embedded Schemas ----
class Quote(BaseModel):
    """Embedded schema for the work order's quote."""

    client_observations: str | None = Field(None, alias="clientObservations")
    diagnostic: str | None = Field(None)
    is_approved: bool = Field(default=False, alias="isApproved")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)  # allow snake_case in code, camelCase in payloads


class WorkOrderItem(BaseModel):
    """Embedded schema for a single line item (part or labor)."""

    type: WorkOrderItemType
    description: str
    reference: str
    quantity: Decimal128 = Field(..., ge=0)
    unit_price_without_iva: Decimal128 = Field(..., alias="unitPriceWithoutIVA")
    iva_rate: Decimal128 = Field(..., ge=0, le=1)
    total_price_with_iva: Decimal128 = Field(..., alias="totalPriceWithIVA")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


# ---- Beanie Document (DB model) ----
class WorkOrder(Document):
    # --- References & Core IDs ---
    work_order_number: Annotated[str, Indexed(unique=True)] = Field(..., alias="workOrderNumber")
    client_id: Annotated[ObjectId, Indexed()] = Field(..., alias="clientId")
    vehicle_id: ObjectId = Field(..., alias="vehicleId")  # Indexed via partial index
    created_by_id: UUID = Field(..., alias="createdById")  # User (PostgreSQL) who created the WO - UUID
    mechanics_ids: list[UUID] | None = Field(default=[], alias="mechanicsIds")  # Array of String (UUIDs)
    # referencing the users table in PostgreSQL.

    # --- Status & Flow Control ---
    status: Annotated[WorkOrderStatus, Indexed()] = Field(default=WorkOrderStatus.AWAITING_DIAGNOSTIC)
    is_active: bool = Field(default=True, alias="isActive")  # Default to True for new WOs

    # --- Embedded Data ---
    quote: Quote | None = None
    items: list[WorkOrderItem] = Field(default=[])

    # --- Totals (Optional, as they are calculated) ---
    final_total_price_without_iva: Decimal128 | None = Field(None, alias="finalTotalPriceWithoutIVA")
    final_total_iva: Decimal128 | None = Field(None, alias="finalTotalIVA")
    final_total_price_with_iva: Decimal128 | None = Field(None, alias="finalTotalPriceWithIVA")

    # --- Timestamps ---
    entry_date: Annotated[datetime, Indexed()] = Field(..., alias="entryDate")
    diagnosis_registered_at: datetime | None = Field(None, alias="diagnosisRegisteredAt")
    quote_approved_at: datetime | None = Field(None, alias="quoteApprovedAt")
    completed_at: datetime | None = Field(None, alias="completedAt")
    delivered_at: datetime | None = Field(None, alias="deliveredAt")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,  # Required for Decimal128
    )

    class Settings:
        name = "workOrders"

        # All complex indexes are define here.
        # Beanie's `Indexed()` wrapper handles the simple ones.
        indexes = [
            # Unique WO number (moved from Indexed(..., unique=True) to an explicit IndexModel)
            IndexModel([("workOrderNumber", 1)], unique=True),
            # Implements RB02 (FerretDB/DocumentDB compatible)
            IndexModel([("vehicleId", 1)], unique=True, partialFilterExpression={"isActive": True}),
            # Optimizes complex Dashboard queries (RF10),
            # filtering by status (e.g., 'InProgress') and sorting by date (newest/oldest)
            IndexModel([("status", 1), ("entryDate", -1)]),
            # Index for mechanics dashboard
            IndexModel([("mechanicsIds", 1)]),
        ]

    # Keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)


# ---- Pydantic Schemas (FastAPI I/O) ----
class WorkOrderCreate(BaseModel):
    """Schema for creating a new Work Order."""

    client_id: ObjectId = Field(..., alias="clientId")
    vehicle_id: ObjectId = Field(..., alias="vehicleId")
    entry_date: datetime = Field(..., alias="entryDate")
    client_observations: str | None = Field(None, alias="clientObservations")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class WorkOrderUpdate(BaseModel):
    """Schema for updating a Work Order. All fields are optional."""

    mechanics_ids: list[UUID] | None = Field(None, alias="mechanicsIds")
    status: WorkOrderStatus | None = Field(None)
    is_active: bool | None = Field(None, alias="isActive")
    quote: Quote | None = Field(None)
    items: list[WorkOrderItem] | None = Field(None)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class WorkOrderOut(BaseModel):
    """Full Work Order schema for API responses."""

    id: str = Field(..., alias="_id")  # Beanie/Pydantic automatically handle ObjectId to str
    work_order_number: str = Field(..., alias="workOrderNumber")
    client_id: str = Field(..., alias="clientId")  # ObjectId serialized to string
    vehicle_id: str = Field(..., alias="vehicleId")  # ObjectId serialized to string
    created_by_id: UUID = Field(..., alias="createdById")
    mechanics_ids: list[UUID] | None = Field(None, alias="mechanicsIds")

    status: WorkOrderStatus
    is_active: bool = Field(..., alias="isActive")

    quote: Quote | None = Field(None)
    items: list[WorkOrderItem] = Field(default=[])

    final_total_price_without_iva: Decimal128 | None = Field(None, alias="finalTotalPriceWithoutIVA")
    final_total_iva: Decimal128 | None = Field(None, alias="finalTotalIVA")
    final_total_price_with_iva: Decimal128 | None = Field(None, alias="finalTotalPriceWithIVA")

    entry_date: datetime = Field(..., alias="entryDate")
    diagnosis_registered_at: datetime | None = Field(None, alias="diagnosisRegisteredAt")
    quote_approved_at: datetime | None = Field(None, alias="quoteApprovedAt")
    completed_at: datetime | None = Field(None, alias="completedAt")
    delivered_at: datetime | None = Field(None, alias="deliveredAt")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,  # Allows Beanie doc to be mapped to this schema
        arbitrary_types_allowed=True,  # For Decimal128
    )
