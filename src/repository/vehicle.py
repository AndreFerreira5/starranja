import logging

from bson import ObjectId

from src.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate

logger = logging.getLogger(__name__)


class VehicleRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "vehicles"

    async def create_vehicle(self, vehicle_data: VehicleCreate) -> Vehicle:
        """
        Create a new vehicle.

        Args:
            vehicle_data: Dictionary with vehicle data
        Returns:
            Created vehicle data with _id, createdAt, and updatedAt fields

        Raises:
            Exception: If the license plate already exists (unique constraint violation)
        """
        logger.info(f"Creating vehicle with license plate {vehicle_data.license_plate}")

        try:
            vehicle = Vehicle(**vehicle_data.model_dump())
            await vehicle.insert()
            return vehicle
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            raise

    async def get_by_id(self, vehicle_id: ObjectId) -> Vehicle | None:
        """
        Retrieve a vehicle by its ID.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            Vehicle document if found, None otherwise
        """
        logger.info(f"Retrieving vehicle by ID: {vehicle_id}")

        try:
            return await Vehicle.get(vehicle_id)
        except Exception as e:
            logger.error(f"Error retrieving vehicle: {e}")
            raise

    async def get_by_license_plate(self, license_plate: str) -> Vehicle | None:
        """
        Retrieve a vehicle by its license plate.

        Args:
            license_plate: Vehicle license plate number

        Returns:
            Vehicle document if found, None otherwise
        """
        logger.info(f"Retrieving vehicle by license plate: {license_plate}")

        try:
            return await Vehicle.find_one(Vehicle.license_plate == license_plate)
        except Exception as e:
            logger.error(f"Error retrieving vehicle: {e}")
            raise

    async def get_by_client_id(self, client_id: ObjectId) -> list[Vehicle]:
        """
        Retrieve all vehicles belonging to a specific client.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of vehicle documents (empty list if none found)
        """
        logger.info(f"Retrieving vehicles for client: {client_id}")

        try:
            return await Vehicle.find(Vehicle.client_id == client_id).to_list()
        except Exception as e:
            logger.error(f"Error retrieving vehicles: {e}")
            raise

    async def update(self, vehicle_id: ObjectId, update_data: VehicleUpdate) -> Vehicle | None:
        """
        Update an existing vehicle.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle to update
            update_data: VehicleUpdate object with fields to update

        Returns:
            Updated vehicle document if found, None otherwise
        """
        logger.info(f"Updating vehicle: {vehicle_id}")

        try:
            vehicle = await Vehicle.get(vehicle_id)
            if not vehicle:
                return None

            update_dict = update_data.model_dump(by_alias=True, exclude_unset=True)

            if update_dict:
                await vehicle.set(update_dict)
                # Trigger save hook to update `updatedAt` field
                await vehicle.save()

            return vehicle

        except Exception as e:
            logger.error(f"Error updating vehicle: {e}")
            raise

    async def delete(self, vehicle_id: ObjectId) -> bool:
        """
        Delete a vehicle from the database.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle to delete

        Returns:
            True if vehicle was deleted, False if not found

        Note:
            Consider implementing soft delete or checking for active work orders
            before allowing deletion (business rule validation)
        """
        logger.info(f"Deleting vehicle: {vehicle_id}")

        try:
            vehicle = await Vehicle.get(vehicle_id)
            if not vehicle:
                return False

            await vehicle.delete()
            return True

        except Exception as e:
            logger.error(f"Error deleting vehicle: {e}")
            raise
