import pytest
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from src.authentication.services.token import RefreshTokenService
from src.models.auth import RefreshToken
from uuid import UUID


@pytest.mark.asyncio
class TestRefreshTokenService:

    async def test_generate_refresh_token(self, test_session, password_service, test_user):
        """Test that a token is generated and stored correctly."""
        service = RefreshTokenService(test_session, password_service)

        token_string = await service.generate_refresh_token(test_user.id)

        assert ":" in token_string
        token_id, secret = token_string.split(":")

        result = await test_session.execute(select(RefreshToken).where(RefreshToken.id == token_id))
        stored_token = result.scalar_one_or_none()

        assert stored_token is not None
        assert stored_token.user_id == test_user.id
        assert stored_token.is_revoked is False
        assert password_service.check_password(stored_token.token_hash, secret) is True


    async def test_validate_refresh_token_success(self, test_session, password_service, test_user):
        service = RefreshTokenService(test_session, password_service)
        token_string = await service.generate_refresh_token(test_user.id)

        validated_token = await service.validate_refresh_token(token_string)

        assert validated_token.user_id == test_user.id
        assert validated_token.is_revoked is False


    async def test_validate_revoked_token(self, test_session, password_service, test_user):
        service = RefreshTokenService(test_session, password_service)
        token_string = await service.generate_refresh_token(test_user.id)
        token_id = token_string.split(":")[0]

        await service.revoke_refresh_token(UUID(token_id))

        with pytest.raises(HTTPException) as exc:
            await service.validate_refresh_token(token_string)
        assert exc.value.status_code == 401
        assert "revoked" in exc.value.detail

    # CHANGED: 'db_session' -> 'test_session'
    async def test_validate_invalid_format(self, test_session, password_service):
        service = RefreshTokenService(test_session, password_service)

        with pytest.raises(HTTPException) as exc:
            await service.validate_refresh_token("invalidformat")
        assert exc.value.status_code == 401


    async def test_validate_wrong_secret(self, test_session, password_service, test_user):
        service = RefreshTokenService(test_session, password_service)
        token_string = await service.generate_refresh_token(test_user.id)
        token_id = token_string.split(":")[0]

        fake_token = f"{token_id}:wrongsecret123"

        with pytest.raises(HTTPException) as exc:
            await service.validate_refresh_token(fake_token)
        assert exc.value.status_code == 401
        assert "signature" in exc.value.detail
