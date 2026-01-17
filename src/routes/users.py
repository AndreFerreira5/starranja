from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.authentication.decorators import token_required
from src.db.clients import get_all_users
from src.db.connection import get_auth_db
from src.models.schemas import UserResponse

router = APIRouter(tags=["Users"])


@router.get("/me")
def read_current_user(user_payload: Annotated[dict, Depends(token_required())]):
    return {
        "message": "Autenticação bem-sucedida",
        "user_id": user_payload.get("user_id"),
        "roles": user_payload.get("roles"),
    }


# TODO initial version of user retrieval, later add possibility for filtering using roles
@router.get("/", response_model=list[UserResponse])
async def get_users(
    user_payload: Annotated[dict, Depends(token_required(roles=["admin", "gerente"]))],
    db: AsyncSession = Depends(get_auth_db),
):
    return await get_all_users(db)
