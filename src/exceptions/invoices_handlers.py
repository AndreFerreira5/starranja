from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.responses import Response

from src.exceptions.invoices import (
    ClientAddressMissingError,
    InvoiceDatabaseError,
    InvoiceNotFoundError,
    InvoiceNumberConflictError,
)


async def invoice_not_found_handler(request: Request, exc: InvoiceNotFoundError) -> Response:
    """Handle InvoiceNotFoundError with 404 response."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": str(exc),
            "identifier": exc.identifier,
        },
    )


async def invoice_number_conflict_handler(request: Request, exc: InvoiceNumberConflictError) -> Response:
    """Handle InvoiceNumberConflictError with 503 Service Unavailable."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "invoice_number_conflict",
            "message": str(exc),
            "retry": True,
        },
    )


async def invoice_database_error_handler(request: Request, exc: InvoiceDatabaseError) -> Response:
    """Handle InvoiceDatabaseError with 500 Internal Server Error."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_error",
            "message": "An unexpected database error occurred",
            "operation": exc.operation,
        },
    )


async def client_address_missing_handler(request: Request, exc: ClientAddressMissingError) -> Response:
    """Handle ClientAddressMissingError with 400 Bad Request."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "client_address_missing",
            "message": str(exc),
            "client_id": exc.client_id,
        },
    )
