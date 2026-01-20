import logging

from bson import ObjectId

from src.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate
from src.repository.decorators import handle_repo_errors

logger = logging.getLogger(__name__)


class VehicleRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "vehicles"

    @handle_repo_errors("create_vehicle")
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
        logger.debug(f"Creating vehicle with license plate {vehicle_data.license_plate}")

        vehicle = Vehicle(**vehicle_data.model_dump())

        await vehicle.insert()

        return vehicle

    @handle_repo_errors("get_vehicle_by_id")
    async def get_by_id(self, vehicle_id: ObjectId) -> Vehicle | None:
        """
        Retrieve a vehicle by its ID.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            Vehicle document if found, None otherwise
        """
        logger.debug(f"Retrieving vehicle by ID: {vehicle_id}")

        return await Vehicle.get(vehicle_id)

    @handle_repo_errors("get_vehicle_by_license_plate")
    async def get_by_license_plate(self, license_plate: str) -> Vehicle | None:
        """
        Retrieve a vehicle by its license plate.

        Args:
            license_plate: Vehicle license plate number

        Returns:
            Vehicle document if found, None otherwise
        """
        logger.debug(f"Retrieving vehicle by license plate: {license_plate}")

        return await Vehicle.find_one(Vehicle.license_plate == license_plate)

    @handle_repo_errors("get_vehicles_by_client_id")
    async def get_by_client_id(self, client_id: ObjectId) -> list[Vehicle]:
        """
        Retrieve all vehicles belonging to a specific client.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of vehicle documents (empty list if none found)
        """
        logger.debug(f"Retrieving vehicles for client: {client_id}")

        return await Vehicle.find(Vehicle.client_id == client_id).to_list()

    @handle_repo_errors("update_vehicle")
    async def update(self, vehicle_id: ObjectId, update_data: VehicleUpdate) -> Vehicle | None:
        """
        Update an existing vehicle.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle to update
            update_data: VehicleUpdate object with fields to update

        Returns:
            Updated vehicle document if found, None otherwise
        """
        logger.debug(f"Updating vehicle: {vehicle_id}")

        vehicle = await Vehicle.get(vehicle_id)
        if not vehicle:
            return None

        update_dict = update_data.model_dump(by_alias=True, exclude_unset=True)

        await vehicle.set(update_dict)
        # Trigger save hook to update `updatedAt` field
        await vehicle.save()

        return vehicle

    @handle_repo_errors("delete_vehicle")
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
        logger.debug(f"Deleting vehicle: {vehicle_id}")

        vehicle = await Vehicle.get(vehicle_id)

        if not vehicle:
            return False

        await vehicle.delete()
        return True
