from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_invoices_repo
from src.models.invoices import Invoice, InvoiceCreate, InvoiceUpdate
from src.repository.invoices import InvoiceRepo

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("/", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    repo: Annotated[InvoiceRepo, Depends(get_invoices_repo)],
):
    """Create a new Invoice."""
    try:
        return await repo.create_invoice(invoice_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "invoice_creation_failed", "message": str(e)},
        )


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice_by_id(invoice_id: str, repo: Annotated[InvoiceRepo, Depends(get_invoices_repo)]):
    if not ObjectId.is_valid(invoice_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    invoice = await repo.get_invoice_by_id(ObjectId(invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/", response_model=list[Invoice])
async def list_invoices(
    repo: Annotated[InvoiceRepo, Depends(get_invoices_repo)],
    client_id: str | None = None,
    work_order_id: str | None = None,
):
    if client_id:
        if not ObjectId.is_valid(client_id):
            raise HTTPException(status_code=400, detail="Invalid client ID format")

        results = await repo.get_invoices_by_client_id(ObjectId(client_id))
        if not results:
            raise HTTPException(status_code=404, detail="No invoices found for this client")
        return results

    if work_order_id:
        if not ObjectId.is_valid(work_order_id):
            raise HTTPException(status_code=400, detail="Invalid work order ID format")

        results = await repo.get_invoices_by_work_order_id(ObjectId(work_order_id))
        if not results:
            raise HTTPException(status_code=404, detail="No invoices found for this work order")
        return results

    # No filters, returns all invoices
    return await repo.get_all_invoices()


@router.patch("/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    repo: Annotated[InvoiceRepo, Depends(get_invoices_repo)],
):
    if not ObjectId.is_valid(invoice_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    updated_invoice = await repo.update_invoice(ObjectId(invoice_id), invoice_data)
    if not updated_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return updated_invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: str,
    repo: Annotated[InvoiceRepo, Depends(get_invoices_repo)],
):
    if not ObjectId.is_valid(invoice_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    deleted = await repo.delete_invoice(ObjectId(invoice_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return None
