from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

VIN = Annotated[str, StringConstraints(min_length=17, max_length=17)]


# - This is the main entity model, as it is defined in the db table, it is used
# - The (Document) is a base class for MongoDB models,
#   that means the Beanie will map the class to the collection - this is done in the class Settings below

# - Indexed means the field will have an Index for faster queries


# - Field is just for us to keep the model properties named correctly with python (snake_case) and still use the
#   table fields original name (camelCase)
class Vehicle(Document):
    client_id: Annotated[ObjectId, Indexed()]
    license_plate: Annotated[str, Indexed(unique=True)] = Field(..., alias="licensePlate")
    brand: str
    model: str = Field(..., min_length=1)
    kilometers: int = Field(ge=0)
    vin: Annotated[VIN, Indexed(unique=True)]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)  # allow snake_case in code, camelCase in payloads

    class Settings:
        name = "vehicles"  # collection name

    # keep updated_at field fresh
    async def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return await super().save(*args, **kwargs)


# ---- Pydantic Schemas (FastAPI I/O) ----
# this are example uses for the requests, we dont use
# the Document class for everything so we dont expose internal fields and only expose necessary fields for the requests
# and only the declared fields can be changed


# - This is the base schema for the vehicles, it is only used for the
#   others schemas to inherit so we dont have all the fields declared in
#   all the schemas
class VehicleBase(BaseModel):
    license_plate: str = Field(..., alias="licensePlate")
    brand: str
    model: str
    kilometers: int = Field(ge=0)
    vin: VIN

    model_config = ConfigDict(populate_by_name=True)


# - This is a schema for when creating a vehicle, it inherits the VehicleBase schema
#   defined above and has client_id because when creating a vehicle we need to attach
#   it to its owner/client
class VehicleCreate(VehicleBase):
    client_id: ObjectId = Field(..., alias="clientId")


class VehicleUpdate(BaseModel):
    kilometers: int | None = Field(None, ge=0)

    model_config = ConfigDict(populate_by_name=True)


class VehicleOut(VehicleBase):
    id: str = Field(alias="_id")
    client_id: str = Field(alias="clientId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
