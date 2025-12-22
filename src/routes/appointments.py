from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_appointments_repo
from src.models.appointments import Appointment, AppointmentCreate, AppointmentUpdate
from src.repository.appointments import AppointmentRepo

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
)


@router.post("/", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> Appointment:
    """Create a new appointment."""
    try:
        appointment = await repo.create_appointment(appointment_data)
        return appointment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{appointment_id}", response_model=Appointment | None)
async def get_appointment(
    appointment_id: ObjectId,
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> Appointment:
    """Retrieve an appointment by its ID."""

    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    appointment = await repo.get_appointment_by_id(ObjectId(appointment_id))

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return appointment


@router.get("/", response_model=list[Appointment] | None)
async def list_appointments(
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
    vehicle_id: ObjectId | None = None,
    client_id: ObjectId | None = None,
) -> list[Appointment] | None:
    """List all appointments."""

    if vehicle_id:
        appointments = await repo.get_appointments_by_vehicle_id(vehicle_id)

        if not appointments:
            raise HTTPException(status_code=404, detail="No appointments found for the given vehicle ID")

        return appointments

    if client_id:
        appointments = await repo.get_appointments_by_client_id(ObjectId(client_id))

        if not appointments:
            raise HTTPException(status_code=404, detail="No appointments found for the given client ID")

        return appointments

    return None


@router.patch("/{appointment_id}", response_model=Appointment)
async def update_appointment(
    appointment_id: ObjectId,
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
    appointment_id: ObjectId,
    repo: Annotated[AppointmentRepo, Depends(get_appointments_repo)],
) -> None:
    """Delete an appointment by its ID."""

    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="Invalid appointment ID format")

    deleted = await repo.delete_appointment(ObjectId(appointment_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment not found")
