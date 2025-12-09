import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.auth import RefreshToken
from src.authentication.services.password import PasswordService


class RefreshTokenService:
    """
    Service for handling Refresh Token lifecycle (Database-backed).
    """

    def __init__(self, db: AsyncSession, password_service: PasswordService):
        self.db = db
        self.password_service = password_service
        self.REFRESH_TOKEN_EXPIRE_DAYS = 7  # Configurable

    async def generate_refresh_token(self, user_id: UUID) -> str:
        """
        Generates a refresh token, stores the hash, and returns a compound string 'uuid:secret'.
        """
        # 1. Generate secure random string
        secret_token = secrets.token_urlsafe(64)

        # 2. Hash it (Argon2)
        token_hash = self.password_service.hash_password(secret_token)

        # 3. Create DB record
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

        new_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False
        )

        self.db.add(new_token)
        await self.db.commit()
        await self.db.refresh(new_token)

        # 4. Return compound token
        return f"{new_token.id}:{secret_token}"

    async def validate_refresh_token(self, plaintext_token: str) -> RefreshToken:
        """
        Validates the compound token string.
        """
        try:
            if ":" not in plaintext_token:
                raise ValueError("Invalid format")

            token_id_str, secret = plaintext_token.split(":", 1)
            token_uuid = UUID(token_id_str)

        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token format"
            )

        # Find token by ID
        query = select(RefreshToken).where(RefreshToken.id == token_uuid)
        result = await self.db.execute(query)
        refresh_token_record = result.scalar_one_or_none()

        if not refresh_token_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")

        if refresh_token_record.is_revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

        if refresh_token_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        # Verify hash
        if not self.password_service.check_password(refresh_token_record.token_hash, secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

        return refresh_token_record

    async def revoke_refresh_token(self, token_id: UUID) -> None:
        query = select(RefreshToken).where(RefreshToken.id == token_id)
        result = await self.db.execute(query)
        token = result.scalar_one_or_none()
        if token:
            token.is_revoked = True
            await self.db.commit()
