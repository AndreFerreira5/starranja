import logging

from bson import ObjectId
from fastapi import HTTPException

from src.models.appointments import Appointment, AppointmentCreate, AppointmentUpdate
from src.models.client import Client

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

        try:
            # Validate the client_id *before* trying to create the appointment
            client = await Client.get(appointment_data.client_id)

            if not client:
                logger.warning(f"Client not found: {appointment_data.client_id}. Aborting appointment creation.")

                raise HTTPException(
                    status_code=404, 
                    detail=f"Client with id {appointment_data.client_id} not found"
                )
            
            appointment = Appointment(**appointment_data.model_dump())

            await appointment.insert()

            logger.info(f"Appointment created with ID: {appointment.id}")

            return appointment
        
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise

    async def get_appointment_by_id(self, appointment_id: ObjectId) -> Appointment | None:
        """
        Retrieve an appointment by its ID.

        Args:
            appointment_id: MongoDB ObjectId of the appointment

        Returns:
            Appointment document if found, None otherwise
        """
        logger.info(f"Retrieving appointment by ID: {appointment_id}")

        try:
            appointment = await Appointment.get(appointment_id)
            
            if appointment:
                logger.info(f"Appointment found: {appointment}")

            else:
                logger.info("No appointment found with the given ID")
            return appointment
        
        except Exception as e:
            logger.error(f"Error retrieving appointment: {e}")
            raise

    async def get_appointments_by_client_id(self, client_id: ObjectId) -> list[Appointment] | None:
        """
        Retrieve appointments by client ID.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of Appointment documents if found, None otherwise
        """
        logger.info(f"Retrieving appointments for client ID: {client_id}")

        try:
            appointments = await Appointment.find(Appointment.client_id == client_id).to_list()

            if appointments:
                logger.info(f"Found {len(appointments)} appointments for client ID {client_id}")

                return appointments
            
            else:
                logger.info("No appointments found for the given client ID")

                return None
            
        except Exception as e:
            logger.error(f"Error retrieving appointments: {e}")
            raise

    async def get_appointments_by_vehicle_id(self, vehicle_id: ObjectId) -> list[Appointment] | None:
        """
        Retrieve appointments by vehicle ID.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            List of Appointment documents if found, None otherwise
        """
        logger.info(f"Retrieving appointments for vehicle ID: {vehicle_id}")

        try:
            appointments = await Appointment.find(Appointment.vehicle_id == vehicle_id).to_list()

            if appointments:
                logger.info(f"Found {len(appointments)} appointments for vehicle ID {vehicle_id}")

                return appointments
            
            else:
                logger.info("No appointments found for the given vehicle ID")

                return None
            
        except Exception as e:
            logger.error(f"Error retrieving appointments: {e}")
            raise

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

        try:
            appointment = await Appointment.get(appointment_id)

            if not appointment:
                logger.info("No appointment found with the given ID")
                return None

            update_dict = update_data.model_dump(by_alias=True, exclude_unset=True)

            await appointment.set(update_dict)

            await appointment.save()

            logger.info(f"Appointment updated: {appointment}")

            return appointment
        
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            raise

    async def delete_appointment(self, appointment_id: ObjectId) -> bool:
        """
        Delete an appointment by its ID.

        Args:
            appointment_id: MongoDB ObjectId of the appointment to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting appointment ID: {appointment_id}")

        try:
            appointment = await Appointment.get(appointment_id)

            if not appointment:
                logger.info("No appointment found with the given ID")
                return False

            await appointment.delete()

            logger.info("Appointment deleted successfully")

            return True
        
        except Exception as e:
            logger.error(f"Error deleting appointment: {e}")
            raise