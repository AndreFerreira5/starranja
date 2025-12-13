import logging
from uuid import UUID

from bson import ObjectId

from src.models.supplier_order import (
    SupplierOrder,
    SupplierOrderCreate,
    SupplierOrderStatus,
    SupplierOrderUpdate,
)

logger = logging.getLogger(__name__)


class SupplierOrderRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "supplierOrders"

    async def create_supplier_order(self, order_data: SupplierOrderCreate, created_by_id: UUID) -> SupplierOrder:
        """
        Create a new supplier order.

        Args:
            order_data: Schema with supplier order data
            created_by_id: UUID of the user creating the order

        Returns:
            The created SupplierOrder document
        """
        logger.info(f"Creating supplier order for: {order_data.supplier_name}")

        # Create the document instance from the Pydantic schema
        # We manually inject created_by_id since it's not in the 'Create' schema
        supplier_order = SupplierOrder(
            **order_data.model_dump(),
            created_by_id=created_by_id,
            # status defaults to PENDING via the model definition
            # order_date defaults to NOW via the model definition
        )

        # Insert into the database
        await supplier_order.insert()

        logger.info(f"Successfully created supplier order: {supplier_order.id}")
        return supplier_order

    async def get_by_id(self, order_id: ObjectId) -> SupplierOrder | None:
        """
        Retrieve a supplier order by its ID.

        Args:
            order_id: MongoDB ObjectId

        Returns:
            SupplierOrder document or None
        """
        logger.debug(f"Retrieving supplier order by ID: {order_id}")
        # Use Beanie's .get() for direct primary key lookup
        order = await SupplierOrder.get(order_id)

        if not order:
            logger.debug(f"Supplier order {order_id} not found")

        return order

    async def get_by_work_order_id(self, work_order_id: ObjectId) -> list[SupplierOrder]:
        """
        Retrieve all supplier orders linked to a specific work order.

        Args:
            work_order_id: MongoDB ObjectId of the work order

        Returns:
            List of SupplierOrder documents
        """
        logger.debug(f"Retrieving supplier orders for work order: {work_order_id}")
        # Use .find() with a filter expression
        orders = await SupplierOrder.find(SupplierOrder.work_order_id == work_order_id).to_list()

        logger.debug(f"Found {len(orders)} orders linked to WO {work_order_id}")
        return orders

    async def get_by_status(self, status: SupplierOrderStatus) -> list[SupplierOrder]:
        """
        Retrieve all supplier orders with a specific status.

        Args:
            status: Enum value (Pending, Ordered, etc.)

        Returns:
            List of SupplierOrder documents
        """
        logger.debug(f"Retrieving supplier orders with status: {status}")

        orders = await SupplierOrder.find(SupplierOrder.status == status).to_list()

        logger.debug(f"Found {len(orders)} orders with status {status}")
        return orders

    async def get_by_supplier_name(self, supplier_name: str) -> list[SupplierOrder]:
        """
        Retrieve all supplier orders for a specific vendor.

        Args:
            supplier_name: Name of the supplier

        Returns:
            List of SupplierOrder documents
        """
        logger.debug(f"Retrieving supplier orders for supplier: {supplier_name}")

        # Simple exact match on the string field
        orders = await SupplierOrder.find(SupplierOrder.supplier_name == supplier_name).to_list()

        return orders

    async def update(self, order_id: ObjectId, update_data: SupplierOrderUpdate) -> SupplierOrder | None:
        """
        Update an existing supplier order.

        Args:
            order_id: MongoDB ObjectId
            update_data: Schema with fields to update

        Returns:
            Updated SupplierOrder document or None
        """
        logger.debug(f"Updating supplier order: {order_id}")

        # Fetch the existing document
        order = await SupplierOrder.get(order_id)

        if not order:
            logger.warning(f"Supplier order {order_id} not found for update")
            return None

        # Convert update schema to dict, removing unset fields
        # by_alias=True ensures fields like 'supplierName' map correctly to DB
        update_dict = update_data.model_dump(by_alias=True, exclude_unset=True)

        # Apply updates to the document in memory
        if update_dict:
            await order.set(update_dict)

            # Save to persist changes (and update updatedAt timestamp)
            await order.save()

        logger.info(f"Successfully updated supplier order: {order_id}")
        return order

    async def delete(self, order_id: ObjectId) -> bool:
        """
        Delete a supplier order.

        Args:
            order_id: MongoDB ObjectId

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting supplier order: {order_id}")

        # Fetch the document
        order = await SupplierOrder.get(order_id)

        if not order:
            logger.warning(f"Supplier order {order_id} not found for deletion")
            return False

        # Delete the document
        await order.delete()

        logger.info(f"Successfully deleted supplier order: {order_id}")
        return True
