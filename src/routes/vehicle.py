from typing import Annotated
from uuid import UUID

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_current_user_id, get_vehicle_repo
from src.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate
from src.repository.vehicle import VehicleRepo

router = APIRouter()


@router.post("/", response_model=Vehicle, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    vehicle_repo: Annotated[VehicleRepo, Depends(get_vehicle_repo)],
):
    """
    Create a new vehicle.

    Args:
        vehicle_data: VehicleCreate model with vehicle details
        current_user_id: UUID of the current authenticated user
        vehicle_repo: VehicleRepo instance for database operations

    Returns:
        Created Vehicle model
    """
    try:
        created_vehicle = await vehicle_repo.create_vehicle(vehicle_data)

        return created_vehicle
    except Exception as e:
        raise HTTPException(status_code=409, detail="Vehicle with this license plate already exists") from e


@router.get("/{vehicle_id}", response_model=Vehicle)
async def get_vehicle_by_id(
    vehicle_id: str,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    vehicle_repo: Annotated[VehicleRepo, Depends(get_vehicle_repo)],
):
    """
    Retrieve a vehicle by its ID.

    Args:
        vehicle_id: String representation of the vehicle's ObjectId
        current_user_id: UUID of the current authenticated user
        vehicle_repo: VehicleRepo instance for database operations

    Returns:
        Vehicle model if found
    """

    vehicle = await vehicle_repo.get_by_id(vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return vehicle


@router.get("/", response_model=list[Vehicle] | Vehicle)
async def list_vehicles(
    vehicle_repo: Annotated[VehicleRepo, Depends(get_vehicle_repo)],
    client_id: str | None = None,
    license_plate: str | None = None,
):
    """
    List vehicles, optionally filtering by client ID or license plate.

    Args:
        vehicle_repo: VehicleRepo instance for database operations
        client_id: Optional string representation of the client's ObjectId to filter vehicles
        license_plate: Optional license plate string to filter vehicles
    Returns:
        List of Vehicle models or a single Vehicle model if filtered by license plate
    """
    if license_plate:
        vehicle = await vehicle_repo.get_by_license_plate(license_plate)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return vehicle

    if client_id:
        vehicles = await vehicle_repo.get_by_client_id(ObjectId(client_id))

        if not vehicles:
            raise HTTPException(status_code=404, detail="No vehicles found for the given client ID")
        return vehicles

    return await vehicle_repo.get_all()


@router.patch("/{vehicle_id}", response_model=Vehicle)
async def update_vehicle(
    vehicle_id: str,
    update_data: VehicleUpdate,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    vehicle_repo: Annotated[VehicleRepo, Depends(get_vehicle_repo)],
):
    """
    Update an existing vehicle.

    Args:
        vehicle_id: String representation of the vehicle's ObjectId
        update_data: VehicleUpdate model with updated vehicle details
        current_user_id: UUID of the current authenticated user
        vehicle_repo: VehicleRepo instance for database operations
    Returns:
        Updated Vehicle model
    """
    updated_vehicle = await vehicle_repo.update(vehicle_id, update_data)

    if not updated_vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return updated_vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: str,
    current_user_id: Annotated[UUID, Depends(get_current_user_id)],
    vehicle_repo: Annotated[VehicleRepo, Depends(get_vehicle_repo)],
):
    """
    Delete a vehicle by its ID.

    Args:
        vehicle_id: String representation of the vehicle's ObjectId
        current_user_id: UUID of the current authenticated user
        vehicle_repo: VehicleRepo instance for database operations

    Returns:
        None
    """
    deleted = await vehicle_repo.delete(vehicle_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return None
