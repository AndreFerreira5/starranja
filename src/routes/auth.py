import logging
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.authentication.exceptions import (
    InvalidPasswordError,
    PasswordHashingError,
    PasswordVerificationError,
    TokenGenerationError,
)
from src.authentication.services.password import PasswordService, hash_password
from src.authentication.services.token import generate_token as token_generator_fn
from src.db.clients import (
    assign_role_to_user,
    create_user,
    get_role_by_name,
    get_roles_by_user_id,
    get_user_by_username,
)
from src.db.connection import get_auth_db
from src.models.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse

logger = logging.getLogger(__name__)
password_service = PasswordService()
router = APIRouter()


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_user(request: LoginRequest, db: AsyncSession = Depends(get_auth_db)):
    # Get user from database
    user = await get_user_by_username(db, username=request.username)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    password_hash = cast(str, user.password_hash)

    try:
        is_valid = password_service.check_password(password_hash, request.password)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
    except PasswordVerificationError as e:
        # Log the error but don't expose details
        logger.error(f"Password verification error for user {user.username}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    # Get user roles
    user_roles_db = await get_roles_by_user_id(db, user_id=str(user.id))
    roles_list = [cast(str, role.name) for role in user_roles_db]

    if not roles_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário não possui funções de acesso.")

    # Generate token
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
    """Register a new user with specified role"""

    # Check if username already exists
    existing_user = await get_user_by_username(db, username=request.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nome de usuário já registrado.")

    # Hash password
    try:
        hashed_password = hash_password(request.password)
        print(f"DEBUG: Generated hash: {hashed_password[:30]}...")  # ← Add this
        print(f"DEBUG: Hash length: {len(hashed_password)}")  # ← Add this
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PasswordHashingError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha interna ao processar a senha."
        )

    # Create user
    new_user = await create_user(
        db=db,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        email=request.email if request.email else None,
    )

    # Assign the role specified in request body
    try:
        # Get the role from database by name
        role = await get_role_by_name(db, request.role.value)

        if not role:
            logger.error(f"Role '{request.role.value}' not found in database!")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Função '{request.role.value}' não existe no sistema."
            )

        # Link user to role via user_roles table
        await assign_role_to_user(db, str(new_user.id), role.id)
        logger.info(f"Assigned '{request.role.value}' role to user: {new_user.username}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign role to user {new_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao atribuir função de usuário."
        )

    return new_user
