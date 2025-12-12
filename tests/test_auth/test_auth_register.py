import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.clients import get_user_by_username


@pytest.mark.asyncio
class TestRegisterEndpoint:
    """Test cases for user registration endpoint."""

    async def test_register_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        sample_user_data: dict,
        admin_token: dict,
    ):
        """Test successful user registration with valid admin credentials."""
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        response = await client.post("/auth/register", json=sample_user_data, headers=headers)
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

    async def test_register_without_email(
        self,
        client: AsyncClient,
        sample_user_data_no_email: dict,
        admin_token: dict,
    ):
        """Test registration without email (optional field)."""
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        response = await client.post(
            "/auth/register",
            json=sample_user_data_no_email,
            headers=headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert data["username"] == sample_user_data_no_email["username"]
        assert data["email"] is None

    async def test_register_duplicate_username(
        self,
        client: AsyncClient,
        sample_user_data: dict,
        admin_token: dict,
    ):
        """Test registration with duplicate username."""
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        # Register first user
        response1 = await client.post("/auth/register", json=sample_user_data, headers=headers)
        assert response1.status_code == 201

        # Try to register with same username
        response2 = await client.post("/auth/register", json=sample_user_data, headers=headers)
        assert response2.status_code == 400
        assert "username already exists" in response2.json()["detail"].lower()

    async def test_register_invalid_password_too_short(
        self,
        client: AsyncClient,
        admin_token: dict,
    ):
        """Test registration with password too short."""
        user_data = {
            "username": "shortpass",
            "password": "short",  # too short
            "full_name": "Short Pass User",
            "email": "short@example.com",
            "role": "mecanico",
        }
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        response = await client.post("/auth/register", json=user_data, headers=headers)
        # Schema validation should reject short password
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        assert any("password" in err["loc"] for err in data["detail"])

    async def test_register_missing_required_fields(
        self,
        client: AsyncClient,
        admin_token: dict,
    ):
        """Test registration with missing required fields."""
        incomplete_data = {"username": "incomplete"}  # missing password, full_name, role
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        response = await client.post("/auth/register", json=incomplete_data, headers=headers)
        assert response.status_code == 422

    async def test_register_multiple_users(
        self,
        client: AsyncClient,
        multiple_users_data: list[dict],
        admin_token: dict,
    ):
        """Test registering multiple different users."""
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        for user_data in multiple_users_data:
            response = await client.post("/auth/register", json=user_data, headers=headers)
            assert response.status_code == 201
            assert response.json()["username"] == user_data["username"]
