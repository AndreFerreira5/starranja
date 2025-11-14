import logging

import uvicorn
from fastapi import FastAPI

from src.api.exception_handlers import (
    active_work_order_exists_handler,
    work_order_database_error_handler,
    work_order_not_found_handler,
    work_order_number_conflict_handler,
)
from src.exceptions.work_orders import (
    ActiveWorkOrderExistsError,
    WorkOrderDatabaseError,
    WorkOrderNotFoundError,
    WorkOrderNumberConflictError,
)
from src.logging_config import configure_logging

# configure logging globally
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    # Register exception handlers
    exception_handlers={
        WorkOrderNotFoundError: work_order_not_found_handler,
        ActiveWorkOrderExistsError: active_work_order_exists_handler,
        WorkOrderNumberConflictError: work_order_number_conflict_handler,
        WorkOrderDatabaseError: work_order_database_error_handler,
    }
)


@app.get("/ping")
async def ping():
    return {"message": "pong"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
