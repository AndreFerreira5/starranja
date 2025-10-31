from datetime import datetime

from typing import Optional
from beanie import Document, Indexed
from pydantic import BaseModel, ConfigDict, Field, EmailStr

# ---- Nested type ----
class Address(BaseModel):
    street: Optional[str] = Field(None, alias="street")
    city: Optional[str] = Field(None, alias="city")
    zip_code: Optional[str] = Field(None, alias="zipCode")

    model_config = ConfigDict(populate_by_name=True)


# ---- Beanie Document (DB model) ----
class Client(Document):
    # Required fields
    name: str = Field(...)
    nif: Indexed(str, unique=True) = Field(...)
    phone: Indexed(str) = Field(...)

    email: Optional[EmailStr] = Field(None)
    address: Optional[Address] = Field(None)

    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

    class Settings:
        name = "clients"  # collection name

    # keep updated_at fresh on save/replace
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)

# ---- Pydantic Schemas (FastAPI I/O) ----

class AddressCreate(Address):
    pass # everything in Address is required on create

class AddressUpdate(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = Field(None, alias="zipCode")

    model_config = ConfigDict(populate_by_name=True)


class ClientBase(BaseModel):
    name: str
    nif: str
    phone: str

    # Optional on create
    email: Optional[EmailStr] = None
    address: Optional[AddressCreate] = None

    model_config = ConfigDict(populate_by_name=True)

# - Partial update; all fields optional
class ClientCreate(ClientBase):
    pass  # everything in ClientBase is required on create

# - Partial update; all fields optional
class ClientUpdate(BaseModel):
    name: Optional[str] = None
    nif: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[AddressUpdate] = None

    model_config = ConfigDict(populate_by_name=True)


class ClientOut(ClientBase):
    id: str = Field(alias="id")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
