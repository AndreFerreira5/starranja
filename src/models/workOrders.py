from datetime import datetime, timezone
from enum import Enum

from beanie import Document, Indexed
from bson import ObjectId, Decimal128
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import List, Optional
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
    client_observations: Optional[str] = Field(None, alias="clientObservations")
    diagnostic: Optional[str] = Field(None)
    is_approved: bool = Field(default=False, alias="isApproved")

    model_config = ConfigDict(populate_by_name=True)  # allow snake_case in code, camelCase in payloads


class WorkOrderItem(BaseModel):
    """Embedded schema for a single line item (part or labor)."""
    type: WorkOrderItemType
    description: str
    reference: str
    quantity: Decimal128 = Field(..., ge=0)
    unit_price_without_iva: Decimal128 = Field(..., alias="unitPriceWithoutIVA")
    iva_rate: Decimal128 = Field(..., ge=0, le=1)
    total_price_with_iva: Decimal128 = Field(..., alias="totalPriceWithIVA")

    model_config = ConfigDict(populate_by_name=True)


# ---- Beanie Document (DB model) ----
class WorkOrder(Document):
    # --- References & Core IDs ---
    work_order_number: Indexed(str, unique=True) = Field(..., alias="workOrderNumber")
    client_id: Indexed(ObjectId) = Field(..., alias="clientId")
    vehicle_id: ObjectId = Field(..., alias="vehicleId")  # Indexed via partial index
    created_by_id: UUID = Field(..., alias="createdById")  # User (PostgreSQL) who created the WO - UUID
    mechanics_ids: Optional[List[UUID]] = Field(default=[], alias="mechanicsIds")  # Array of String (UUIDs)
    # referencing the users table in PostgreSQL.

    # --- Status & Flow Control ---
    status: Indexed(
        WorkOrderStatus,
        default=WorkOrderStatus.AWAITING_DIAGNOSTIC
    )
    is_active: bool = Field(default=True, alias="isActive")  # Default to True for new WOs

    # --- Embedded Data ---
    quote: Optional[Quote] = Field(default_factory=Quote)
    items: List[WorkOrderItem] = Field(default=[])

    # --- Totals (Optional, as they are calculated) ---
    final_total_price_without_iva: Optional[Decimal128] = Field(None, alias="finalTotalPriceWithoutIVA")
    final_total_iva: Optional[Decimal128] = Field(None, alias="finalTotalIVA")
    final_total_price_with_iva: Optional[Decimal128] = Field(None, alias="finalTotalPriceWithIVA")

    # --- Timestamps ---
    entry_date: Indexed(datetime) = Field(..., alias="entryDate")
    diagnosis_registered_at: Optional[datetime] = Field(None, alias="diagnosisRegisteredAt")
    quote_approved_at: Optional[datetime] = Field(None, alias="quoteApprovedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    delivered_at: Optional[datetime] = Field(None, alias="deliveredAt")
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc), alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.now(timezone.utc), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True  # Required for Decimal128
    )

    class Settings:
        name = "workOrders"

        # All complex indexes are define here.
        # Beanie's `Indexed()` wrapper handles the simple ones.
        indexes = [
            # Implements RB02 (FerretDB/DocumentDB compatible)
            IndexModel(
                [("vehicleId", 1)],
                unique=True,
                partialFilterExpression={"isActive": True}
            ),

            # Optimizes complex Dashboard queries (RF10),
            # filtering by status (e.g., 'InProgress') and sorting by date (newest/oldest)
            IndexModel(
                [("status", 1), ("entryDate", -1)]
            ),

            # Index for mechanics dashboard
            IndexModel(
                [("mechanicsIds", 1)]
            )
        ]

    # Keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)


# ---- Pydantic Schemas (FastAPI I/O) ----
class WorkOrderCreate(BaseModel):
    """Schema for creating a new Work Order."""
    client_id: ObjectId = Field(..., alias="clientId")
    vehicle_id: ObjectId = Field(..., alias="vehicleId")
    entry_date: datetime = Field(..., alias="entryDate")
    client_observations: Optional[str] = Field(None, alias="clientObservations")

    model_config = ConfigDict(populate_by_name=True)


class WorkOrderUpdate(BaseModel):
    """Schema for updating a Work Order. All fields are optional."""
    mechanics_ids: Optional[List[UUID]] = Field(None, alias="mechanicsIds")
    status: Optional[WorkOrderStatus] = Field(None)
    is_active: Optional[bool] = Field(None, alias="isActive")
    quote: Optional[Quote] = Field(None)
    items: Optional[List[WorkOrderItem]] = Field(None)

    model_config = ConfigDict(populate_by_name=True)

    class WorkOrderOut(BaseModel):
        """Full Work Order schema for API responses."""
        id: str = Field(..., alias="_id")  # Beanie/Pydantic automatically handle ObjectId to str
        work_order_number: str = Field(..., alias="workOrderNumber")
        client_id: str = Field(..., alias="clientId")  # ObjectId serialized to string
        vehicle_id: str = Field(..., alias="vehicleId")  # ObjectId serialized to string
        created_by_id: UUID = Field(..., alias="createdById")
        mechanics_ids: Optional[List[UUID]] = Field(None, alias="mechanicsIds")

        status: WorkOrderStatus
        is_active: bool = Field(..., alias="isActive")

        quote: Optional[Quote] = Field(None)
        items: List[WorkOrderItem] = Field(default=[])

        final_total_price_without_iva: Optional[Decimal128] = Field(None, alias="finalTotalPriceWithoutIVA")
        final_total_iva: Optional[Decimal128] = Field(None, alias="finalTotalIVA")
        final_total_price_with_iva: Optional[Decimal128] = Field(None, alias="finalTotalPriceWithIVA")

        entry_date: datetime = Field(..., alias="entryDate")
        diagnosis_registered_at: Optional[datetime] = Field(None, alias="diagnosisRegisteredAt")
        quote_approved_at: Optional[datetime] = Field(None, alias="quoteApprovedAt")
        completed_at: Optional[datetime] = Field(None, alias="completedAt")
        delivered_at: Optional[datetime] = Field(None, alias="deliveredAt")
        created_at: datetime = Field(..., alias="createdAt")
        updated_at: datetime = Field(..., alias="updatedAt")

        model_config = ConfigDict(
            populate_by_name=True,
            from_attributes=True,  # Allows Beanie doc to be mapped to this schema
            arbitrary_types_allowed=True  # For Decimal128
        )
