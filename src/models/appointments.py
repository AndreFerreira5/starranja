from datetime import UTC, datetime
from typing import Annotated
from enum import Enum

from beanie import Document, Indexed
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

class AppointmentStatus(str, Enum):
    """Enumeration of possible appointment statuses."""

    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class Appointment(Document):
    client_id: Annotated[ObjectId, Indexed()] = Field(..., alias="clientId")
    vehicle_id: Annotated[ObjectId, Indexed()] | None = Field(None, alias="vehicleId")
    work_order_id: Annotated[ObjectId, Indexed()] | None = Field(None, alias="workOrderId")

    notes: str | None = Field(None)
    status: Annotated[AppointmentStatus, Indexed()] = Field(default=AppointmentStatus.SCHEDULED)

    appointment_date: datetime = Field(..., alias="appointmentDate")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        name = "appointments"  # collection name

    # keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)

class AppointmentCreate(BaseModel):
    """Schema for creating a new Appointment."""

    client_id: ObjectId = Field(..., alias="clientId")
    appointment_date: datetime = Field(..., alias="appointmentDate")
    notes: str | None = Field(None)

    model_config = ConfigDict(populate_by_name=True)

class appointmentUpdate(BaseModel):
    """Schema for updating an Appointment. """

    notes: str | None = Field(None)
    status: AppointmentStatus | None = Field(None)

    vehicle_id: ObjectId | None = Field(None, alias="vehicleId")
    work_order_id: ObjectId | None = Field(None, alias="workOrderId")

    appointment_date: datetime | None = Field(None, alias="appointmentDate") # is appointment date updatable?
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

class AppointmentOut(BaseModel):
    """Full Appointment schema for API responses."""

    id: str = Field(..., alias="_id")  # Beanie/Pydantic automatically handle ObjectId to str

    appointment_date: datetime = Field(..., alias="appointmentDate")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")