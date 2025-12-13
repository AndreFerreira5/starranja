import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.db.connection import auth_db_connect, auth_db_disconnect
from src.exceptions.clients import (
    ClientDatabaseError,
    ClientNotFoundError,
    DuplicateClientEmailError,
    DuplicateClientNIFError,
    InvalidClientDataError,
)
from src.exceptions.handlers import (
    active_work_order_exists_handler,
    client_database_error_handler,
    client_not_found_handler,
    duplicate_client_email_handler,
    duplicate_client_nif_handler,
    invalid_client_data_handler,
    supplier_order_database_error_handler,
    supplier_order_not_found_handler,
    work_order_database_error_handler,
    work_order_not_found_handler,
    work_order_number_conflict_handler,
)
from src.exceptions.supplier_order import (
    SupplierOrderDatabaseError,
    SupplierOrderNotFoundError,
)
from src.exceptions.work_orders import (
    ActiveWorkOrderExistsError,
    WorkOrderDatabaseError,
    WorkOrderNotFoundError,
    WorkOrderNumberConflictError,
)
from src.logging_config import configure_logging
from src.routes import auth, users

# configure logging globally
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await auth_db_connect()
    yield
    await auth_db_disconnect()


app = FastAPI(
    lifespan=lifespan,
    exception_handlers={
        WorkOrderNotFoundError: work_order_not_found_handler,
        ActiveWorkOrderExistsError: active_work_order_exists_handler,
        WorkOrderNumberConflictError: work_order_number_conflict_handler,
        WorkOrderDatabaseError: work_order_database_error_handler,
        ClientNotFoundError: client_not_found_handler,
        DuplicateClientNIFError: duplicate_client_nif_handler,
        DuplicateClientEmailError: duplicate_client_email_handler,
        InvalidClientDataError: invalid_client_data_handler,
        ClientDatabaseError: client_database_error_handler,
        SupplierOrderDatabaseError: supplier_order_database_error_handler,
        SupplierOrderNotFoundError: supplier_order_not_found_handler,
    },
)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])


@app.get("/ping")
async def ping():
    return {"message": "pong"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
