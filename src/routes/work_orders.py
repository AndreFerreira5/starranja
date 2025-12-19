from typing import Annotated
from uuid import UUID

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_current_user_id, get_work_order_repo
from src.exceptions.work_orders import ActiveWorkOrderExistsError, WorkOrderNotFoundError
from src.models.work_orders import WorkOrder, WorkOrderCreate, WorkOrderStatus, WorkOrderUpdate
from src.repository.work_orders import WorkOrderRepo

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.post("/", response_model=WorkOrder, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    order_data: WorkOrderCreate,
    repo: Annotated[WorkOrderRepo, Depends(get_work_order_repo)],
    created_by_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Create a new Work Order."""
    try:
        # created_by_id is injected automatically by our dependency
        return await repo.create_work_order(order_data, created_by_id)
    except ActiveWorkOrderExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "active_work_order_exists", "message": str(e), "vehicle_id": e.vehicle_id},
        )


@router.get("/{work_order_id}", response_model=WorkOrder)
async def get_work_order(work_order_id: str, repo: Annotated[WorkOrderRepo, Depends(get_work_order_repo)]):
    if not ObjectId.is_valid(work_order_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    work_order = await repo.get_by_id(ObjectId(work_order_id))
    if not work_order:
        raise WorkOrderNotFoundError(work_order_id)
    return work_order


@router.get("/", response_model=list[WorkOrder] | WorkOrder)
async def list_work_orders(
    repo: Annotated[WorkOrderRepo, Depends(get_work_order_repo)],
    work_order_number: str | None = None,
    vehicle_id: str | None = None,
    client_id: str | None = None,
    status: WorkOrderStatus | None = None,
    active_only: bool = False,
):
    # Search by Unique Number
    if work_order_number:
        wo = await repo.get_by_work_order_number(work_order_number)
        if not wo:
            raise WorkOrderNotFoundError(work_order_number)
        return wo

    # Filter by Vehicle
    if vehicle_id:
        if not ObjectId.is_valid(vehicle_id):
            raise HTTPException(status_code=400, detail="Invalid Vehicle ID")
        if active_only:
            wo = await repo.get_active_by_vehicle_id(ObjectId(vehicle_id))
            return [wo] if wo else []
        return await repo.get_by_vehicle_id(ObjectId(vehicle_id))

    # Filter by Client
    if client_id:
        if not ObjectId.is_valid(client_id):
            raise HTTPException(status_code=400, detail="Invalid Client ID")
        return await repo.get_by_client_id(ObjectId(client_id))

    # Filter by Status
    if status:
        return await repo.get_by_status(status)

    return []


@router.patch("/{work_order_id}", response_model=WorkOrder)
async def update_work_order(
    work_order_id: str,
    update_data: WorkOrderUpdate,
    repo: Annotated[WorkOrderRepo, Depends(get_work_order_repo)],
):
    if not ObjectId.is_valid(work_order_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    updated_wo = await repo.update(ObjectId(work_order_id), update_data)
    if not updated_wo:
        raise WorkOrderNotFoundError(work_order_id)
    return updated_wo


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_order(work_order_id: str, repo: Annotated[WorkOrderRepo, Depends(get_work_order_repo)]):
    if not ObjectId.is_valid(work_order_id):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    success = await repo.delete(ObjectId(work_order_id))
    if not success:
        raise WorkOrderNotFoundError(work_order_id)
    return None
