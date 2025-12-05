import logging 

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument

from src.models.invoices import Invoice, InvoiceCreate, InvoiceUpdate
from src.models.work_orders import WorkOrder
from src.models.client import Client

from src.repository.decorators import handle_repo_errors

logger = logging.getLogger(__name__)

class InvoiceRepo:
    def __init__(self, db):
        self.db = db
        self.collection = "invoices"
        self.counters_collection = db["counters"]

    async def _get_next_invoice_number(self) -> str:
        """
        Atomically increments and retrieves the next invoice number.
        This uses a separate 'counters' collection to prevent race conditions.
        """
        try:
            counter_doc = await self.counters_collection.find_one_and_update(
                {"_id": "invoiceNumber"},
                {"$inc": {"seq": 1}},
                upsert=True,  # Creates the counter if it doesn't exist
                return_document=ReturnDocument.AFTER,
            )
            seq = counter_doc["seq"]

            return f"{seq:04d}"
        except Exception as e:
            logger.error(f"Failed to generate invoice number: {e}", exc_info=True)

    @handle_repo_errors("create_invoice")
    async def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """
        Create a new invoice.

        Args:
            invoice_data: Dictionary with invoice data
        Returns:
            Created invoice data with _id, createdAt, and updatedAt fields

        Raises:
            Exception: If there is any issue during creation
        """
        logger.info(f"Creating invoice for work order ID {invoice_data.work_order_id}")

        raise NotImplementedError("Method not implemented yet")

    @handle_repo_errors("get_invoice_by_id")
    async def get_invoice_by_id(self, invoice_id: ObjectId) -> Invoice | None:
        """
        Retrieve an invoice by its ID.

        Args:
            invoice_id: MongoDB ObjectId of the invoice

        Returns:
            Invoice document if found, None otherwise
        """
        logger.info(f"Retrieving invoice with ID {invoice_id}")

        raise NotImplementedError("Method not implemented yet")
    
    @handle_repo_errors("get_invoices_by_client_id")
    async def get_invoices_by_client_id(self, client_id: ObjectId) -> list[Invoice]:
        """
        Retrieve all invoices for a given client ID.

        Args:
            client_id: MongoDB ObjectId of the client
        Returns:
            List of Invoice documents for the client
        """
        logger.info(f"Retrieving invoices for client ID {client_id}")

        raise NotImplementedError("Method not implemented yet")
    
    @handle_repo_errors("get_invoices_by_work_order_id")
    async def get_invoices_by_work_order_id(self, work_order_id: ObjectId) -> list[Invoice]: 
        """
        Retrieve all invoices for a given work order ID.

        Args:
            work_order_id: MongoDB ObjectId of the work order
        Returns:
            List of Invoice documents for the work order
        """
        logger.info(f"Retrieving invoices for work order ID {work_order_id}")

        raise NotImplementedError("Method not implemented yet")
    
    @handle_repo_errors("update_invoice")
    async def update_invoice(self, invoice_id: ObjectId, invoice_data: InvoiceUpdate) -> Invoice | None:
        """
        Update an existing invoice.

        Args:
            invoice_id: MongoDB ObjectId of the invoice to update
            invoice_data: Dictionary with updated invoice data

        Returns:
            Updated Invoice document if found, None otherwise
        """
        logger.info(f"Updating invoice with ID {invoice_id}")

        raise NotImplementedError("Method not implemented yet")

    @handle_repo_errors("delete_invoice")
    async def delete_invoice(self, invoice_id: ObjectId) -> bool:
        """
        Delete an invoice by its ID.

        Args:
            invoice_id: MongoDB ObjectId of the invoice to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting invoice with ID {invoice_id}")

        raise NotImplementedError("Method not implemented yet")