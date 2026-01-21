import logging
from contextlib import asynccontextmanager

import uvicorn
from beanie import init_beanie
from fastapi import FastAPI

from src.db.connection import auth_db_connect, auth_db_disconnect, mongo_db, mongo_db_connect, mongo_db_disconnect
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

from src.models.appointments import Appointment
from src.models.client import Client
from src.models.invoices import Invoice
from src.models.supplier_order import SupplierOrder
from src.models.vehicle import Vehicle
from src.models.work_orders import WorkOrder
from src.routes import auth, clients, users, work_orders, invoices

# configure logging globally
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await auth_db_connect()
    await mongo_db_connect()

    await init_beanie(
        database=mongo_db.database,
        document_models=[
            Invoice,
            Client,
            Vehicle,
            WorkOrder,
            SupplierOrder,
            Appointment,
        ],
        allow_index_dropping=True,
    )

    yield

    await auth_db_disconnect()
    await mongo_db_disconnect()


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
app.include_router(work_orders.router, prefix="/work-orders", tags=["Work Orders"])
app.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
app.include_router(clients.router)


@app.get("/ping")
async def ping():
    return {"message": "pong"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
