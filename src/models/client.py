from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed, Insert, Replace, Save, before_event
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- Nested type ----
class Address(BaseModel):
    street: str | None = Field(None, alias="street")
    city: str | None = Field(None, alias="city")
    zip_code: str | None = Field(None, alias="zipCode")

    model_config = ConfigDict(populate_by_name=True)


# ---- Beanie Document (DB model) ----
class Client(Document):
    # Required fields
    name: str = Field(...)
    nif: Annotated[str, Indexed(unique=True)] = Field(...)
    phone: Annotated[str, Indexed()] = Field(...)

    email: EmailStr | None = Field(None)
    address: Address | None = Field(None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        name = "clients"  # collection name

    @before_event([Save, Replace])
    def _update_timestamps(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(UTC)


# ---- Pydantic Schemas (FastAPI I/O) ----


class AddressCreate(Address):
    pass  # everything in Address is required on create


class AddressUpdate(BaseModel):
    street: str | None = None
    city: str | None = None
    zip_code: str | None = Field(None, alias="zipCode")

    model_config = ConfigDict(populate_by_name=True)


class ClientBase(BaseModel):
    name: str
    nif: str
    phone: str

    # Optional on create
    email: EmailStr | None = None
    address: AddressCreate | None = None

    model_config = ConfigDict(populate_by_name=True)


# - Partial update; all fields optional
class ClientCreate(ClientBase):
    pass  # everything in ClientBase is required on create


# - Partial update; all fields optional
class ClientUpdate(BaseModel):
    name: str | None = None
    nif: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: AddressUpdate | None = None

    model_config = ConfigDict(populate_by_name=True)


class ClientOut(ClientBase):
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
