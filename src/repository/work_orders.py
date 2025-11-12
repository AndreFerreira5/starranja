import logging
from uuid import UUID

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.models.work_orders import Quote, WorkOrder, WorkOrderCreate, WorkOrderUpdate

logger = logging.getLogger(__name__)


class WorkOrderRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "workOrders"
        self.counters_collection = db["counters"]

    async def _get_next_work_order_number(self) -> str:
        """
        Atomically increments and retrieves the next work order number.
        This uses a separate 'counters' collection to prevent race conditions.
        """
        counter_doc = await self.counters_collection.find_one_and_update(
            {"_id": "workOrderNumber"},
            {"$inc": {"seq": 1}},
            upsert=True,  # Creates the counter if it doesn't exist
            return_document=ReturnDocument.AFTER,
        )
        seq = counter_doc["seq"]

        return f"{seq:04d}"

    async def create_work_order(self, work_order_data: WorkOrderCreate, created_by_id: UUID) -> WorkOrder:
        """
        Create a new work order.

        Args:
            created_by_id: ID of the user who created the work order.
            work_order_data: Dictionary with work order data
        Returns:
            Created work order data with _id, createdAt, and updatedAt fields

        Raises:
            Exception: If the workOrderNumber already exists (unique constraint)
            Exception: If an active work order for the vehicleId already exists (partial unique constraint)
        """

        try:
            # 1. Generate the unique, sequential number
            wo_number = await self._get_next_work_order_number()

            # 2. Create the embedded Quote object from the create data
            quote_data = Quote(clientObservations=work_order_data.client_observations, diagnostic=None)

            # 3. Create the new WorkOrder document
            # The model will set defaults for:
            # - status (AWAITING_DIAGNOSTIC)
            # - isActive (True)
            # - createdAt/updatedAt
            new_work_order = WorkOrder(
                work_order_number=wo_number,
                created_by_id=created_by_id,
                client_id=work_order_data.client_id,
                vehicle_id=work_order_data.vehicle_id,
                entry_date=work_order_data.entry_date,
                quote=quote_data,
            )

            # 4. Save to the database
            # This will trigger the unique indexes
            await new_work_order.save()

            logger.info(f"Successfully created work order {new_work_order.work_order_number}")
            return new_work_order

        except DuplicateKeyError as e:
            logger.warning(f"Failed to create work order due to duplicate key: {e.details}")

            if e.details:
                key_pattern = e.details.get("keyPattern", {})
                if "vehicleId_1" in key_pattern:
                    # This is the partial index for RB02
                    raise Exception("This vehicle already has an active work order. (RB02)")
                if "workOrderNumber_1" in key_pattern:
                    # This is the (now very rare) race condition
                    raise Exception("Work order number concurrency error. Please try again.")
                # Generic fallback
            raise Exception(f"Database unique constraint violated: {e.details}")

        except Exception as e:
            logger.error(f"An unexpected error occurred while creating work order: {e}", exc_info=True)
            raise e

    async def get_by_id(self, work_order_id: ObjectId) -> WorkOrder | None:
        """
        Retrieve a work order by its ID.

        Args:
            work_order_id: MongoDB ObjectId of the work order

        Returns:
            WorkOrder document if found, None otherwise
        """
        logger.info(f"Retrieving work order by ID: {work_order_id}")

        try:
            # Use Beanie's .get() method for a direct lookup by _id
            work_order = await WorkOrder.get(work_order_id)

            if not work_order:
                logger.info(f"Work order with ID {work_order_id} not found.")
                return None

            return work_order

        except Exception as e:
            # Catch potential database connection errors or other issues
            logger.error(
                f"An unexpected error occurred while retrieving work order {work_order_id}: {e}", exc_info=True
            )
            raise e  # Re-raise the exception to be handled by the service/API layer

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
