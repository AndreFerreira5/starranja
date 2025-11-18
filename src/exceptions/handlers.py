"""FastAPI exception handlers for work order operations."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.responses import Response

from src.exceptions.work_orders import (
    ActiveWorkOrderExistsError,
    WorkOrderDatabaseError,
    WorkOrderNotFoundError,
    WorkOrderNumberConflictError,
)


async def work_order_not_found_handler(request: Request, exc: WorkOrderNotFoundError) -> Response:
    """Handle WorkOrderNotFoundError with 404 response."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": str(exc),
            "identifier": exc.identifier,
        },
    )


async def active_work_order_exists_handler(request: Request, exc: ActiveWorkOrderExistsError) -> Response:
    """Handle ActiveWorkOrderExistsError with 409 Conflict response."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "active_work_order_exists",
            "message": str(exc),
            "vehicle_id": exc.vehicle_id,
            "rule": "RB02",
        },
    )


async def work_order_number_conflict_handler(request: Request, exc: WorkOrderNumberConflictError) -> Response:
    """Handle WorkOrderNumberConflictError with 503 Service Unavailable."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "work_order_number_conflict",
            "message": str(exc),
            "retry": True,
        },
    )


async def work_order_database_error_handler(request: Request, exc: WorkOrderDatabaseError) -> Response:
    """Handle WorkOrderDatabaseError with 500 Internal Server Error."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_error",
            "message": "An unexpected database error occurred",
            "operation": exc.operation,
        },
    )
