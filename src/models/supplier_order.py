from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from beanie import Document
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel


# --- Enums ---
class SupplierOrderStatus(str, Enum):
    """Enumeration of possible supplier order statuses."""

    PENDING = "Pending"
    ORDERED = "Ordered"
    SHIPPED = "Shipped"
    RECEIVED = "Received"
    CANCELLED = "Cancelled"


# ---- Beanie Document (DB model) ----
class SupplierOrder(Document):
    """
    Main Beanie document model for 'supplierOrders'.
    Handles both specific Work Order parts and general internal supplies.
    """

    # --- Core Info ---
    supplier_name: str = Field(..., alias="supplierName")
    description: str = Field(..., description="Summary of the order (e.g. 'Brake Parts for WO-2025-001')")

    # --- Links ---
    # Optional: Only present if this order is strictly for a specific repair job
    work_order_id: ObjectId | None = Field(None, alias="workOrderId")

    # User (PostgreSQL) who placed the order
    created_by_id: UUID = Field(..., alias="createdById")

    # --- Status ---
    status: SupplierOrderStatus = Field(default=SupplierOrderStatus.PENDING)

    # --- Date ---
    order_date: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="orderDate")

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,  # Required for ObjectId
    )

    class Settings:
        name = "supplierOrders"

        indexes = [
            # Fast lookup for orders linked to a specific job
            # Sparse ensures we don't index documents where workOrderId is null.
            IndexModel([("workOrderId", 1)], sparse=True),
            # Dashboard filtering (e.g., "Show all Pending orders")
            IndexModel([("status", 1)]),
            # History sorting (Newest first)
            IndexModel([("createdAt", -1)]),
            # Vendor history
            IndexModel([("supplierName", 1)]),
        ]

    # Keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)


# ---- Pydantic Schemas (FastAPI I/O) ----
class SupplierOrderCreate(BaseModel):
    """Schema for creating a new Supplier Order."""

    supplier_name: str = Field(..., alias="supplierName")
    description: str
    work_order_id: ObjectId | None = Field(None, alias="workOrderId")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class SupplierOrderUpdate(BaseModel):
    """Schema for updating a Supplier Order."""

    supplier_name: str | None = Field(None, alias="supplierName")
    description: str | None = None
    status: SupplierOrderStatus | None = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class SupplierOrderOut(BaseModel):
    """Full Supplier Order schema for API responses."""

    id: str = Field(..., alias="_id")
    supplier_name: str = Field(..., alias="supplierName")
    description: str
    work_order_id: str | None = Field(None, alias="workOrderId")
    status: SupplierOrderStatus
    created_by_id: UUID = Field(..., alias="createdById")
    order_date: datetime = Field(..., alias="orderDate")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True, arbitrary_types_allowed=True)
