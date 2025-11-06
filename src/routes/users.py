from fastapi import APIRouter, Depends
from typing import Annotated
from src.authentication.auth_dependency import auth_required

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def read_current_user(
    user_payload: Annotated[dict, Depends(auth_required)]
):
    return {
        "message": "Autenticação bem-sucedida",
        "user_id": user_payload.get("user_id"),
        "roles": user_payload.get("roles")
    }
