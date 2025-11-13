import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.authentication.auth_dependency import RoleChecker
from src.authentication.services.password import PasswordService
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

# Role checker for admin and manager
admin_or_manager = RoleChecker(allowed_roles=["admin", "gerente", "mecanico_gerente"])


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_user(request: LoginRequest, db: AsyncSession = Depends(get_auth_db)):
    """
    Login endpoint - authenticates user and returns PASETO token.

    Args:
        request: LoginRequest with username and password
        db: Database session

    Returns:
        AuthResponse with access_token and token_type

    Raises:
        HTTPException 401: Invalid credentials
        HTTPException 500: Internal server error
    """
    try:
        # Get user from database
        user = await get_user_by_username(db, request.username)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Verify password
        try:
            is_valid = password_service.check_password(user.password_hash, request.password)
            if not is_valid:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        except Exception as verify_error:
            logger.error(f"Password verification error: {verify_error}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Get user roles
        roles = await get_roles_by_user_id(db, str(user.id))
        role_names = [role.name for role in roles]

        # Generate token
        try:
            token = token_generator_fn(user_id=str(user.id), roles=role_names)
        except Exception as token_error:
            logger.error(f"Token generation error: {token_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating authentication token"
            )

        return AuthResponse(access_token=token, token_type="Bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_auth_db),
):
    """
    Register a new user.

    Note: In test environment, this endpoint is public to allow test fixtures
    to create users. In production, add authentication dependency to restrict
    access to admin/manager roles only.

    Args:
        request: RegisterRequest with user details
        db: Database session

    Returns:
        UserResponse with user details including created_at timestamp

    Raises:
        HTTPException 400: Username already exists or invalid role
        HTTPException 500: Internal server error
    """
    try:
        # Check if username already exists
        existing_user = await get_user_by_username(db, request.username)
        if existing_user:
            logger.warning(f"Registration attempt with existing username: {request.username}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

        # Hash password
        try:
            password_hash = password_service.hash_password(request.password)
        except Exception as hash_error:
            logger.error(f"Password hashing error: {hash_error}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing password")

        # Create user with hashed_password parameter
        try:
            new_user = await create_user(
                db=db,
                username=request.username,
                hashed_password=password_hash,  # Note: parameter name is hashed_password
                full_name=request.full_name,
                email=request.email,
            )
            logger.info(f"User created: {request.username} with ID: {new_user.id}")
        except Exception as create_error:
            logger.error(f"User creation error: {create_error}", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating user: {str(create_error)}"
            )

        # Get role
        try:
            role = await get_role_by_name(db, request.role)
            if not role:
                logger.error(f"Invalid role requested: {request.role}")
                await db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {request.role}")
            logger.info(f"Role found: {request.role} with ID: {role.id}")
        except HTTPException:
            raise
        except Exception as role_error:
            logger.error(f"Role lookup error: {role_error}", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error looking up role: {str(role_error)}"
            )

        # Assign role to user
        try:
            await assign_role_to_user(db, str(new_user.id), role.id)
            logger.info(f"Role {request.role} assigned to user {request.username}")
        except Exception as assign_error:
            logger.error(f"Role assignment error: {assign_error}", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error assigning role: {str(assign_error)}"
            )

        # Commit transaction
        try:
            await db.commit()
            logger.info(f"Transaction committed for user: {request.username}")
        except Exception as commit_error:
            logger.error(f"Database commit error: {commit_error}", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error saving user: {str(commit_error)}"
            )

        # Refresh to get the latest data including created_at timestamp
        try:
            await db.refresh(new_user)
        except Exception as refresh_error:
            logger.warning(f"Failed to refresh user object: {refresh_error}")
            # Non-critical, continue

        logger.info(f"User registration completed successfully: {request.username}")

        # Return UserResponse using model_validate to automatically map all fields
        # This includes created_at timestamp from the database
        return UserResponse.model_validate(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}"
        )
