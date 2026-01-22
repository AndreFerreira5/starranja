from typing import Annotated
from uuid import UUID

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_current_user_id, get_supplier_order_repo
from src.exceptions.supplier_order import SupplierOrderDatabaseError
from src.models.supplier_order import (
    SupplierOrderCreate,
    SupplierOrderOut,
    SupplierOrderStatus,
    SupplierOrderUpdate,
)
from src.repository.supplier_order import SupplierOrderRepo

router = APIRouter()


@router.post("/", response_model=SupplierOrderOut, status_code=status.HTTP_201_CREATED)
async def create_supplier_order(
    order_data: SupplierOrderCreate,
    created_by_id: Annotated[UUID, Depends(get_current_user_id)],
    repo: Annotated[SupplierOrderRepo, Depends(get_supplier_order_repo)],
):
    """
    Create a new supplier order.

    Args:
        order_data: The data for the new order.
        created_by_id: ID of the currently authenticated user (auto-injected).
        repo: Repository instance.

    Returns:
        The created Supplier Order.
    """
    try:
        # Validate ObjectId manually if Pydantic doesn't catch it strictly enough
        if order_data.work_order_id and not ObjectId.is_valid(order_data.work_order_id):
            raise HTTPException(status_code=400, detail="Invalid work order ID format")

        return await repo.create_supplier_order(order_data, created_by_id)

    except SupplierOrderDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": str(e)},
        )


@router.get("/{order_id}", response_model=SupplierOrderOut)
async def get_supplier_order_by_id(
    order_id: str,
    repo: Annotated[SupplierOrderRepo, Depends(get_supplier_order_repo)],
):
    """Retrieve a supplier order by its ID."""
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    try:
        order = await repo.get_by_id(ObjectId(order_id))
        if not order:
            raise HTTPException(status_code=404, detail="Supplier order not found")
        return order
    except SupplierOrderDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": str(e)},
        )


@router.get("/", response_model=list[SupplierOrderOut])
async def list_supplier_orders(
    repo: Annotated[SupplierOrderRepo, Depends(get_supplier_order_repo)],
    work_order_id: str | None = None,
    status: SupplierOrderStatus | None = None,
    supplier_name: str | None = None,
):
    """
    List supplier orders with optional filters.

    - If `work_order_id` is provided -> Returns orders for that WO.
    - If `status` is provided -> Returns orders with that status.
    - If `supplier_name` is provided -> Returns orders for that supplier.
    - Otherwise -> Returns ALL orders (if get_all is implemented) or empty list.
    """
    try:
        if work_order_id:
            if not ObjectId.is_valid(work_order_id):
                raise HTTPException(status_code=400, detail="Invalid work order ID format")
            return await repo.get_by_work_order_id(ObjectId(work_order_id))

        if status:
            return await repo.get_by_status(status)

        if supplier_name:
            return await repo.get_by_supplier_name(supplier_name)

        return await repo.get_all()  # Uncomment if you implement it

    except SupplierOrderDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": str(e)},
        )


@router.patch("/{order_id}", response_model=SupplierOrderOut)
async def update_supplier_order(
    order_id: str,
    update_data: SupplierOrderUpdate,
    repo: Annotated[SupplierOrderRepo, Depends(get_supplier_order_repo)],
):
    """Update an existing supplier order."""
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    try:
        updated_order = await repo.update(ObjectId(order_id), update_data)
        if not updated_order:
            raise HTTPException(status_code=404, detail="Supplier order not found")
        return updated_order
    except SupplierOrderDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": str(e)},
        )


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier_order(
    order_id: str,
    repo: Annotated[SupplierOrderRepo, Depends(get_supplier_order_repo)],
):
    """Delete a supplier order."""
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    try:
        success = await repo.delete(ObjectId(order_id))
        if not success:
            raise HTTPException(status_code=404, detail="Supplier order not found")
        return None
    except SupplierOrderDatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_error", "message": str(e)},
        )
