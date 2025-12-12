"""
Comprehensive Test Suite for RBAC Decorators

REFACTORED VERSION - Updated for case-insensitive role matching

Tests cover:
- Authentication enforcement (token presence, validity, expiration)
- Authorization enforcement (role-based access control)
- Error handling and security edge cases
- Integration with FastAPI dependency injection
- Request state management
- Case-insensitive role matching
- Single role as string parameter support
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from src.authentication.decorators import (
    AuthenticationRequired,
    get_current_user,
    normalize_roles,
    token_required,
)
from src.authentication.exceptions import (
    InvalidTokenError,
    TokenError,
    TokenExpiredError,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def app():
    """Create a minimal FastAPI app for testing."""
    return FastAPI()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def valid_token_payload():
    """Sample valid token payload."""
    now = datetime.now(UTC)
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "roles": ["admin", "user"],
        "iat": now.isoformat(),
        "exp": (now + timedelta(hours=1)).isoformat(),
        "nbf": now.isoformat(),
    }


@pytest.fixture
def mechanic_token_payload():
    """Sample token payload for mechanic role."""
    now = datetime.now(UTC)
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174001",
        "roles": ["mecanico"],
        "iat": now.isoformat(),
        "exp": (now + timedelta(hours=1)).isoformat(),
        "nbf": now.isoformat(),
    }


@pytest.fixture
def mixed_case_token_payload():
    """Sample token payload with mixed case roles."""
    now = datetime.now(UTC)
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174002",
        "roles": ["Admin", "Manager"],  # Mixed case
        "iat": now.isoformat(),
        "exp": (now + timedelta(hours=1)).isoformat(),
        "nbf": now.isoformat(),
    }


# ============================================================================
# Unit Tests: normalize_roles Utility Function
# ============================================================================


class TestNormalizeRoles:
    """Test the normalize_roles utility function."""

    def test_normalize_lowercase_roles(self):
        """Test normalization of already lowercase roles."""
        roles = ["admin", "user", "manager"]
        result = normalize_roles(roles)
        assert result == ["admin", "user", "manager"]

    def test_normalize_uppercase_roles(self):
        """Test normalization of uppercase roles."""
        roles = ["ADMIN", "USER", "MANAGER"]
        result = normalize_roles(roles)
        assert result == ["admin", "user", "manager"]

    def test_normalize_mixed_case_roles(self):
        """Test normalization of mixed case roles."""
        roles = ["Admin", "UsEr", "MANAGER"]
        result = normalize_roles(roles)
        assert result == ["admin", "user", "manager"]

    def test_normalize_empty_list(self):
        """Test normalization of empty list."""
        roles = []
        result = normalize_roles(roles)
        assert result == []

    def test_normalize_filters_non_strings(self):
        """Test that non-string values are filtered out."""
        roles = ["admin", 123, None, "user", True]
        result = normalize_roles(roles)
        assert result == ["admin", "user"]


# ============================================================================
# Unit Tests: AuthenticationRequired Class
# ============================================================================


class TestAuthenticationRequired:
    """Test the AuthenticationRequired dependency class."""

    def test_initialization_without_roles(self):
        """Test initialization without role requirements."""
        auth = AuthenticationRequired()
        assert auth.required_roles == []

    def test_initialization_with_roles_list(self):
        """Test initialization with role requirements as list."""
        auth = AuthenticationRequired(required_roles=["admin", "manager"])
        assert auth.required_roles == ["admin", "manager"]

    def test_initialization_with_single_role_string(self):
        """Test initialization with single role as string."""
        auth = AuthenticationRequired(required_roles="admin")
        assert auth.required_roles == ["admin"]

    def test_initialization_normalizes_roles_to_lowercase(self):
        """Test that roles are normalized to lowercase on init."""
        auth = AuthenticationRequired(required_roles=["Admin", "MANAGER"])
        assert auth.required_roles == ["admin", "manager"]

    def test_initialization_with_invalid_type_raises_error(self):
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError) as exc_info:
            AuthenticationRequired(required_roles=123)
        assert "must be a string, list" in str(exc_info.value)

    def test_initialization_with_non_string_in_list_raises_error(self):
        """Test that non-strings in list raise TypeError."""
        with pytest.raises(TypeError) as exc_info:
            AuthenticationRequired(required_roles=["admin", 123, "user"])
        assert "All roles must be strings" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_credentials(self):
        """Test authentication failure when Bearer token is missing."""
        auth = AuthenticationRequired()
        request = Mock(spec=Request)

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=None)

        assert exc_info.value.status_code == 401
        assert "Missing authentication credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_valid_token_authentication(self, mock_verify, valid_token_payload):
        """Test successful authentication with valid token."""
        mock_verify.return_value = valid_token_payload
        auth = AuthenticationRequired()
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token_string"

        result = await auth(request=request, credentials=credentials)

        assert result == valid_token_payload
        assert request.state.user == valid_token_payload
        mock_verify.assert_called_once_with("valid_token_string")

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_expired_token(self, mock_verify):
        """Test authentication failure with expired token."""
        mock_verify.side_effect = TokenExpiredError("Token has expired")
        auth = AuthenticationRequired()
        request = Mock(spec=Request)
        credentials = Mock()
        credentials.credentials = "expired_token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_invalid_token(self, mock_verify):
        """Test authentication failure with invalid token."""
        mock_verify.side_effect = InvalidTokenError("Invalid token format")
        auth = AuthenticationRequired()
        request = Mock(spec=Request)
        credentials = Mock()
        credentials.credentials = "invalid_token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_authorization_success_with_matching_role(
        self,
        mock_verify,
        valid_token_payload,
    ):
        """Test successful authorization when user has required role."""
        mock_verify.return_value = valid_token_payload  # Has "admin" role
        auth = AuthenticationRequired(required_roles=["admin"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        result = await auth(request=request, credentials=credentials)

        assert result == valid_token_payload

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_authorization_success_with_one_of_multiple_roles(
        self,
        mock_verify,
        valid_token_payload,
    ):
        """Test authorization success when user has one of multiple required roles."""
        mock_verify.return_value = valid_token_payload
        # Require admin OR manager (user has admin)
        auth = AuthenticationRequired(required_roles=["admin", "manager", "owner"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        result = await auth(request=request, credentials=credentials)

        assert result == valid_token_payload

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_authorization_failure_insufficient_permissions(
        self,
        mock_verify,
        mechanic_token_payload,
    ):
        """Test authorization failure when user lacks required role."""
        mock_verify.return_value = mechanic_token_payload
        # Require admin or gerente (user only has mecanico)
        auth = AuthenticationRequired(required_roles=["admin", "gerente"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_case_insensitive_role_matching(
        self,
        mock_verify,
        valid_token_payload,
    ):
        """Test that role matching is case-insensitive."""
        mock_verify.return_value = valid_token_payload  # Has "admin" role
        # Require ADMIN role (uppercase) - should match "admin" (lowercase)
        auth = AuthenticationRequired(required_roles=["ADMIN"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        result = await auth(request=request, credentials=credentials)

        assert result == valid_token_payload  # Should succeed

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_mixed_case_roles_in_token(
        self,
        mock_verify,
        mixed_case_token_payload,
    ):
        """Test authorization with mixed case roles in token."""
        mock_verify.return_value = mixed_case_token_payload  # Has ["Admin", "Manager"]
        # Require lowercase "admin" - should match "Admin" from token
        auth = AuthenticationRequired(required_roles=["admin"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        result = await auth(request=request, credentials=credentials)

        assert result == mixed_case_token_payload  # Should succeed

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_token_missing_roles_claim(self, mock_verify):
        """Test that missing roles claim returns 500 (not 403)."""
        # Token missing 'roles' key entirely
        payload = {
            "user_id": "test_user",
            "iat": datetime.now(UTC).isoformat(),
            "exp": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        mock_verify.return_value = payload
        auth = AuthenticationRequired(required_roles=["admin"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        # Should return 500 (configuration error), not 403 (authorization)
        assert exc_info.value.status_code == 500
        assert "missing required claims" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_token_with_non_list_roles(self, mock_verify):
        """Test that non-list roles value returns 500."""
        # Token has roles as string instead of list
        payload = {
            "user_id": "test_user",
            "roles": "admin",  # Should be ["admin"]
            "iat": datetime.now(UTC).isoformat(),
            "exp": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        mock_verify.return_value = payload
        auth = AuthenticationRequired(required_roles=["admin"])
        request = Mock(spec=Request)
        request.state = Mock()
        credentials = Mock()
        credentials.credentials = "valid_token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        assert exc_info.value.status_code == 500
        assert "invalid format" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_generic_token_error(self, mock_verify):
        """Test handling of generic token errors."""
        mock_verify.side_effect = TokenError("Generic token error")
        auth = AuthenticationRequired()
        request = Mock(spec=Request)
        credentials = Mock()
        credentials.credentials = "problematic_token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_unexpected_exception_handling(self, mock_verify):
        """Test handling of unexpected exceptions during verification."""
        mock_verify.side_effect = RuntimeError("Unexpected error")
        auth = AuthenticationRequired()
        request = Mock(spec=Request)
        credentials = Mock()
        credentials.credentials = "token"

        with pytest.raises(Exception) as exc_info:
            await auth(request=request, credentials=credentials)

        assert exc_info.value.status_code == 500
        assert "Internal authentication error" in exc_info.value.detail


# ============================================================================
# Unit Tests: token_required Factory Function
# ============================================================================


class TestTokenRequiredFactory:
    """Test the token_required decorator factory function."""

    def test_token_required_without_roles(self):
        """Test token_required returns AuthenticationRequired without roles."""
        dependency = token_required()
        assert isinstance(dependency, AuthenticationRequired)
        assert dependency.required_roles == []

    def test_token_required_with_roles_list(self):
        """Test token_required returns AuthenticationRequired with roles."""
        dependency = token_required(roles=["admin", "manager"])
        assert isinstance(dependency, AuthenticationRequired)
        assert dependency.required_roles == ["admin", "manager"]

    def test_token_required_with_single_role_string(self):
        """Test token_required accepts single role as string."""
        dependency = token_required(roles="admin")
        assert isinstance(dependency, AuthenticationRequired)
        assert dependency.required_roles == ["admin"]

    def test_token_required_with_empty_roles_list(self):
        """Test token_required with empty roles list."""
        dependency = token_required(roles=[])
        assert isinstance(dependency, AuthenticationRequired)
        assert dependency.required_roles == []

    def test_token_required_normalizes_roles(self):
        """Test that token_required normalizes roles to lowercase."""
        dependency = token_required(roles=["Admin", "MANAGER"])
        assert isinstance(dependency, AuthenticationRequired)
        assert dependency.required_roles == ["admin", "manager"]


# ============================================================================
# Integration Tests: FastAPI Routes
# ============================================================================


class TestFastAPIIntegration:
    """Test decorator integration with FastAPI routes."""

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_protected_route_with_valid_token(
        self,
        mock_verify,
        app,
        client,
        valid_token_payload,
    ):
        """Test accessing protected route with valid authentication."""
        mock_verify.return_value = valid_token_payload

        @app.get("/protected")
        async def protected_endpoint(user: dict = Depends(token_required())):
            return {"message": "Access granted", "user_id": user["user_id"]}

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer valid_token_string"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"
        assert response.json()["user_id"] == valid_token_payload["user_id"]

    @pytest.mark.asyncio
    async def test_protected_route_without_token(self, app, client):
        """Test accessing protected route without token returns 401."""

        @app.get("/protected")
        async def protected_endpoint(user: dict = Depends(token_required())):
            return {"message": "Access granted"}

        response = client.get("/protected")

        assert response.status_code == 401
        assert "Missing authentication credentials" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_role_protected_route_with_authorized_user(
        self,
        mock_verify,
        app,
        client,
        valid_token_payload,
    ):
        """Test role-protected route with authorized user."""
        mock_verify.return_value = valid_token_payload

        @app.post("/admin/action")
        async def admin_action(
            user: dict = Depends(token_required(roles=["admin"])),
        ):
            return {"message": "Admin action performed"}

        response = client.post(
            "/admin/action",
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Admin action performed"

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_role_protected_route_with_unauthorized_user(
        self,
        mock_verify,
        app,
        client,
        mechanic_token_payload,
    ):
        """Test role-protected route with unauthorized user returns 403."""
        mock_verify.return_value = mechanic_token_payload

        @app.post("/admin/action")
        async def admin_action(
            user: dict = Depends(token_required(roles=["admin", "gerente"])),
        ):
            return {"message": "Admin action performed"}

        response = client.post(
            "/admin/action",
            headers={"Authorization": "Bearer mechanic_token"},
        )

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_single_role_as_string_parameter(
        self,
        mock_verify,
        app,
        client,
        valid_token_payload,
    ):
        """Test using single role as string (not list)."""
        mock_verify.return_value = valid_token_payload

        @app.get("/admin-only")
        async def admin_only(
            user: dict = Depends(token_required(roles="admin")),
        ):  # String, not list
            return {"message": "Admin access granted"}

        response = client.get(
            "/admin-only",
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Admin access granted"

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_case_insensitive_route_protection(
        self,
        mock_verify,
        app,
        client,
        valid_token_payload,
    ):
        """Test that route protection is case-insensitive."""
        mock_verify.return_value = valid_token_payload  # Has "admin" role

        @app.get("/protected")
        async def protected_endpoint(
            user: dict = Depends(token_required(roles=["ADMIN"])),  # Uppercase
        ):
            return {"message": "Access granted"}

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer token"},
        )

        # Should SUCCEED because "admin" matches "ADMIN" (case-insensitive)
        assert response.status_code == 200
        assert response.json()["message"] == "Access granted"

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_get_current_user_from_request_state(
        self,
        mock_verify,
        app,
        client,
        valid_token_payload,
    ):
        """Test retrieving current user from request state."""
        mock_verify.return_value = valid_token_payload

        @app.get("/me")
        async def get_me(
            request: Request,
            user: dict = Depends(token_required()),
        ):
            user_from_state = get_current_user(request)
            return {
                "from_param": user["user_id"],
                "from_state": user_from_state["user_id"],
            }

        response = client.get(
            "/me",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["from_param"] == valid_token_payload["user_id"]
        assert data["from_state"] == valid_token_payload["user_id"]


# ============================================================================
# Security Edge Case Tests
# ============================================================================


class TestSecurityEdgeCases:
    """Test security-focused edge cases and attack scenarios."""

    @pytest.mark.asyncio
    async def test_malformed_authorization_header(self, app, client):
        """Test rejection of malformed Authorization header."""

        @app.get("/protected")
        async def protected_endpoint(user: dict = Depends(token_required())):
            return {"message": "Access granted"}

        # Missing "Bearer" prefix
        response = client.get(
            "/protected",
            headers={"Authorization": "invalid_token_string"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_empty_roles_in_token_payload(
        self,
        mock_verify,
        app,
        client,
    ):
        """Test handling of token with empty roles list."""
        now = datetime.now(UTC)
        payload = {
            "user_id": "test_user",
            "roles": [],  # Empty roles
            "iat": now.isoformat(),
            "exp": (now + timedelta(hours=1)).isoformat(),
            "nbf": now.isoformat(),
        }
        mock_verify.return_value = payload

        @app.get("/protected")
        async def protected_endpoint(
            user: dict = Depends(token_required(roles=["admin"])),
        ):
            return {"message": "Access granted"}

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_various_case_combinations(
        self,
        mock_verify,
        app,
        client,
    ):
        """Test various case combinations for role matching."""
        now = datetime.now(UTC)

        # Test cases: (token_roles, required_roles, should_succeed)
        test_cases = [
            (["admin"], ["admin"], True),
            (["admin"], ["ADMIN"], True),
            (["ADMIN"], ["admin"], True),
            (["Admin"], ["admin"], True),
            (["admin"], ["Admin"], True),
            (["AdMiN"], ["aDmIn"], True),
            (["user"], ["admin"], False),
            (["USER"], ["admin"], False),
        ]

        for token_roles, required_roles, should_succeed in test_cases:
            payload = {
                "user_id": "test_user",
                "roles": token_roles,
                "iat": now.isoformat(),
                "exp": (now + timedelta(hours=1)).isoformat(),
                "nbf": now.isoformat(),
            }
            mock_verify.return_value = payload

            app_test = FastAPI()

            @app_test.get("/test")
            async def test_endpoint(
                user: dict = Depends(token_required(roles=required_roles)),
            ):
                return {"success": True}

            client_test = TestClient(app_test)
            response = client_test.get(
                "/test",
                headers={"Authorization": "Bearer token"},
            )

            msg_ok = f"Failed: token_roles={token_roles}, required={required_roles}"
            msg_fail = f"Should have failed: token_roles={token_roles}, required={required_roles}"

            if should_succeed:
                assert response.status_code == 200, msg_ok
            else:
                assert response.status_code == 403, msg_fail

    @pytest.mark.asyncio
    @patch("src.authentication.decorators.verify_token")
    async def test_special_characters_in_roles(
        self,
        mock_verify,
        app,
        client,
    ):
        """Test handling of special characters in role names."""
        now = datetime.now(UTC)
        payload = {
            "user_id": "test_user",
            "roles": ["super-admin", "level_1"],
            "iat": now.isoformat(),
            "exp": (now + timedelta(hours=1)).isoformat(),
            "nbf": now.isoformat(),
        }
        mock_verify.return_value = payload

        @app.get("/protected")
        async def protected_endpoint(
            user: dict = Depends(token_required(roles=["super-admin"])),
        ):
            return {"message": "Access granted"}

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200


# ============================================================================
# Edge Case: get_current_user Function
# ============================================================================


class TestGetCurrentUser:
    """Test the get_current_user helper function."""

    def test_get_current_user_without_authentication(self):
        """Test that get_current_user raises error without auth."""
        request = Mock(spec=Request)
        request.state = Mock(spec=[])  # No 'user' attribute

        with pytest.raises(AttributeError) as exc_info:
            get_current_user(request)

        assert "User not found in request state" in str(exc_info.value)

    def test_get_current_user_with_authentication(self):
        """Test successful retrieval of current user."""
        user_payload = {"user_id": "123", "roles": ["admin"]}
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = user_payload

        result = get_current_user(request)

        assert result == user_payload
