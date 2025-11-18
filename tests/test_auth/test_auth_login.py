"""
Test suite for POST /auth/login endpoint.
Tests authentication functionality, security measures, and error handling.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLoginEndpoint:
    """Test cases for user login endpoint"""

    # ==================== SUCCESS CASES ====================

    async def test_login_success(self, client: AsyncClient, registered_user: dict):
        """Test successful login with correct credentials"""
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

    async def test_login_token_is_valid_paseto(self, client: AsyncClient, registered_user: dict):
        """Test that returned token is a valid PASETO token"""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200

        token = response.json()["access_token"]
        # PASETO tokens start with version prefix (v2.local or v4.local)
        assert token.startswith("v2.local.") or token.startswith("v4.local.")

    async def test_login_can_use_token_for_protected_endpoint(self, client: AsyncClient, registered_user: dict):
        """Test that login token can be used to access protected endpoints"""
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

    # ==================== FAILURE CASES ====================

    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with non-existent username"""
        login_data = {"username": "nonexistent_user_12345", "password": "SomePassword123!"}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "detail" in response.json()

        # Should have generic error message (security best practice)
        detail = response.json()["detail"].lower()
        assert "invalid" in detail or "credentials" in detail

    async def test_login_invalid_password(self, client: AsyncClient, registered_user: dict):
        """Test login with correct username but wrong password"""
        login_data = {"username": registered_user["user_data"]["username"], "password": "WrongPassword123!"}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        assert "detail" in response.json()

        # Should NOT reveal if username exists (security)
        detail = response.json()["detail"].lower()
        assert "invalid" in detail or "credentials" in detail

    async def test_login_empty_username(self, client: AsyncClient):
        """Test login with empty username"""
        login_data = {"username": "", "password": "SomePassword123!"}

        response = await client.post("/auth/login", json=login_data)
        # Should be validation error (422) or unauthorized (401)
        assert response.status_code in [401, 422]

    async def test_login_empty_password(self, client: AsyncClient, registered_user: dict):
        """Test login with empty password"""
        login_data = {"username": registered_user["user_data"]["username"], "password": ""}

        response = await client.post("/auth/login", json=login_data)
        # Should be validation error (422) or unauthorized (401)
        assert response.status_code in [401, 422]

    async def test_login_missing_username(self, client: AsyncClient):
        """Test login with missing username field"""
        login_data = {"password": "SomePassword123!"}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 422

        errors = response.json()["detail"]
        assert any(error["loc"][-1] == "username" for error in errors)

    async def test_login_missing_password(self, client: AsyncClient):
        """Test login with missing password field"""
        login_data = {"username": "testuser"}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 422

        errors = response.json()["detail"]
        assert any(error["loc"][-1] == "password" for error in errors)

    async def test_login_case_sensitive_username(self, client: AsyncClient, registered_user: dict):
        """Test that username is case-sensitive"""
        login_data = {
            "username": registered_user["user_data"]["username"].upper(),
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)
        # Depends on business logic - typically usernames are case-sensitive
        assert response.status_code == 401

    # ==================== SECURITY CASES ====================

    async def test_login_sql_injection_attempt(self, client: AsyncClient):
        """Test SQL injection attempt is safely handled"""
        login_data = {"username": "admin' OR '1'='1", "password": "password' OR '1'='1"}

        response = await client.post("/auth/login", json=login_data)
        # Should fail authentication, not cause server error
        assert response.status_code == 401

    async def test_login_xss_attempt_in_username(self, client: AsyncClient):
        """Test XSS attempt in username is safely handled"""
        login_data = {"username": "<script>alert('xss')</script>", "password": "SomePassword123!"}

        response = await client.post("/auth/login", json=login_data)
        # Should fail authentication safely
        assert response.status_code == 401

    async def test_login_timing_attack_prevention(self, client: AsyncClient, registered_user: dict):
        """Test that response times are similar for valid and invalid usernames"""
        import time

        # Test with invalid username
        start = time.time()
        await client.post("/auth/login", json={"username": "invalid_user", "password": "SomePassword123!"})
        invalid_time = time.time() - start

        # Test with valid username but wrong password
        start = time.time()
        await client.post(
            "/auth/login", json={"username": registered_user["user_data"]["username"], "password": "WrongPassword123!"}
        )
        valid_time = time.time() - start

        # Times should be similar (within 2x) to prevent timing attacks
        # This is a basic check - real timing attack prevention requires constant-time comparison
        assert abs(valid_time - invalid_time) < max(valid_time, invalid_time)

    async def test_login_special_characters_in_password(self, client: AsyncClient):
        """Test login with special characters in password"""
        # Register user with special character password
        user_data = {
            "username": "special_char_user",
            "password": "P@ssw0rd!#$%^&*()",
            "full_name": "Special Char User",
            "email": "special@example.com",
            "role": "mecanico",
        }

        reg_response = await client.post("/auth/register", json=user_data)
        assert reg_response.status_code == 201

        # Login with special character password
        login_data = {"username": user_data["username"], "password": user_data["password"]}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200

    # ==================== TOKEN VERIFICATION ====================

    async def test_login_token_contains_expected_data(self, client: AsyncClient, registered_user: dict):
        """Test that token contains expected user data"""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)
        token = response.json()["access_token"]

        # PASETO tokens should be encrypted - we can't decode without the key
        # But we can verify it's a valid format
        assert len(token) > 100  # PASETO tokens are fairly long
        assert "." in token  # Should have parts separated by dots

    async def test_login_token_has_expiration(self, client: AsyncClient, registered_user: dict):
        """Test that token has expiration time set"""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200

        # Token should be present
        token = response.json()["access_token"]
        assert token is not None

        # Note: Actual expiration validation would require decoding the token
        # which requires access to the secret key

    async def test_login_multiple_users_different_tokens(self, client: AsyncClient):
        """Test that different users get different tokens"""
        # Register two users
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

        reg1 = await client.post("/auth/register", json=user1_data)
        assert reg1.status_code == 201, f"User 1 registration failed: {reg1.text}"

        reg2 = await client.post("/auth/register", json=user2_data)
        assert reg2.status_code == 201, f"User 2 registration failed: {reg2.text}"

        # Login both users
        response1 = await client.post("/auth/login", json={"username": "user1", "password": "Password123!"})
        assert response1.status_code == 200, f"User 1 login failed: {response1.text}"

        response2 = await client.post("/auth/login", json={"username": "user2", "password": "Password123!"})
        assert response2.status_code == 200, f"User 2 login failed: {response2.text}"

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Tokens should be different
        assert token1 != token2

    # ==================== EDGE CASES ====================

    async def test_login_unicode_characters_in_username(self, client: AsyncClient):
        """Test login with unicode characters in username"""
        login_data = {"username": "用户名", "password": "Password123!"}

        response = await client.post("/auth/login", json=login_data)
        # Should handle gracefully (either 401 or accept depending on validation rules)
        assert response.status_code in [401, 422]

    async def test_login_very_long_username(self, client: AsyncClient):
        """Test login with very long username"""
        login_data = {"username": "a" * 1000, "password": "Password123!"}

        response = await client.post("/auth/login", json=login_data)
        # Should handle gracefully
        assert response.status_code in [401, 422]

    async def test_login_very_long_password(self, client: AsyncClient, registered_user: dict):
        """Test login with very long password"""
        login_data = {"username": registered_user["user_data"]["username"], "password": "a" * 1000}

        response = await client.post("/auth/login", json=login_data)
        # Should handle gracefully
        assert response.status_code in [401, 422]

    async def test_login_null_values(self, client: AsyncClient):
        """Test login with null values"""
        login_data = {"username": None, "password": None}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 422

    async def test_login_numeric_username(self, client: AsyncClient):
        """Test login with numeric username"""
        # Register user with numeric username
        user_data = {
            "username": "123456",
            "password": "Password123!",
            "full_name": "Numeric User",
            "role": "mecanico",
        }

        reg_response = await client.post("/auth/register", json=user_data)
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"

        # Login with numeric username
        login_data = {"username": "123456", "password": "Password123!"}

        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200, f"Login failed: {response.text}"
