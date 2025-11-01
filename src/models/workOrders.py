from datetime import datetime
from enum import Enum

from beanie import Document, Indexed
from bson import ObjectId, Decimal128
from pydantic import BaseModel, ConfigDict, Field, constr
from uuid import UUID
from typing import List, Optional


# --- Enums ---
class WorkOrderStatus(str, Enum):
    """Enumeration of possible work order statuses."""
    AWAITING_APPROVAL = "AwaitingApproval"
    APPROVED = "Approved"
    AWAITING_PARTS = "AwaitingParts"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    INVOICED = "Invoiced"
    DELIVERED = "Delivered"


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
    status: Indexed(WorkOrderStatus)
    is_active: bool = Field(..., alias="isActive")  # For RB02 index

    # --- Embedded Data ---
    quote: Optional[Quote] = Field(default_factory=Quote)
    items: List[WorkOrderItem] = Field(default=[])
