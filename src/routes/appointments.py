from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_appointments_repo
from src.models.appointments import Appointment, AppointmentCreate, AppointmentOut, AppointmentUpdate
from src.repository.appointments import AppointmentRepo

router = APIRouter()


@router.post("/", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> Appointment:
    """Create a new appointment."""
    try:
        appointment = await repo.create_appointment(appointment_data)
        return appointment
    except Exception as e:
        # It's good practice to log the error here
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: str,  # Changed from ObjectId to str to let Pydantic/FastAPI handle the path param parsing
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> Appointment:
    """Retrieve an appointment by its ID."""

    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    appointment = await repo.get_appointment_by_id(ObjectId(appointment_id))

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return appointment


@router.get("/", response_model=list[AppointmentOut])
async def list_appointments(
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
    vehicle_id: str | None = None,
    client_id: str | None = None,
) -> list[Appointment]:
    """List all appointments."""

    if vehicle_id:
        if not ObjectId.is_valid(vehicle_id):
            raise HTTPException(status_code=400, detail="Invalid vehicle ID format")

        appointments = await repo.get_appointments_by_vehicle_id(ObjectId(vehicle_id))

        # If strict 404 is desired for empty filters:
        if not appointments:
            raise HTTPException(status_code=404, detail="No appointments found for the given vehicle ID")

        return appointments

    if client_id:
        if not ObjectId.is_valid(client_id):
            raise HTTPException(status_code=400, detail="Invalid client ID format")

        appointments = await repo.get_appointments_by_client_id(ObjectId(client_id))

        if not appointments:
            raise HTTPException(status_code=404, detail="No appointments found for the given client ID")

        return appointments

    return await repo.get_all()


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: str,
    appointment_data: AppointmentUpdate,
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> Appointment:
    """Update an existing appointment."""

    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    appointment = await repo.update_appointment(ObjectId(appointment_id), appointment_data)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: str,
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> None:
    """Delete an appointment by its ID."""

    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    deleted = await repo.delete_appointment(ObjectId(appointment_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment not found")
