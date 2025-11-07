import logging

from bson import ObjectId

from src.models.work_orders import WorkOrder, WorkOrderCreate, WorkOrderUpdate

logger = logging.getLogger(__name__)


class WorkOrderRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "workOrders"

    async def create_work_order(self, work_order_data: WorkOrderCreate) -> WorkOrder:
        """
        Create a new work order.

        Args:
            work_order_data: Dictionary with work order data
        Returns:
            Created work order data with _id, createdAt, and updatedAt fields

        Raises:
            Exception: If the workOrderNumber already exists (unique constraint)
            Exception: If an active work order for the vehicleId already exists (partial unique constraint)
        """
        logger.info(f"Creating work order for vehicle: {work_order_data.vehicle_id}")

        raise NotImplementedError("create_work_order method not yet implemented")

    async def get_by_id(self, work_order_id: ObjectId) -> WorkOrder | None:
        """
        Retrieve a work order by its ID.

        Args:
            work_order_id: MongoDB ObjectId of the work order

        Returns:
            WorkOrder document if found, None otherwise
        """
        logger.info(f"Retrieving work order by ID: {work_order_id}")

        raise NotImplementedError("get_by_id method not yet implemented")

    async def get_by_work_order_number(self, work_order_number: str) -> WorkOrder | None:
        """
        Retrieve a work order by its human-readable workOrderNumber.

        Args:
            work_order_number: The sequential work order number (e.g., "2025-0001")

        Returns:
            WorkOrder document if found, None otherwise
        """
        logger.info(f"Retrieving work order by number: {work_order_number}")

        raise NotImplementedError("get_by_work_order_number method not yet implemented")

    async def get_active_by_vehicle_id(self, vehicle_id: ObjectId) -> WorkOrder | None:
        """
        Retrieve the single *active* work order for a specific vehicle.
        This is the main method to enforce Business Rule RB02.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            WorkOrder document if an *active* one is found, None otherwise
        """
        logger.info(f"Checking for active work order for vehicle: {vehicle_id}")

        raise NotImplementedError("get_active_by_vehicle_id method not yet implemented")

    async def get_by_vehicle_id(self, vehicle_id: ObjectId) -> list[WorkOrder]:
        """
        Retrieve all work orders (active and inactive) for a specific vehicle.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            List of work order documents (empty list if none found)
        """
        logger.info(f"Retrieving all work orders for vehicle: {vehicle_id}")

        raise NotImplementedError("get_by_vehicle_id method not yet implemented")

    async def get_by_client_id(self, client_id: ObjectId) -> list[WorkOrder]:
        """
        Retrieve all work orders belonging to a specific client.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of work order documents (empty list if none found)
        """
        logger.info(f"Retrieving work orders for client: {client_id}")

        raise NotImplementedError("get_by_client_id method not yet implemented")

    async def update(self, work_order_id: ObjectId, update_data: WorkOrderUpdate) -> WorkOrder | None:
        """
        Update an existing work order.

        Args:
            work_order_id: MongoDB ObjectId of the work order to update
            update_data: WorkOrderUpdate Pydantic model with fields to update

        Returns:
            Updated work order document if found, None otherwise
        """
        logger.info(f"Updating work order: {work_order_id}")

        raise NotImplementedError("update method not yet implemented")

    async def delete(self, work_order_id: ObjectId) -> bool:
        """
        Delete a work order from the database.
        NOTE: This is a hard delete. Consider business logic implications.

        Args:
            work_order_id: MongoDB ObjectId of the work order to delete

        Returns:
            True if work order was deleted, False if not found
        """
        logger.info(f"Deleting work order: {work_order_id}")

        raise NotImplementedError("delete method not yet implemented")
