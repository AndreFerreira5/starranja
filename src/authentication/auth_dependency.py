from fastapi import Depends, Header, HTTPException, status

from src.authentication.services.token import verify_token


async def auth_required(authorization: str = Header(...)) -> dict:
    """
    Dependency to verify authentication token.
    Returns the decoded token payload containing user info and roles.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme. Expected 'Bearer <token>'"
        )

    token = authorization.replace("Bearer ", "")

    try:
        payload = verify_token(token)
        return payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


class RoleChecker:
    """
    Dependency class to check if authenticated user has required roles.

    Usage:
        admin_only = RoleChecker(allowed_roles=["admin"])

        @router.post("/protected")
        async def protected_endpoint(user: dict = Depends(admin_only)):
            return {"message": "Access granted"}
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user_payload: dict = Depends(auth_required)) -> dict:
        """
        Check if user has any of the allowed roles.
        Raises 403 Forbidden if user doesn't have required permissions.
        """
        user_roles = user_payload.get("roles", [])

        if not any(role in self.allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(self.allowed_roles)}",
            )

        return user_payload
