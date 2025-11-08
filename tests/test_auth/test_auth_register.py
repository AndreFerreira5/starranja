import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.clients import get_user_by_username


@pytest.mark.asyncio
class TestRegisterEndpoint:
    """Test cases for user registration endpoint"""

    async def test_register_success(self, client: AsyncClient, test_session: AsyncSession, sample_user_data: dict):
        """Test successful user registration"""
        response = await client.post("/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == sample_user_data["username"]
        assert data["email"] == sample_user_data["email"]
        assert data["full_name"] == sample_user_data["full_name"]
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

        # Verify user exists in database
        user = await get_user_by_username(test_session, sample_user_data["username"])
        assert user is not None
        assert user.username == sample_user_data["username"]

    async def test_register_without_email(self, client: AsyncClient, sample_user_data_no_email: dict):
        """Test registration without email (optional field)"""
        response = await client.post("/auth/register", json=sample_user_data_no_email)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == sample_user_data_no_email["username"]
        assert data["email"] is None

    async def test_register_duplicate_username(self, client: AsyncClient, sample_user_data: dict):
        """Test registration with duplicate username"""
        # Register first user
        response1 = await client.post("/auth/register", json=sample_user_data)
        assert response1.status_code == 201

        # Try to register with same username
        response2 = await client.post("/auth/register", json=sample_user_data)
        assert response2.status_code == 409
        assert "registrado" in response2.json()["detail"].lower()

    async def test_register_invalid_password_too_short(self, client: AsyncClient):
        """Test registration with password too short"""
        user_data = {
            "username": "shortpass",
            "password": "short",
            "full_name": "Short Pass User",
            "email": "short@example.com",
        }

        response = await client.post("/auth/register", json=user_data)
        if response.status_code == 422:
            # Pydantic validation error
            assert "detail" in response.json()
        else:
            # Custom validation error (400)
            assert response.status_code == 400

    async def test_register_missing_required_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        incomplete_data = {"username": "incomplete"}

        response = await client.post("/auth/register", json=incomplete_data)
        assert response.status_code == 422

    async def test_register_multiple_users(self, client: AsyncClient, multiple_users_data: list):
        """Test registering multiple different users"""
        for user_data in multiple_users_data:
            response = await client.post("/auth/register", json=user_data)
            assert response.status_code == 201
            assert response.json()["username"] == user_data["username"]
