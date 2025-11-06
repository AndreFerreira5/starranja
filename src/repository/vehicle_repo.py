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
        logger.info(f"Creating vehicle with license plate {vehicle_data.get('licensePlate')}")

        raise NotImplementedError("create_vehicle method not yet implemented")

    async def get_by_id(self, vehicle_id: ObjectId) -> Vehicle | None:
        """
        Retrieve a vehicle by its ID.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            Vehicle document if found, None otherwise
        """
        logger.info(f"Retrieving vehicle by ID: {vehicle_id}")

        raise NotImplementedError("get_by_id method not yet implemented")

    async def get_by_license_plate(self, license_plate: str) -> Vehicle | None:
        """
        Retrieve a vehicle by its license plate.

        Args:
            license_plate: Vehicle license plate number

        Returns:
            Vehicle document if found, None otherwise
        """
        logger.info(f"Retrieving vehicle by license plate: {license_plate}")

        raise NotImplementedError("get_by_license_plate method not yet implemented")

    async def get_by_client_id(self, client_id: ObjectId) -> list[Vehicle]:
        """
        Retrieve all vehicles belonging to a specific client.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of vehicle documents (empty list if none found)
        """
        logger.info(f"Retrieving vehicles for client: {client_id}")

        raise NotImplementedError("get_by_client_id method not yet implemented")

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

        raise NotImplementedError("update method not yet implemented")

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

        raise NotImplementedError("delete method not yet implemented")
