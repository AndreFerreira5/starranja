import logging
from datetime import UTC, datetime  # Ensure UTC is imported

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.exceptions.invoices import (
    ClientAddressMissingError,
    InvoiceDatabaseError,
    InvoiceNumberConflictError,
)
from src.models.client import Client
from src.models.invoices import (
    Invoice,
    InvoiceAddress,
    InvoiceClientDetails,
    InvoiceCreate,
    InvoiceStatus,
    InvoiceUpdate,
    InvoiceVehicleDetails,
)
from src.models.vehicle import Vehicle
from src.models.work_orders import WorkOrder
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
        """
        try:
            counter_doc = await self.counters_collection.find_one_and_update(
                {"_id": "invoiceNumber"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            seq = counter_doc["seq"]
            return f"FT {datetime.now(UTC).year}/{seq}"

        except Exception as e:
            logger.error(f"Error generating invoice number: {e}")
            raise InvoiceDatabaseError("invoice number generation", str(e))

    @handle_repo_errors("create_invoice")
    async def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        logger.info(f"Creating invoice for work order ID {invoice_data.work_order_id}")

        try:
            # 1. Fetch the Work Order
            work_order = await WorkOrder.get(invoice_data.work_order_id)

            # handler for missing work order needs to be added
            if not work_order:
                raise HTTPException(status_code=404, detail=f"Work Order {invoice_data.work_order_id} not found")

            # 2. Fetch Related Entities (Client and Vehicle)
            client = await Client.get(work_order.client_id)

            # handler for missing client needs to be added
            if not client:
                raise HTTPException(status_code=404, detail=f"Client {work_order.client_id} not found")

            vehicle = await Vehicle.get(work_order.vehicle_id)

            # handler for missing vehicle needs to be added
            if not vehicle:
                # Handle edge case where vehicle might have been deleted, or raise 404
                raise HTTPException(status_code=404, detail=f"Vehicle {work_order.vehicle_id} not found")

            # 3. Prepare Snapshots
            client_address = getattr(client, "address", None)

            # Fallback if address is missing but required by InvoiceAddress model
            if not client_address:
                raise ClientAddressMissingError(str(client.id))
            
            # Assuming client.address matches InvoiceAddress structure or mapping is needed
            addr_snapshot = InvoiceAddress(
                street=client_address.street, city=client_address.city, zipCode=client_address.zip_code
            )

            client_snapshot = InvoiceClientDetails(name=client.name, nif=client.nif, address=addr_snapshot)

            vehicle_snapshot = InvoiceVehicleDetails(
                licensePlate=vehicle.license_plate, brand=vehicle.brand, model=vehicle.model
            )
            invoice_items = work_order.items

            # 4. Generate Invoice Number
            invoice_number = await self._get_next_invoice_number()

            invoice = Invoice(
                invoice_number=invoice_number,
                invoice_date=datetime.now(UTC),
                status=InvoiceStatus.EMITTED,
                # References
                work_order_id=work_order.id,
                client_id=client.id,
                emitted_by_id=work_order.created_by_id,  # Or user from context
                # Snapshots
                client_details=client_snapshot,
                vehicle_details=vehicle_snapshot,
                items=invoice_items,  # MAKE SURE THIS IS POPULATED CORRECTLY (see note below)
                # --- FIX IS HERE ---
                # Retrieve totals from the fetched work_order object, NOT invoice_data
                total_without_iva=work_order.final_total_price_without_iva,
                total_iva=work_order.final_total_iva,
                total_with_iva=work_order.final_total_price_with_iva,
            )

            await invoice.insert()
            logger.info(f"Invoice created with ID: {invoice.id}")
            return invoice

        except DuplicateKeyError as e:
            logger.error(f"Invoice number conflict: {e}")

            if e.details and e.details.get("keyPattern", {}).get("invoice_number"):
                raise InvoiceNumberConflictError() from e

            raise InvoiceDatabaseError("create invoice", str(e)) from e

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

        try:
            invoice = await Invoice.get(invoice_id)

            if invoice:
                logger.info(f"Invoice found: {invoice}")

            else:
                logger.info("No invoice found with the given ID")

            return invoice

        except Exception as e:
            logger.error(f"Error retrieving invoice: {e}")
            raise InvoiceDatabaseError("get invoice by id", str(e)) from e

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

        try:
            invoices = await Invoice.find(Invoice.client_id == client_id).to_list()

            logger.info(f"Found {len(invoices)} invoices for client ID {client_id}")

            return invoices

        except Exception as e:
            logger.error(f"Error retrieving invoices: {e}")
            raise InvoiceDatabaseError("get_invoices_by_client_id", str(e)) from e

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

        try:
            invoices = await Invoice.find(Invoice.work_order_id == work_order_id).to_list()

            logger.info(f"Found {len(invoices)} invoices for work order ID {work_order_id}")

            return invoices

        except Exception as e:
            logger.error(f"Error retrieving invoices: {e}")
            raise InvoiceDatabaseError("get_invoices_by_work_order_id", str(e)) from e

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

        try:
            invoice = await Invoice.get(invoice_id)

            if not invoice:
                logger.info("No invoice found with the given ID")
                return None

            updated_dict = invoice_data.model_dump(by_alias=True, exclude_unset=True)

            await invoice.set(updated_dict)

            await invoice.save()

            logger.info(f"Invoice updated: {invoice}")

            return invoice

        except Exception as e:
            logger.error(f"Error updating invoice: {e}")
            raise InvoiceDatabaseError("update invoice", str(e)) from e

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

        try:
            invoice = await Invoice.get(invoice_id)

            if not invoice:
                logger.info("No invoice found with the given ID")
                return False

            await invoice.delete()

            logger.info("Invoice deleted successfully")

            return True

        except Exception as e:
            logger.error(f"Error deleting invoice: {e}")
            raise InvoiceDatabaseError("delete invoice", str(e)) from e
