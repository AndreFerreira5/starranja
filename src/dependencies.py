from uuid import UUID

from fastapi import Depends, HTTPException

# Import from the Auth Team
from src.authentication.decorators import token_required

# Import the CENTRAL get_database from connection.py
from src.db.connection import get_mongo_db
from src.repository.invoices import InvoiceRepo
from src.repository.work_orders import WorkOrderRepo

# --- REMOVE the local get_database(request: Request) function entirely ---


def get_invoices_repo(
    db=Depends(get_mongo_db),
) -> InvoiceRepo:
    """Dependency to provide InvoiceRepo."""
    return InvoiceRepo(db)


def get_work_order_repo(
    # Now this Depends matches the one we are overriding in the test
    db=Depends(get_mongo_db),
) -> WorkOrderRepo:
    """Dependency to provide WorkOrderRepo."""
    return WorkOrderRepo(db)


def get_current_user_id(payload: dict = Depends(token_required())) -> UUID:
    """
    Uses the Auth team's 'token_required' to validate the user.
    """
    try:
        user_id_str = payload.get("user_id")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid Token Payload")
        return UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid User ID format")
