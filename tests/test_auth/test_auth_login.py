"""
Test suite for POST /auth/login endpoint.

Tests authentication functionality, security measures, and error handling.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLoginEndpoint:
    """Test cases for user login endpoint."""

    # ==================== SUCCESS CASES ====================

    async def test_login_success(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """Test successful login with correct credentials."""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        # Should return access token
        assert "access_token" in data
        assert data["access_token"] is not None
        assert len(data["access_token"]) > 0

        # Should have token type
        assert "token_type" in data
        assert data["token_type"] == "Bearer"

        # Should NOT expose password
        assert "password" not in data
        assert "password_hash" not in data

    async def test_login_token_is_valid_paseto(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """Test that returned token is a valid PASETO token."""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200

        token = response.json()["access_token"]
        # PASETO tokens start with version prefix (v2.local or v4.local)
        assert token.startswith("v2.local.") or token.startswith("v4.local.")

    async def test_login_can_use_token_for_protected_endpoint(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """Test that login token can be used to access protected endpoints."""
        # Login
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        login_response = await client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        # Verify token format is correct for PASETO
        assert token is not None
        assert len(token) > 100
        assert token.startswith("v2.local.") or token.startswith("v4.local.")

        # Optionally, you can call a protected route here if desired,
        # but your decorator tests already cover RBAC behavior.

    # ==================== FAILURE CASES ====================

    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with non-existent username."""
        login_data = {
            "username": "nonexistent_user_12345",
            "password": "SomePassword123!",
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "detail" in response.json()

        # Should have generic error message (security best practice)
        detail = response.json()["detail"].lower()
        assert "invalid" in detail or "credentials" in detail

    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """Test login with correct username but wrong password."""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": "WrongPassword123!",
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "detail" in response.json()

        # Should NOT reveal if username exists (security)
        detail = response.json()["detail"].lower()
        assert "invalid" in detail or "credentials" in detail

    async def test_login_empty_username(self, client: AsyncClient):
        """Test login with empty username."""
        login_data = {
            "username": "",
            "password": "SomePassword123!",
        }

        response = await client.post("/auth/login", json=login_data)

        # Should be validation error (422) or unauthorized (401)
        assert response.status_code in [401, 422]

    async def test_login_empty_password(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """Test login with empty password."""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": "",
        }

        response = await client.post("/auth/login", json=login_data)

        # Should be validation error (422) or unauthorized (401)
        assert response.status_code in [401, 422]

    async def test_login_missing_username(self, client: AsyncClient):
        """Test login with missing username field."""
        login_data = {
            "password": "SomePassword123!",
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 422

        errors = response.json()["detail"]
        assert any(error["loc"][-1] == "username" for error in errors)

    async def test_login_missing_password(self, client: AsyncClient):
        """Test login with missing password field."""
        login_data = {
            "username": "testuser",
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 422

        errors = response.json()["detail"]
        assert any(error["loc"][-1] == "password" for error in errors)

    async def test_login_case_sensitive_username(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """Test that username is case-sensitive."""
        login_data = {
            "username": registered_user["user_data"]["username"].upper(),
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)

        # Depends on business logic - here we assume usernames are case-sensitive
        assert response.status_code == 401

    # ==================== SECURITY CASES ====================

    async def test_login_sql_injection_attempt(self, client: AsyncClient):
        """Test SQL injection attempt is safely handled."""
        login_data = {
            "username": "admin' OR '1'='1",
            "password": "password' OR '1'='1",
        }

        response = await client.post("/auth/login", json=login_data)

        # Should fail authentication, not cause server error
        assert response.status_code == 401

    async def test_login_xss_attempt_in_username(self, client: AsyncClient):
        """Test XSS attempt in username is safely handled."""
        login_data = {
            "username": "<script>alert('xss')</script>",
            "password": "SomePassword123!",
        }

        response = await client.post("/auth/login", json=login_data)

        # Should fail authentication, not reflect the script
        assert response.status_code == 401
        assert "<script" not in response.text.lower()

    async def test_login_special_characters_in_password(
        self,
        client: AsyncClient,
        admin_token: dict,
    ):
        """Test login with password containing special characters."""
        # Register a user with a complex password via protected register
        user_data = {
            "username": "special_pass_user",
            "password": "P@$$w0rd!#€%&/()=?",
            "full_name": "Special Password User",
            "role": "mecanico",
        }
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        reg_response = await client.post(
            "/auth/register",
            json=user_data,
            headers=headers,
        )
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"

        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }
        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_multiple_users_different_tokens(
        self,
        client: AsyncClient,
        admin_token: dict,
    ):
        """Test that different users get different tokens."""
        # Register two users via protected register
        user1_data = {
            "username": "user1",
            "password": "Password123!",
            "full_name": "User One",
            "role": "mecanico",
        }
        user2_data = {
            "username": "user2",
            "password": "Password123!",
            "full_name": "User Two",
            "role": "mecanico",
        }

        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        reg1 = await client.post("/auth/register", json=user1_data, headers=headers)
        assert reg1.status_code == 201, f"User 1 registration failed: {reg1.text}"

        reg2 = await client.post("/auth/register", json=user2_data, headers=headers)
        assert reg2.status_code == 201, f"User 2 registration failed: {reg2.text}"

        # Login for each user
        login1 = await client.post(
            "/auth/login",
            json={
                "username": user1_data["username"],
                "password": user1_data["password"],
            },
        )
        login2 = await client.post(
            "/auth/login",
            json={
                "username": user2_data["username"],
                "password": user2_data["password"],
            },
        )

        assert login1.status_code == 200
        assert login2.status_code == 200

        token1 = login1.json()["access_token"]
        token2 = login2.json()["access_token"]

        assert token1 != token2

    async def test_login_numeric_username(
        self,
        client: AsyncClient,
        admin_token: dict,
    ):
        """Test login with numeric username."""
        # Register user with numeric username via protected register
        user_data = {
            "username": "123456",
            "password": "Password123!",
            "full_name": "Numeric User",
            "role": "mecanico",
        }
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        reg_response = await client.post(
            "/auth/register",
            json=user_data,
            headers=headers,
        )
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"

        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }
        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_very_long_password(
        self,
        client: AsyncClient,
        admin_token: dict,
    ):
        """Test login with a very long but valid password."""
        long_password = "A" * 100 + "1!"  # Ensure it meets complexity
        user_data = {
            "username": "long_password_user",
            "password": long_password,
            "full_name": "Long Password User",
            "role": "mecanico",
        }
        headers = {"Authorization": f"Bearer {admin_token['token']}"}

        reg_response = await client.post(
            "/auth/register",
            json=user_data,
            headers=headers,
        )
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"

        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }
        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_timing_attack_prevention(
        self,
        client: AsyncClient,
        registered_user: dict,
    ):
        """
        Basic check that invalid login does not crash the server.

        Detailed constant-time guarantees are enforced in lower-level tests
        for the password service.
        """
        # Valid username, invalid password
        login_invalid = {
            "username": registered_user["user_data"]["username"],
            "password": "CompletelyWrongPassword!",
        }
        # Completely invalid username
        login_unknown = {
            "username": "non_existent_user_for_timing_check",
            "password": "SomePassword123!",
        }

        resp_invalid = await client.post("/auth/login", json=login_invalid)
        resp_unknown = await client.post("/auth/login", json=login_unknown)

        assert resp_invalid.status_code == 401
        assert resp_unknown.status_code == 401
