from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel

class AppointmentStatus(str, Enum):
    """Enumeration of possible appointment statuses."""

    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

#--- Beanie Document (DB model) ---
class Appointment(Document):
    client_id: Annotated[ObjectId, Indexed()] = Field(..., alias="clientId")
    vehicle_id: Annotated[ObjectId, Indexed()] | None = Field(None, alias="vehicleId")
    work_order_id: Annotated[ObjectId, Indexed()] | None = Field(None, alias="workOrderId")

    notes: str | None = Field(None)
    status: Annotated[AppointmentStatus, Indexed()] = Field(default=AppointmentStatus.SCHEDULED)

    appointment_date: datetime = Field(..., alias="appointmentDate")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, 
                              arbitrary_types_allowed=True)
    
    class Settings:
        name = "appointments"  # collection name

        indexes = [
            IndexModel([("appointmentDate", -1)]),
            IndexModel([("clientId", 1)]),
            IndexModel([("status", 1), ("appointmentDate", -1)])]

    # keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)


class AppointmentCreate(BaseModel):
    """Schema for creating a new Appointment."""

    client_id: ObjectId = Field(..., alias="clientId")
    appointment_date: datetime = Field(..., alias="appointmentDate")
    notes: str | None = Field(None)

    model_config = ConfigDict(populate_by_name=True, 
                              arbitrary_types_allowed=True)


class AppointmentUpdate(BaseModel):
    """Schema for updating an Appointment."""

    notes: str | None = Field(None)
    status: AppointmentStatus | None = Field(None)

    vehicle_id: ObjectId | None = Field(None, alias="vehicleId")
    work_order_id: ObjectId | None = Field(None, alias="workOrderId")

    model_config = ConfigDict(populate_by_name=True, 
                              arbitrary_types_allowed=True)


class AppointmentOut(BaseModel):
    """Full Appointment schema for API responses."""

    id: str = Field(..., alias="_id")  # Beanie/Pydantic automatically handle ObjectId to str

    appointment_date: datetime = Field(..., alias="appointmentDate")

    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,  # Allows Beanie doc to be mapped to this schema
        arbitrary_types_allowed=True,  # For Decimal128
    )
