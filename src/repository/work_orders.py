import logging
from uuid import UUID

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.exceptions.work_orders import (
    ActiveWorkOrderExistsError,
    WorkOrderDatabaseError,
    WorkOrderNumberConflictError,
)
from src.models.work_orders import Quote, WorkOrder, WorkOrderCreate, WorkOrderUpdate
from src.repository.decorators import handle_repo_errors

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
        try:
            counter_doc = await self.counters_collection.find_one_and_update(
                {"_id": "workOrderNumber"},
                {"$inc": {"seq": 1}},
                upsert=True,  # Creates the counter if it doesn't exist
                return_document=ReturnDocument.AFTER,
            )
            seq = counter_doc["seq"]

            return f"{seq:04d}"
        except Exception as e:
            logger.error(f"Failed to generate work order number: {e}", exc_info=True)
            raise WorkOrderDatabaseError("work order number generation", str(e)) from e

    @handle_repo_errors("create_work_order")
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
            await new_work_order.insert()

            logger.info(f"Successfully created work order {new_work_order.work_order_number}")
            return new_work_order

        except DuplicateKeyError as e:
            logger.warning(
                f"Duplicate key error creating work order: {e.details}",
                extra={"vehicle_id": str(work_order_data.vehicle_id)},
            )

            if e.details:
                key_pattern = e.details.get("keyPattern", {})

                errmsg = e.details.get("errmsg", "")

                # Check both keyPattern and errmsg for vehicleId
                if "vehicleId" in key_pattern or "vehicleId" in errmsg:
                    raise ActiveWorkOrderExistsError(str(work_order_data.vehicle_id)) from e

                # Check both keyPattern and errmsg for workOrderNumber
                if "workOrderNumber" in key_pattern or "workOrderNumber" in errmsg:
                    raise WorkOrderNumberConflictError() from e

            # Generic database error for unexpected constraint violations
            raise WorkOrderDatabaseError("create_work_order", f"Unique constraint violated: {e.details}") from e

    @handle_repo_errors("get_by_id")
    async def get_by_id(self, work_order_id: ObjectId) -> WorkOrder | None:
        """
        Retrieve a work order by its ID.

        Args:
            work_order_id: MongoDB ObjectId of the work order

        Returns:
            WorkOrder document if found, None otherwise
        """
        logger.debug(f"Retrieving work order by ID: {work_order_id}")

        # Use Beanie's .get() method for a direct lookup by _id
        work_order = await WorkOrder.get(work_order_id)

        if not work_order:
            logger.debug(f"Work order with ID {work_order_id} not found.")

        return work_order

    @handle_repo_errors("get_by_work_order_number")
    async def get_by_work_order_number(self, work_order_number: str) -> WorkOrder | None:
        """
        Retrieve a work order by its human-readable workOrderNumber.

        Args:
            work_order_number: The sequential work order number (e.g., "2025-0001")

        Returns:
            WorkOrder document if found, None otherwise
        """
        logger.debug(f"Retrieving work order by number: {work_order_number}")

        # find_one to query by the work_order_number field
        work_order = await WorkOrder.find_one(WorkOrder.work_order_number == work_order_number)

        if not work_order:
            logger.debug(f"Work order with number {work_order_number} not found.")

        return work_order

    @handle_repo_errors("get_active_by_vehicle_id")
    async def get_active_by_vehicle_id(self, vehicle_id: ObjectId) -> WorkOrder | None:
        """
        Retrieve the single *active* work order for a specific vehicle.
        This is the main method to enforce Business Rule RB02.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            WorkOrder document if an *active* one is found, None otherwise
        """
        logger.debug(f"Checking for active work order for vehicle: {vehicle_id}")

        # Find the document that matches BOTH the vehicleId AND isActive: true
        work_order = await WorkOrder.find_one(
            WorkOrder.vehicle_id == vehicle_id,
            WorkOrder.is_active == True,  # noqa: E712
        )

        if not work_order:
            logger.info(f"No active work order found for vehicle: {vehicle_id}")

        return work_order

    @handle_repo_errors("get_by_vehicle_id")
    async def get_by_vehicle_id(self, vehicle_id: ObjectId) -> list[WorkOrder]:
        """
        Retrieve all work orders (active and inactive) for a specific vehicle.

        Args:
            vehicle_id: MongoDB ObjectId of the vehicle

        Returns:
            List of work order documents (empty list if none found)
        """
        logger.debug(f"Retrieving all work orders for vehicle: {vehicle_id}")

        # .find() to get a query builder for all matching documents,
        # .to_list() to execute the query and return a list.
        work_orders = await WorkOrder.find(WorkOrder.vehicle_id == vehicle_id).to_list()

        logger.debug(f"Found {len(work_orders)} work orders for vehicle {vehicle_id}")
        return work_orders

    @handle_repo_errors("get_by_client_id")
    async def get_by_client_id(self, client_id: ObjectId) -> list[WorkOrder]:
        """
        Retrieve all work orders belonging to a specific client.

        Args:
            client_id: MongoDB ObjectId of the client

        Returns:
            List of work order documents (empty list if none found)
        """
        logger.info(f"Retrieving work orders for client: {client_id}")

        # .find() to get a query builder for all matching documents,
        # .to_list() to execute the query.
        work_orders = await WorkOrder.find(WorkOrder.client_id == client_id).to_list()

        logger.debug(f"Found {len(work_orders)} work orders for client {client_id}")
        return work_orders

    @handle_repo_errors("update")
    async def update(self, work_order_id: ObjectId, update_data: WorkOrderUpdate) -> WorkOrder | None:
        """
        Update an existing work order.

        Args:
            work_order_id: MongoDB ObjectId of the work order to update
            update_data: WorkOrderUpdate Pydantic model with fields to update

        Returns:
            Updated work order document if found, None otherwise
        """
        logger.debug(f"Updating work order: {work_order_id}")

        # 1. Find the document by its ID
        work_order = await WorkOrder.get(work_order_id)

        if not work_order:
            logger.warning(f"Work order {work_order_id} not found for update.")
            return None

        # 2. Convert the Pydantic update model to a dictionary.
        #    exclude_unset=True is crucial: it only includes fields that
        #    were explicitly set in the update_data object.
        #    by_alias=True ensures we use DB field names (e.g., "isActive")
        update_dict = update_data.model_dump(by_alias=True, exclude_unset=True)

        # 3. Apply the changes to the document in memory
        await work_order.set(update_dict)

        # 4. Save the document to the database.
        #    This will also trigger the save() hook, updating `updated_at`.
        await work_order.save()

        logger.info(f"Successfully updated work order: {work_order_id}")
        return work_order

    @handle_repo_errors("delete")
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

        # 1. Find the document by its ID using Beanie's .get()
        work_order = await WorkOrder.get(work_order_id)

        # 2. If the document doesn't exist, return False
        if not work_order:
            logger.warning(f"Work order {work_order_id} not found for deletion.")
            return False

        # 3. If the document exists, delete it
        await work_order.delete()

        logger.info(f"Successfully deleted work order: {work_order_id}")
        return True
