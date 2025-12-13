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
        raise NotImplementedError("create_supplier_order not implemented yet")

    async def get_by_id(self, order_id: ObjectId) -> SupplierOrder | None:
        """
        Retrieve a supplier order by its ID.

        Args:
            order_id: MongoDB ObjectId

        Returns:
            SupplierOrder document or None
        """
        logger.debug(f"Retrieving supplier order by ID: {order_id}")
        raise NotImplementedError("get_by_id not implemented yet")

    async def get_by_work_order_id(self, work_order_id: ObjectId) -> list[SupplierOrder]:
        """
        Retrieve all supplier orders linked to a specific work order.

        Args:
            work_order_id: MongoDB ObjectId of the work order

        Returns:
            List of SupplierOrder documents
        """
        logger.debug(f"Retrieving supplier orders for work order: {work_order_id}")
        raise NotImplementedError("get_by_work_order_id not implemented yet")

    async def get_by_status(self, status: SupplierOrderStatus) -> list[SupplierOrder]:
        """
        Retrieve all supplier orders with a specific status.

        Args:
            status: Enum value (Pending, Ordered, etc.)

        Returns:
            List of SupplierOrder documents
        """
        logger.debug(f"Retrieving supplier orders with status: {status}")
        raise NotImplementedError("get_by_status not implemented yet")

    async def get_by_supplier_name(self, supplier_name: str) -> list[SupplierOrder]:
        """
        Retrieve all supplier orders for a specific vendor.

        Args:
            supplier_name: Name of the supplier

        Returns:
            List of SupplierOrder documents
        """
        logger.debug(f"Retrieving supplier orders for supplier: {supplier_name}")
        raise NotImplementedError("get_by_supplier_name not implemented yet")

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
        raise NotImplementedError("update not implemented yet")

    async def delete(self, order_id: ObjectId) -> bool:
        """
        Delete a supplier order.

        Args:
            order_id: MongoDB ObjectId

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting supplier order: {order_id}")
        raise NotImplementedError("delete not implemented yet")
