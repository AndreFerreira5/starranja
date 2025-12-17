from uuid import UUID

from fastapi import Depends, HTTPException, Request

# --- IMPORT FROM AUTH TEAM ---
from src.authentication.decorators import token_required
from src.repository.work_orders import WorkOrderRepo


def get_database(request: Request):
    """Retrieve the MongoDB database from app state."""
    return getattr(request.app.state, "db", None)


def get_work_order_repo(db=Depends(get_database)) -> WorkOrderRepo:
    """Dependency to provide WorkOrderRepo."""
    return WorkOrderRepo(db)


def get_current_user_id(
    # We use the Auth Team's existing dependency here
    payload: dict = Depends(token_required()),
) -> UUID:
    """
    Uses the Auth team's 'token_required' to validate the user,
    then converts the string ID to a UUID object for our Repo.
    """
    try:
        user_id_str = payload.get("user_id")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid Token Payload")
        return UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid User ID format")
