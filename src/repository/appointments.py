import logging

from bson import ObjectId

from src.models.appointments import Appointment, AppointmentCreate, AppointmentUpdate

logger = logging.getLogger(__name__)


class AppointmentRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "appointments"

    async def create_appointment(self, appointment_data: AppointmentCreate) -> Appointment:
        """
        Create a new appointment.

        Args:
            appointment_data: Dictionary with appointment data
        Returns:
            Created appointment data with _id, createdAt, and updatedAt fields

        Raises:
            Exception: If there is any issue during creation
        """
        logger.info(f"Creating appointment for client ID {appointment_data.client_id}")

        raise NotImplementedError("create_appointment method not yet implemented")

    async def get_appointment_by_id(self, appointment_id: ObjectId) -> Appointment | None:
        """
        Retrieve an appointment by its ID.

        Args:
            appointment_id: MongoDB ObjectId of the appointment

        Returns:
            Appointment document if found, None otherwise
        """
        logger.info(f"Retrieving appointment by ID: {appointment_id}")

        raise NotImplementedError("get_by_id method not yet implemented")

    async def get_appointments_by_client_id(self, client_id: ObjectId) -> list[Appointment] | None:
        """
        Retrieve appointments by client ID.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of Appointment documents if found, None otherwise
        """
        logger.info(f"Retrieving appointments for client ID: {client_id}")

        raise NotImplementedError("get_by_client_id method not yet implemented")

    async def get_appointments_by_vehicle_id(self, vehicle_id: ObjectId) -> list[Appointment] | None:
        """
        Retrieve appointments by vehicle ID.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            List of Appointment documents if found, None otherwise
        """
        logger.info(f"Retrieving appointments for vehicle ID: {vehicle_id}")

        raise NotImplementedError("get_by_vehicle_id method not yet implemented")

    async def update_appointment(self, appointment_id: ObjectId, update_data: AppointmentUpdate) -> Appointment | None:
        """
        Update an existing appointment.

        Args:
            appointment_id: MongoDB ObjectId of the appointment to update
            update_data: Dictionary with fields to update

        Returns:
            Updated appointment document if found, None otherwise
        """
        logger.info(f"Updating appointment ID: {appointment_id}")

        raise NotImplementedError("update method not yet implemented")

    async def delete_appointment(self, appointment_id: ObjectId) -> bool:
        """
        Delete an appointment by its ID.

        Args:
            appointment_id: MongoDB ObjectId of the appointment to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting appointment ID: {appointment_id}")

        raise NotImplementedError("delete method not yet implemented")
