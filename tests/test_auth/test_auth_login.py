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
        assert data["token_type"] in ["bearer", "Paseto"]

        # Should NOT expose password
        assert "password" not in data
        assert "password_hash" not in data

    async def test_login_success_returns_user_info(self, client: AsyncClient, registered_user: dict):
        """Test that login returns user information"""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        # Should include user info (optional but good practice)
        if "user" in data:
            assert data["user"]["username"] == registered_user["user_data"]["username"]
            assert "id" in data["user"]

    async def test_login_token_is_valid_jwt(self, client: AsyncClient, registered_user: dict):
        """Test that returned token is a valid JWT"""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Should be able to decode token (validation happens in endpoint)
        # Just check it has JWT structure
        assert len(token.split(".")) == 3  # JWT has 3 parts

    # ==================== FAILURE CASES ====================

    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with non-existent username"""
        login_data = {"username": "nonexistent_user", "password": "SomePassword123!"}

        response = await client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "detail" in response.json()
        # Should have generic error message (security best practice)
        detail = response.json()["detail"].lower()
        assert "inválidas" in detail or "invalid" in detail or "incorrect" in detail

    async def test_login_invalid_password(self, client: AsyncClient, registered_user: dict):
        """Test login with correct username but wrong password"""
        login_data = {"username": registered_user["user_data"]["username"], "password": "WrongPassword123!"}

        response = await client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "detail" in response.json()
        # Should NOT reveal if username exists (security)
        detail = response.json()["detail"].lower()
        assert "inválidas" in detail or "invalid" in detail or "incorrect" in detail

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

        # Depends on your business logic - typically case-sensitive
        assert response.status_code == 401

    # ==================== SECURITY CASES ====================

    async def test_login_sql_injection_attempt(self, client: AsyncClient):
        """Test SQL injection attempt is safely handled"""
        login_data = {"username": "admin' OR '1'='1", "password": "password' OR '1'='1"}

        response = await client.post("/auth/login", json=login_data)

        # Should fail authentication, not cause error
        assert response.status_code == 401

    async def test_login_no_timing_attack(self, client: AsyncClient, registered_user: dict):
        """Test that response time doesn't reveal user existence (timing attack prevention)"""
        import time

        # Login with valid username, wrong password
        start1 = time.time()
        response1 = await client.post(
            "/auth/login", json={"username": registered_user["user_data"]["username"], "password": "WrongPassword123!"}
        )
        time1 = time.time() - start1

        # Login with invalid username
        start2 = time.time()
        response2 = await client.post(
            "/auth/login", json={"username": "nonexistent_user_12345", "password": "WrongPassword123!"}
        )
        time2 = time.time() - start2

        # Both should return 401
        assert response1.status_code == 401
        assert response2.status_code == 401

        # Timing should be similar (within reasonable margin)
        # This is a soft check - exact timing is hard in tests
        time_diff = abs(time1 - time2)
        assert time_diff < 0.5  # Should be within 500ms

    # ==================== RATE LIMITING (Optional) ====================

    @pytest.mark.slow
    async def test_login_rate_limiting(self, client: AsyncClient, registered_user: dict):
        """Test rate limiting after multiple failed login attempts"""
        login_data = {"username": registered_user["user_data"]["username"], "password": "WrongPassword123!"}

        # Attempt multiple failed logins
        responses = []
        for _ in range(6):  # 6 failed attempts
            response = await client.post("/auth/login", json=login_data)
            responses.append(response)

        # After N attempts, should be rate limited (429) or still 401
        # Depends on if you implement rate limiting
        last_response = responses[-1]
        assert last_response.status_code in [401, 429]

    # ==================== TOKEN VERIFICATION ====================

    async def test_login_token_contains_user_claims(self, client: AsyncClient, registered_user: dict):
        """Test that token contains expected claims"""
        login_data = {
            "username": registered_user["user_data"]["username"],
            "password": registered_user["user_data"]["password"],
        }

        response = await client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Decode without verification (for testing purposes)
        try:
            from datetime import datetime

            import jwt

            payload = jwt.decode(token, options={"verify_signature": False})

            # Should have standard claims
            assert "sub" in payload or "user_id" in payload
            assert "exp" in payload  # Expiration time

            # Expiration should be in the future
            exp_timestamp = payload["exp"]
            assert exp_timestamp > datetime.utcnow().timestamp()

        except Exception as e:
            # If it's a PASETO token (not JWT), skip this test
            if token.startswith("v2.") or token.startswith("v4."):
                pytest.skip("Token is PASETO, not JWT - skipping JWT validation")
            else:
                # For JWT decode errors, fail with message
                pytest.fail(f"Failed to decode token: {str(e)}")

    async def test_login_multiple_users_different_tokens(self, client: AsyncClient, multiple_users_data: list):
        """Test that different users get different tokens"""
        # Register two users
        user1_data = multiple_users_data[0]
        user2_data = multiple_users_data[1]

        await client.post("/auth/register", json=user1_data)
        await client.post("/auth/register", json=user2_data)

        # Login both users
        response1 = await client.post(
            "/auth/login", json={"username": user1_data["username"], "password": user1_data["password"]}
        )

        response2 = await client.post(
            "/auth/login", json={"username": user2_data["username"], "password": user2_data["password"]}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Tokens should be different
        assert token1 != token2
