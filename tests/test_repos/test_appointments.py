from datetime import UTC, datetime

import pytest
from bson import ObjectId
from fastapi import HTTPException  # <-- Import the exception

from src.models.appointments import Appointment, AppointmentCreate, AppointmentStatus, AppointmentUpdate

# Import  models
from src.models.client import Client
from src.models.vehicle import Vehicle

# Import the repository to test
from src.repository.appointments import AppointmentRepo

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def appointment_repo(init_db):
    """Fixture to provide a clean AppointmentRepo instance for each test."""
    return AppointmentRepo(init_db)  # init_db provides the db connection


@pytest.fixture(scope="function")
async def sample_client(init_db):
    """Fixture to create a sample client in the test DB."""
    client = Client(
        name="Test Client",
        nif="123456789",
        phone="912345678",
        # ... other required Client fields
    )
    await client.save()
    return client


@pytest.fixture(scope="function")
async def sample_vehicle(init_db, sample_client):
    """Fixture to create a sample vehicle linked to the sample client."""
    vehicle = Vehicle(
        client_id=sample_client.id,
        license_plate="AA-00-BB",
        brand="Test",
        model="Model",
        kilometers=1000,
        vin="1234567890ABCDEFG",
        # ... other required Vehicle fields
    )
    await vehicle.save()
    return vehicle


@pytest.fixture(scope="function")
async def sample_appointment(init_db, sample_client, sample_vehicle):
    """Fixture to create a sample appointment in the test DB."""
    appointment = Appointment(
        client_id=sample_client.id,
        vehicle_id=sample_vehicle.id,
        appointment_date=datetime.now(UTC),
        status=AppointmentStatus.SCHEDULED,
    )
    await appointment.save()
    return appointment


# --- Tests ---


async def test_create_appointment_success(appointment_repo, sample_client):
    """Test creating a new appointment successfully."""
    create_data = AppointmentCreate(
        client_id=sample_client.id,
        appointment_date=datetime.now(UTC),
        notes="Test appointment",
        status=AppointmentStatus.SCHEDULED,
    )

    # This will fail with NotImplementedError
    new_appointment = await appointment_repo.create_appointment(create_data)

    # --- Assertions (for when implemented) ---
    assert new_appointment is not None
    assert new_appointment.id is not None
    assert new_appointment.client_id == sample_client.id
    assert new_appointment.status == AppointmentStatus.SCHEDULED

    # Verify it was actually saved to the DB
    found = await Appointment.get(new_appointment.id)
    assert found is not None
    assert found.client_id == sample_client.id
    assert found.status == AppointmentStatus.SCHEDULED


async def test_create_appointment_failed(appointment_repo):
    """Test creating an appointment with an invalid client_id fails."""
    create_data = AppointmentCreate(
        client_id=ObjectId(),  # Non-existent client ID
        appointment_date=datetime.now(UTC),
        notes="Invalid appointment",
    )

    # Now, this will catch the HTTPException you're raising
    with pytest.raises(HTTPException):
        await appointment_repo.create_appointment(create_data)


async def test_get_appointment_by_id_success(appointment_repo, sample_appointment):
    # This will fail with NotImplementedError
    found = await appointment_repo.get_appointment_by_id(sample_appointment.id)

    assert found is not None
    assert found.id == sample_appointment.id


async def test_get_appointment_by_id_failed(
    appointment_repo,
):
    # This will fail with NotImplementedError
    found = await appointment_repo.get_appointment_by_id(ObjectId())  # Random, non-existent ID
    assert found is None


async def test_get_appointments_by_client_id_success(appointment_repo, sample_client, sample_appointment):
    # This will fail with NotImplementedError
    found_appointments = await appointment_repo.get_appointments_by_client_id(sample_client.id)

    assert found_appointments is not None
    assert len(found_appointments) >= 1
    assert any(appointment.id == sample_appointment.id for appointment in found_appointments)


async def test_get_appointments_by_client_id_failed(appointment_repo):
    # This will fail with NotImplementedError
    # Random, non-existent client ID
    found_appointments = await appointment_repo.get_appointments_by_client_id(ObjectId())
    assert found_appointments is None


async def test_get_appointments_by_vehicle_id_success(appointment_repo, sample_vehicle, sample_appointment):
    found_appointments = await appointment_repo.get_appointments_by_vehicle_id(sample_vehicle.id)

    assert found_appointments is not None
    assert len(found_appointments) >= 1
    assert any(appointment.id == sample_appointment.id for appointment in found_appointments)


async def test_get_appointments_by_vehicle_id_failed(appointment_repo):
    # This will fail with NotImplementedError
    # Random, non-existent vehicle ID
    found_appointments = await appointment_repo.get_appointments_by_vehicle_id(ObjectId())

    assert found_appointments is None


async def test_update_appointment_success(appointment_repo, sample_appointment):
    update_data = AppointmentUpdate(
        id=sample_appointment.id,
        notes="Updated notes",
        status=AppointmentStatus.CANCELLED,
    )

    # This will fail with NotImplementedError
    updated_appointment = await appointment_repo.update_appointment(sample_appointment.id, update_data)

    # --- Assertions (for when implemented) ---
    assert updated_appointment is not None
    assert updated_appointment.id == sample_appointment.id
    assert updated_appointment.notes == update_data.notes
    assert updated_appointment.status == update_data.status

    # Verify it was actually updated in the DB
    found = await Appointment.get(updated_appointment.id)
    assert found is not None
    assert found.notes == update_data.notes
    assert found.status == update_data.status


async def test_update_appointment_failed(appointment_repo):
    update_data = AppointmentUpdate(
        id=ObjectId(),  # Non-existent ID
        notes="Should not update",
        status=AppointmentStatus.CANCELLED,
    )

    # This will fail with NotImplementedError
    updated_appointment = await appointment_repo.update_appointment(ObjectId(), update_data)

    assert updated_appointment is None


async def test_delete_appointment_success(appointment_repo, sample_appointment):
    # This will fail with NotImplementedError

    deleted = await appointment_repo.delete_appointment(sample_appointment.id)

    assert deleted is True

    # Verify it was actually deleted from the DB
    found = await Appointment.get(sample_appointment.id)
    assert found is None


async def test_delete_appointment_failed(appointment_repo):
    # This will fail with NotImplementedError
    # Non-existent ID
    deleted = await appointment_repo.delete_appointment(ObjectId())

    assert deleted is False
