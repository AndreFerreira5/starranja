# src/routes/auth.py

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.authentication.exceptions import InvalidPasswordError, PasswordHashingError, TokenGenerationError
from src.authentication.services.password import PasswordService, hash_password
from src.authentication.services.token import generate_token as token_generator_fn
from src.db.clients import create_user, get_roles_by_user_id, get_user_by_username
from src.db.connection import get_auth_db
from src.models.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse

logger = logging.getLogger(__name__)
password_service = PasswordService()
router = APIRouter()


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_user(request: LoginRequest, db: AsyncSession = Depends(get_auth_db)):
    user = await get_user_by_username(db, username=request.username)

    if not user or not password_service.check_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    user_roles_db = await get_roles_by_user_id(db, user_id=str(user.id))
    roles_list = [role.name for role in user_roles_db]

    if not roles_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário não possui funções de acesso.")

    try:
        access_token = token_generator_fn(user_id=str(user.id), roles=roles_list)

    except TokenGenerationError as e:
        logger.error(f"Failed to generate token for user {user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha na geração do token de acesso."
        )

    return AuthResponse(access_token=access_token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: RegisterRequest, db: AsyncSession = Depends(get_auth_db)):
    existing_user = await get_user_by_username(db, username=request.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nome de usuário já registrado.")

    try:
        hashed_password = hash_password(request.password)

    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PasswordHashingError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha interna ao processar a senha."
        )

    new_user = await create_user(
        db=db,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        email=request.email if request.email else None,
    )

    return new_user
