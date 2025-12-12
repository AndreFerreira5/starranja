import logging
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.authentication.decorators import token_required
from src.authentication.services.password import PasswordService
from src.authentication.services.refresh_token_service import RefreshTokenService
from src.authentication.services.token import generate_token as token_generator_fn
from src.config import settings
from src.db.clients import (
    assign_role_to_user,
    create_user,
    delete_user,
    get_role_by_name,
    get_roles_by_user_id,
    get_user_by_username,
    update_user,
)
from src.db.connection import get_auth_db
from src.models.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    UserUpdate,
)

logger = logging.getLogger(__name__)

# Instantiate services outside if they are stateless, or inside dependency
password_service = PasswordService()
router = APIRouter()


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_auth_db),
) -> AuthResponse:
    """
    Login endpoint: authenticates user and returns PASETO access token AND refresh token.

    Raises 401 for invalid credentials and 500 for unexpected errors.
    """
    try:
        # Get user from database
        user = await get_user_by_username(db, request.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Verify password
        try:
            is_valid = password_service.check_password(
                user.password_hash,
                request.password,
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )
        except Exception as verify_error:
            logger.error("Password verification error: %s", verify_error)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Get user roles
        roles = await get_roles_by_user_id(db, str(user.id))
        role_names = [role.name for role in roles]

        # 1. Generate Access Token
        try:
            access_token = token_generator_fn(
                user_id=str(user.id),
                roles=role_names,
            )
        except Exception as token_error:
            logger.error("Token generation error: %s", token_error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating authentication token",
            )

        # 2. Generate Refresh Token
        try:
            # Instantiate service with dependencies
            refresh_service = RefreshTokenService(db, password_service)
            refresh_token = await refresh_service.generate_refresh_token(UUID(str(user.id)))
        except Exception as refresh_error:
            logger.error(f"Refresh token generation error: {refresh_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating refresh token"
            )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,  # Mitigates XSS (JS cannot access this)
            secure=True,  # Only sends over HTTPS (False for localhost testing if not https)
            samesite="strict",  # CSRF protection
            max_age=7 * 24 * 60 * 60,  # 7 days in seconds
        )

        # 3. Return ONLY Access Token in Body
        return AuthResponse(
            access_token=access_token,
            token_type="Bearer",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during login: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post(
    "/bootstrap-admin",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_admin_user(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_auth_db),
) -> UserResponse:
    """
    Test/dev-only endpoint to ensure an admin user exists.

    This MUST NOT be enabled in production. It is used by automated tests
    to create an initial admin account independent of RBAC.
    """
    # Read environment from flat Settings model; default to "production" if unset
    env_value = getattr(settings, "ENVIRONMENT", "production")
    if env_value.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin bootstrap not allowed in production",
        )

    # If user already exists and already has admin role, return it
    existing_user = await get_user_by_username(db, request.username)
    if existing_user:
        roles = await get_roles_by_user_id(db, str(existing_user.id))
        role_names = [r.name for r in roles]
        if "admin" in role_names:
            return UserResponse.model_validate(existing_user)

    # Otherwise create a new admin user
    try:
        password_hash = password_service.hash_password(request.password)
    except Exception as hash_error:
        logger.error("Password hashing error in bootstrap: %s", hash_error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password",
        )

    try:
        new_user = await create_user(
            db=db,
            username=request.username,
            hashed_password=password_hash,
            full_name=request.full_name,
            email=request.email,
        )
    except Exception as create_error:
        logger.error("User creation error in bootstrap: %s", create_error)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        )

    try:
        role = await get_role_by_name(db, "admin")
        if not role:
            logger.error("Admin role not found during bootstrap")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin role not found",
            )
        await assign_role_to_user(db, str(new_user.id), role.id)
        await db.commit()
        await db.refresh(new_user)
    except HTTPException:
        raise
    except Exception as role_error:
        logger.error("Role assignment error in bootstrap: %s", role_error)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error assigning admin role",
        )

    return UserResponse.model_validate(new_user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_auth_db),
    current_user: dict = Depends(
        token_required(roles=["admin", "gerente", "mecanico_gerente"]),
    ),
) -> UserResponse:
    """
    Register a new user.

    This endpoint is protected by RBAC: only admin/manager roles are allowed.
    """
    try:
        # Optional: audit logging of who is creating users
        logger.info(
            "User registration requested by %s with roles %s",
            current_user.get("user_id"),
            current_user.get("roles"),
        )

        # Check if username already exists
        existing_user = await get_user_by_username(db, request.username)
        if existing_user:
            logger.warning(
                "Registration attempt with existing username: %s",
                request.username,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

        # Hash password
        try:
            password_hash = password_service.hash_password(request.password)
        except Exception as hash_error:
            logger.error("Password hashing error: %s", hash_error, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing password",
            )

        # Create user
        try:
            new_user = await create_user(
                db=db,
                username=request.username,
                hashed_password=password_hash,
                full_name=request.full_name,
                email=request.email,
            )
            logger.info("User created: %s with ID: %s", request.username, new_user.id)
        except Exception as create_error:
            logger.error("User creation error: %s", create_error, exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user",
            )

        # Get role
        try:
            role = await get_role_by_name(db, request.role)
            if not role:
                logger.error("Invalid role requested: %s", request.role)
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {request.role}",
                )
            logger.info(
                "Role found: %s with ID: %s",
                request.role,
                role.id,
            )
        except HTTPException:
            raise
        except Exception as role_error:
            logger.error("Role lookup error: %s", role_error, exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error looking up role",
            )

        # Assign role to user
        try:
            await assign_role_to_user(db, str(new_user.id), role.id)
            logger.info(
                "Role %s assigned to user %s",
                request.role,
                request.username,
            )
        except Exception as assign_error:
            logger.error("Role assignment error: %s", assign_error, exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error assigning role",
            )

        # Commit transaction
        try:
            await db.commit()
            logger.info("Transaction committed for user: %s", request.username)
        except Exception as commit_error:
            logger.error("Database commit error: %s", commit_error, exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error saving user",
            )

        # Refresh to get the latest data
        try:
            await db.refresh(new_user)
        except Exception as refresh_error:
            logger.warning("Failed to refresh user object: %s", refresh_error)

        logger.info(
            "User registration completed successfully: %s",
            request.username,
        )

        # Return UserResponse using model_validate to automatically map all fields
        return UserResponse.model_validate(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during registration: %s", e, exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_auth_db),
):
    """
    Refresh Access Token Endpoint.

    1. Validates the refresh token (from HttpOnly cookie).
    2. Revokes the old refresh token (Token Rotation).
    3. Issues a new Access Token and a new Refresh Token.
    """
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    # Instantiate services
    refresh_service = RefreshTokenService(db, password_service)

    try:
        # 1. Validate the existing refresh token
        token_record = await refresh_service.validate_refresh_token(refresh_token)
        user_id = token_record.user_id

        # 2. Revoke the old token (Token Rotation)
        await refresh_service.revoke_refresh_token(UUID(str(token_record.id)))

        # 3. Get user roles for the new access token
        roles = await get_roles_by_user_id(db, str(user_id))
        role_names = [role.name for role in roles]

        # 4. Generate NEW Access Token
        new_access_token = token_generator_fn(user_id=str(user_id), roles=role_names)

        # 5. Generate NEW Refresh Token
        new_refresh_token = await refresh_service.generate_refresh_token(UUID(str(user_id)))

        # 6. Set the NEW Refresh Token in HttpOnly Cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,  # Set False if testing on localhost without HTTPS
            samesite="strict",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

        return AuthResponse(access_token=new_access_token, token_type="Bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(token_required(roles=["admin"]))],
)
async def update_user_endpoint(
    user_id: str,
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_auth_db),
    current_user: dict = Depends(token_required(roles=["admin"])),
) -> UserResponse:
    """
    Update a user profile.
    Restricted to 'admin' role only.
    """
    try:
        # Pass password_service to handle hashing if password is updated
        updated_user = await update_user(
            db=db,
            user_id=user_id,
            user_update=update_data,
            password_service=password_service,
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info("User %s updated by admin %s", user_id, current_user.get("user_id"))
        return UserResponse.model_validate(updated_user)

    except ValueError as e:
        # Catch errors like missing password service
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update user",
        )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(token_required(roles=["admin"]))],
)
async def delete_user_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_auth_db),
    current_user: dict = Depends(token_required(roles=["admin"])),
) -> None:
    """
    Delete a user permanently.
    Restricted to 'admin' role only.
    """
    try:
        # Prevent admin from deleting themselves
        if str(user_id) == str(current_user.get("user_id")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account.",
            )

        success = await delete_user(db, user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info("User %s deleted by admin %s", user_id, current_user.get("user_id"))
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete user",
        )
