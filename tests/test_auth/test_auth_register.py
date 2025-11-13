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

        # --- FIX 1: Assert 400 and the correct error message ---
        assert response2.status_code == 400
        assert "username already exists" in response2.json()["detail"].lower()

    async def test_register_invalid_password_too_short(self, client: AsyncClient):
        """Test registration with password too short"""

        # --- FIX 2: Add all required fields, including a valid "role" ---
        user_data = {
            "username": "shortpass",
            "password": "short",  # This is the field we are testing
            "full_name": "Short Pass User",
            "email": "short@example.com",
            "role": "mecanico",  # Added missing required field
        }

        response = await client.post("/auth/register", json=user_data)

        # Now we can be sure the 422 is for the password length
        assert response.status_code == 422

        # Optional: A better assertion to check the error detail
        data = response.json()
        assert "detail" in data
        # Check that the validation error refers to the 'password' field
        assert any("password" in err["loc"] for err in data["detail"])

    async def test_register_missing_required_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        # Missing password, full_name, and role
        incomplete_data = {"username": "incomplete"}

        response = await client.post("/auth/register", json=incomplete_data)
        assert response.status_code == 422

    async def test_register_multiple_users(self, client: AsyncClient, multiple_users_data: list):
        """Test registering multiple different users"""
        for user_data in multiple_users_data:
            response = await client.post("/auth/register", json=user_data)
            assert response.status_code == 201
            assert response.json()["username"] == user_data["username"]
