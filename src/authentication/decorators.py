"""
Role-Based Access Control (RBAC) Decorators for FastAPI Route Protection

Decorators:
- @token_required: Base authentication decorator
- @token_required(roles=[...]): Authentication + role-based authorization
"""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.authentication.exceptions import (
    InvalidTokenError,
    TokenError,
    TokenExpiredError,
)
from src.authentication.services.token import verify_token

logger = logging.getLogger(__name__)

# FastAPI HTTP Bearer scheme for automatic OpenAPI documentation
security_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="JWT-like PASETO token authentication",
    auto_error=False,  # We'll handle errors manually for better control
)


def normalize_roles(roles: list[str]) -> list[str]:
    """
    Normalize role names to lowercase for case-insensitive comparison.

    Args:
        roles: List of role names

    Returns:
        List of normalized (lowercase) role names
    """
    return [role.lower() for role in roles if isinstance(role, str)]


class AuthenticationRequired:
    """
    Dependency class for enforcing authentication on FastAPI routes.

    This class implements the authentication logic as a callable dependency
    that can be injected into FastAPI route handlers using Depends().

    Attributes:
        required_roles: Optional list of roles for authorization checks

    Raises:
        HTTPException 401: Authentication failed (missing, invalid, or expired token)
        HTTPException 403: Authorization failed (insufficient permissions)
    """

    def __init__(self, required_roles: list[str] | str | None = None):
        """
        Initialize the authentication dependency.

        Args:
            required_roles: Role(s) required for authorization.
                Can be a string (single role) or list of strings (multiple roles).
                If None, only authentication is enforced.
                If provided, user must have at least one of these roles.
                Role matching is case-insensitive.

        Raises:
            TypeError: If required_roles is not a string, list, or None
        """
        # Type validation and normalization
        if required_roles is None:
            self.required_roles = []
        elif isinstance(required_roles, str):
            self.required_roles = [required_roles.lower()]
        elif isinstance(required_roles, list):
            if not all(isinstance(role, str) for role in required_roles):
                raise TypeError("All roles must be strings")
            self.required_roles = normalize_roles(required_roles)
        else:
            raise TypeError(
                f"required_roles must be a string, list of strings, or None. Got {type(required_roles).__name__}"
            )

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    ) -> dict[str, Any]:
        """
        Validate authentication token and enforce authorization if roles are specified.

        This method is called automatically by FastAPI's dependency injection system.
        It extracts the Bearer token, validates it, and checks role permissions.

        Args:
            request: FastAPI request object (for attaching user state)
            credentials: HTTP Bearer credentials extracted from Authorization header

        Returns:
            dict: Decoded token payload containing user_id, roles, and timestamps

        Raises:
            HTTPException 401: If token is missing, invalid, or expired
            HTTPException 403: If user lacks required role permissions
            HTTPException 500: If token is missing required claims
        """
        # Step 1: Verify token is present
        if credentials is None:
            logger.warning("Authentication attempt without Bearer token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials

        # Step 2: Validate and decode token
        try:
            payload = verify_token(token)
            logger.debug(f"Token validated for user_id: {payload.get('user_id')}")

        except TokenExpiredError as e:
            logger.warning(f"Expired token used: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except InvalidTokenError as e:
            logger.warning(f"Invalid token received: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except TokenError as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authentication error",
            )

        # Step 3: Store user payload in request state for downstream access
        request.state.user = payload

        # Step 4: Enforce role-based authorization if roles are specified
        if self.required_roles:
            # Validate that token contains roles claim
            user_roles = payload.get("roles")

            if user_roles is None:
                logger.error(
                    f"Token for user {payload.get('user_id')} missing 'roles' claim. "
                    "This indicates a token service configuration error."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Token missing required claims. Please contact administrator.",
                )

            # Ensure user_roles is a list
            if not isinstance(user_roles, list):
                logger.error(
                    f"Token for user {payload.get('user_id')} has invalid 'roles' format. "
                    f"Expected list, got {type(user_roles).__name__}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Token has invalid format. Please contact administrator.",
                )

            # Normalize user roles for case-insensitive comparison
            normalized_user_roles = normalize_roles(user_roles)

            # Check if user has at least one of the required roles (case-insensitive)
            has_permission = any(role in self.required_roles for role in normalized_user_roles)

            if not has_permission:
                logger.warning(
                    f"Authorization denied for user {payload.get('user_id')} "
                    f"with roles {user_roles}. Required roles: {self.required_roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {', '.join(self.required_roles)}",
                )

            logger.debug(
                f"Authorization granted for user {payload.get('user_id')} with matching role from {user_roles}"
            )

        return payload


def token_required(roles: list[str] | str | None = None) -> Callable:
    """
    Decorator factory for creating authentication/authorization dependencies.

    This function returns a FastAPI dependency that can be used with Depends()
    to protect routes with authentication and optional role-based authorization.

    Args:
        roles: Optional role(s) required for authorization.
            Can be a string (single role) or list of strings (multiple roles).
            If None, only authentication is enforced.
            Role matching is case-insensitive.

    Returns:
        Callable: A dependency function compatible with FastAPI's Depends()
    """
    return AuthenticationRequired(required_roles=roles)


def get_current_user(request: Request) -> dict[str, Any]:
    """
    Extract the current authenticated user from the request state.

    Args:
        request: FastAPI request object

    Returns:
        dict: User payload from validated token

    Raises:
        AttributeError: If called without authentication decorator applied
    """
    if not hasattr(request.state, "user"):
        raise AttributeError(
            "User not found in request state. Ensure @token_required decorator is applied via Depends()"
        )
    return request.state.user
