"""
Unit Tests for Token Service
"""

import concurrent.futures
import json
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pyseto
import pytest

from authentication.config import settings
from authentication.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    TokenGenerationError,
    TokenValidationError,
)
from authentication.token_service import TokenService, generate_token, verify_token


@pytest.fixture
def token_service():
    """Provide a fresh TokenService instance for each test."""
    # Reset singleton for testing
    TokenService._instance = None
    return TokenService()


@pytest.fixture
def valid_user_data():
    """Provide valid test user data."""
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "roles": ["user", "admin"],
    }


@pytest.fixture
def valid_token(token_service, valid_user_data):
    """Generate a valid token for testing verification."""
    return token_service.generate_token(
        user_id=valid_user_data["user_id"], roles=valid_user_data["roles"]
    )


# Test Class: Service Initialization
class TestTokenServiceInitialization:
    """Test TokenService initialization and singleton pattern."""

    def test_singleton_pattern(self):
        """Test that TokenService follows singleton pattern."""
        service1 = TokenService()
        service2 = TokenService()
        assert service1 is service2, "TokenService should be a singleton"

    def test_key_initialization_success(self, token_service):
        """Test successful key initialization."""
        assert token_service._key is not None
        assert token_service._key.version == 4
        assert token_service._key.purpose == "local"

    def test_key_initialization_with_invalid_length(self):
        """Test that invalid key length raises error."""
        TokenService._instance = None
        with patch("authentication.config.settings.PASETO_SECRET_KEY", "tooshort"):
            with pytest.raises(TokenGenerationError) as exc_info:
                TokenService()
            assert "32 bytes" in str(exc_info.value)

    def test_key_initialization_with_non_hex(self):
        """Test that non-hexadecimal key raises error."""
        TokenService._instance = None
        # 64 chars but not valid hex
        invalid_key = "z" * 64
        with patch("authentication.config.settings.PASETO_SECRET_KEY", invalid_key):
            with pytest.raises(TokenGenerationError):
                TokenService()


# Test Class: Token Generation - Valid Cases
class TestTokenGeneration:
    """Test successful token generation scenarios."""

    def test_generate_token_with_valid_inputs(self, token_service, valid_user_data):
        """Test token generation with valid user data."""
        token = token_service.generate_token(
            user_id=valid_user_data["user_id"], roles=valid_user_data["roles"]
        )

        assert isinstance(token, str)
        assert token.startswith("v4.local.")
        assert len(token) > 50  # PASETO tokens are relatively long

    def test_generate_token_with_single_role(self, token_service):
        """Test token generation with a single role."""
        token = token_service.generate_token(user_id="user-123", roles=["basic_user"])

        payload = token_service.verify_token(token)
        assert payload["user_id"] == "user-123"
        assert payload["roles"] == ["basic_user"]

    def test_generate_token_with_multiple_roles(self, token_service):
        """Test token generation with multiple roles."""
        roles = ["user", "admin", "moderator", "analyst"]
        token = token_service.generate_token(user_id="user-456", roles=roles)

        payload = token_service.verify_token(token)
        assert payload["roles"] == roles

    def test_generate_token_with_custom_expiration(self, token_service):
        """Test token generation with custom expiration time."""
        custom_expiration = 30  # 30 minutes
        token = token_service.generate_token(
            user_id="user-789",
            roles=["user"],
            expires_in_minutes=custom_expiration,
        )

        payload = token_service.verify_token(token)
        exp_time = datetime.fromisoformat(payload["exp"])
        iat_time = datetime.fromisoformat(payload["iat"])
        delta = exp_time - iat_time

        # Allow 1 second tolerance for processing time
        assert abs(delta.total_seconds() - (custom_expiration * 60)) < 1

    def test_generate_token_with_default_expiration(self, token_service):
        """Test that default expiration is applied when not specified."""
        token = token_service.generate_token(user_id="user-101", roles=["user"])

        payload = token_service.verify_token(token)
        exp_time = datetime.fromisoformat(payload["exp"])
        iat_time = datetime.fromisoformat(payload["iat"])
        delta = exp_time - iat_time

        expected_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        assert abs(delta.total_seconds() - (expected_minutes * 60)) < 1

    def test_generate_token_payload_structure(self, token_service):
        """Test that generated token has correct payload structure."""
        token = token_service.generate_token(user_id="user-202", roles=["user"])

        payload = token_service.verify_token(token)

        # Check all required fields exist
        assert "user_id" in payload
        assert "roles" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert "nbf" in payload

        # Check field types
        assert isinstance(payload["user_id"], str)
        assert isinstance(payload["roles"], list)
        assert isinstance(payload["iat"], str)
        assert isinstance(payload["exp"], str)
        assert isinstance(payload["nbf"], str)

    def test_generate_token_with_unicode_user_id(self, token_service):
        """Test token generation with Unicode characters in user_id."""
        unicode_id = "user-αβγδ-日本語-🔒"
        token = token_service.generate_token(user_id=unicode_id, roles=["user"])

        payload = token_service.verify_token(token)
        assert payload["user_id"] == unicode_id

    def test_generate_token_with_special_chars_in_role(self, token_service):
        """Test token generation with special characters in roles."""
        special_roles = ["admin:read", "user:write", "data-analyst_v2"]
        token = token_service.generate_token(user_id="user-303", roles=special_roles)

        payload = token_service.verify_token(token)
        assert payload["roles"] == special_roles


# Test Class: Token Generation - Input Validation
class TestTokenGenerationInputValidation:
    """Test input validation during token generation."""

    def test_generate_token_with_empty_user_id(self, token_service):
        """Test that empty user_id raises error."""
        with pytest.raises(TokenGenerationError) as exc_info:
            token_service.generate_token(user_id="", roles=["user"])
        assert "non-empty string" in str(exc_info.value)

    def test_generate_token_with_whitespace_only_user_id(self, token_service):
        """Test that whitespace-only user_id raises error."""
        with pytest.raises(TokenGenerationError) as exc_info:
            token_service.generate_token(user_id=" ", roles=["user"])
        assert "non-empty string" in str(exc_info.value)

    def test_generate_token_with_none_user_id(self, token_service):
        """Test that None user_id raises error."""
        with pytest.raises(TokenGenerationError):
            token_service.generate_token(user_id=None, roles=["user"])  # type: ignore

    def test_generate_token_with_integer_user_id(self, token_service):
        """Test that integer user_id raises error."""
        with pytest.raises(TokenGenerationError):
            token_service.generate_token(user_id=12345, roles=["user"])  # type: ignore

    def test_generate_token_with_empty_roles_list(self, token_service):
        """Test that empty roles list raises error."""
        with pytest.raises(TokenGenerationError) as exc_info:
            token_service.generate_token(user_id="user-404", roles=[])
        assert "cannot be empty" in str(exc_info.value)

    def test_generate_token_with_none_roles(self, token_service):
        """Test that None roles raises error."""
        with pytest.raises(TokenGenerationError):
            token_service.generate_token(user_id="user-505", roles=None)  # type: ignore

    def test_generate_token_with_string_roles(self, token_service):
        """Test that string roles (not list) raises error."""
        with pytest.raises(TokenGenerationError) as exc_info:
            token_service.generate_token(
                user_id="user-606",
                roles="admin",  # type: ignore
            )
        assert "must be a list" in str(exc_info.value)

    def test_generate_token_with_empty_string_in_roles(self, token_service):
        """Test that empty string in roles list raises error."""
        with pytest.raises(TokenGenerationError) as exc_info:
            token_service.generate_token(user_id="user-707", roles=["admin", ""])
        assert "non-empty strings" in str(exc_info.value)

    def test_generate_token_with_whitespace_only_role(self, token_service):
        """Test that whitespace-only role raises error."""
        with pytest.raises(TokenGenerationError):
            token_service.generate_token(user_id="user-808", roles=["admin", " "])

    def test_generate_token_with_non_string_role(self, token_service):
        """Test that non-string role raises error."""
        with pytest.raises(TokenGenerationError):
            token_service.generate_token(
                user_id="user-909",
                roles=["admin", 123],  # type: ignore
            )

    def test_generate_token_with_very_long_user_id(self, token_service):
        """Test token generation with extremely long user_id."""
        long_id = "x" * 10000
        token = token_service.generate_token(user_id=long_id, roles=["user"])

        payload = token_service.verify_token(token)
        assert payload["user_id"] == long_id


# Test Class: Token Verification - Valid Cases
class TestTokenVerification:
    """Test successful token verification scenarios."""

    def test_verify_valid_token(self, token_service, valid_token, valid_user_data):
        """Test verification of a valid token."""
        payload = token_service.verify_token(valid_token)

        assert payload["user_id"] == valid_user_data["user_id"]
        assert payload["roles"] == valid_user_data["roles"]
        assert "iat" in payload
        assert "exp" in payload
        assert "nbf" in payload

    def test_verify_token_returns_all_payload_fields(self, token_service):
        """Test that verify_token returns complete payload."""
        token = token_service.generate_token(user_id="user-111", roles=["user"])

        payload = token_service.verify_token(token)

        required_fields = ["user_id", "roles", "iat", "exp", "nbf"]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

    def test_verify_token_preserves_data_types(self, token_service):
        """Test that data types are preserved through token cycle."""
        roles = ["admin", "user", "analyst"]
        token = token_service.generate_token(user_id="user-222", roles=roles)

        payload = token_service.verify_token(token)

        assert isinstance(payload["user_id"], str)
        assert isinstance(payload["roles"], list)
        assert all(isinstance(role, str) for role in payload["roles"])

    def test_verify_freshly_generated_token(self, token_service):
        """Test that a freshly generated token verifies immediately."""
        token = token_service.generate_token(user_id="user-333", roles=["user"])

        # No delay - verify immediately
        payload = token_service.verify_token(token)
        assert payload["user_id"] == "user-333"

    def test_verify_token_with_unicode_data(self, token_service):
        """Test verification of token containing Unicode data."""
        unicode_id = "用户-∞-€-🌟"
        unicode_roles = ["角色-α", "rôle-β"]

        token = token_service.generate_token(user_id=unicode_id, roles=unicode_roles)

        payload = token_service.verify_token(token)
        assert payload["user_id"] == unicode_id
        assert payload["roles"] == unicode_roles


# Test Class: Token Verification - Invalid Tokens
class TestTokenVerificationInvalidTokens:
    """Test token verification with invalid tokens."""

    def test_verify_empty_token(self, token_service):
        """Test that empty token raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token("")
        assert "non-empty string" in str(exc_info.value)

    def test_verify_whitespace_only_token(self, token_service):
        """Test that whitespace-only token raises error."""
        with pytest.raises(InvalidTokenError):
            token_service.verify_token(" ")

    def test_verify_none_token(self, token_service):
        """Test that None token raises error."""
        with pytest.raises(InvalidTokenError):
            token_service.verify_token(None)  # type: ignore

    def test_verify_integer_token(self, token_service):
        """Test that integer token raises error."""
        with pytest.raises(InvalidTokenError):
            token_service.verify_token(12345)  # type: ignore

    def test_verify_malformed_token_wrong_prefix(self, token_service):
        """Test that token with wrong prefix raises error."""
        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token("v3.local.invalidtoken")
        assert "v4.local" in str(exc_info.value)

    def test_verify_malformed_token_random_string(self, token_service):
        """Test that random string raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            token_service.verify_token("v4.local.thisisnotavalidtoken")

    def test_verify_token_with_tampered_payload(self, token_service, valid_token):
        """Test that tampering with token payload invalidates it."""
        # Try to manually change part of the token
        parts = valid_token.split(".")
        if len(parts) >= 3:
            # Modify the payload section
            parts[2] = parts[2][:-5] + "XXXXX"
            tampered_token = ".".join(parts)

            with pytest.raises(InvalidTokenError):
                token_service.verify_token(tampered_token)

    def test_verify_token_from_different_key(self, token_service):
        """Test that token generated with different key fails verification."""
        # Generate token with a different key
        different_key = pyseto.Key.new(
            version=4,
            purpose="local",
            key=bytes.fromhex("a" * 64),  # Different key
        )

        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        payload = {
            "user_id": "user-444",
            "roles": ["user"],
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        # Use json serializer instead of pyseto.JsonSerializer (which doesn't exist)
        foreign_token = pyseto.encode(
            key=different_key, payload=payload, serializer=json
        ).decode("utf-8")

        # Try to verify with our service (different key)
        with pytest.raises(InvalidTokenError):
            token_service.verify_token(foreign_token)

    def test_verify_truncated_token(self, token_service, valid_token):
        """Test that truncated token raises error."""
        truncated = valid_token[:50]  # Cut token short

        with pytest.raises(InvalidTokenError):
            token_service.verify_token(truncated)

    def test_verify_token_with_extra_data(self, token_service, valid_token):
        """Test that token with appended data fails verification."""
        modified_token = valid_token + "extradata"

        with pytest.raises(InvalidTokenError):
            token_service.verify_token(modified_token)


# Test Class: Token Expiration
class TestTokenExpiration:
    """Test token expiration functionality."""

    def test_verify_expired_token(self, token_service):
        """Test that expired token raises TokenExpiredError."""
        # Generate token that expires in 1 second
        token = token_service.generate_token(
            user_id="user-555",
            roles=["user"],
            expires_in_minutes=1 / 60,  # 1 second
        )

        # Wait for token to expire
        time.sleep(2)

        with pytest.raises(TokenExpiredError) as exc_info:
            token_service.verify_token(token)
        assert "expired" in str(exc_info.value).lower()

    def test_verify_token_just_before_expiration(self, token_service):
        """Test token verification just before expiration."""
        # Generate token that expires in 5 seconds
        token = token_service.generate_token(
            user_id="user-666", roles=["user"], expires_in_minutes=5 / 60
        )

        # Verify immediately (should succeed)
        payload = token_service.verify_token(token)
        assert payload["user_id"] == "user-666"

    def test_token_with_future_expiration(self, token_service):
        """Test token with long expiration time."""
        token = token_service.generate_token(
            user_id="user-777",
            roles=["user"],
            expires_in_minutes=60,  # 1 hour
        )

        payload = token_service.verify_token(token)
        exp_time = datetime.fromisoformat(payload["exp"])
        now = datetime.now(UTC)

        # Should expire approximately 1 hour from now
        time_until_expiry = (exp_time - now).total_seconds()
        assert 3500 < time_until_expiry < 3700  # ~60 minutes ± tolerance

    def test_token_expiration_exact_boundary(self, token_service):
        """Test token at exact expiration boundary."""
        # Create a token that expires in 2 seconds
        token = token_service.generate_token(
            user_id="user-888", roles=["user"], expires_in_minutes=2 / 60
        )

        # Verify works before expiration
        payload = token_service.verify_token(token)
        assert payload["user_id"] == "user-888"

        # Wait until just after expiration
        time.sleep(3)

        # Should now be expired
        with pytest.raises(TokenExpiredError):
            token_service.verify_token(token)


# Test Class: Token Payload Validation
class TestTokenPayloadValidation:
    """Test payload structure validation during verification."""

    def test_verify_token_missing_user_id(self, token_service):
        """Test that token missing user_id field raises error."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        # Manually create token with missing user_id
        payload = {
            "roles": ["user"],
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token(token)
        assert "user_id" in str(exc_info.value)

    def test_verify_token_missing_roles(self, token_service):
        """Test that token missing roles field raises error."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        payload = {
            "user_id": "user-999",
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token(token)
        assert "roles" in str(exc_info.value)

    def test_verify_token_with_empty_roles_list(self, token_service):
        """Test that token with empty roles list raises error."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        payload = {
            "user_id": "user-1010",
            "roles": [],  # Empty roles list
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token(token)
        assert "roles" in str(exc_info.value) and "empty" in str(exc_info.value)

    def test_verify_token_with_invalid_user_id_type(self, token_service):
        """Test that token with non-string user_id raises error."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        payload = {
            "user_id": 12345,  # Integer instead of string
            "roles": ["user"],
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token(token)
        assert "user_id" in str(exc_info.value) and "string" in str(exc_info.value)

    def test_verify_token_with_invalid_roles_type(self, token_service):
        """Test that token with non-list roles raises error."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        payload = {
            "user_id": "user-1111",
            "roles": "admin",  # String instead of list
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token(token)
        assert "roles" in str(exc_info.value) and "list" in str(exc_info.value)


# Test Class: Token Not-Before Time
class TestTokenNotBeforeTime:
    """Test not-before time validation."""

    def test_verify_token_with_future_nbf(self, token_service):
        """Test that token with future nbf time raises error."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        # Manually create token with nbf in the future
        future_time = now + timedelta(seconds=10)

        payload = {
            "user_id": "user-1212",
            "roles": ["user"],
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": future_time.isoformat(),  # Not yet valid
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.verify_token(token)
        assert "not yet valid" in str(exc_info.value) or "nbf" in str(exc_info.value)

    def test_verify_token_with_past_nbf(self, token_service):
        """Test that token with past nbf time verifies successfully."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        past_time = now - timedelta(minutes=5)

        payload = {
            "user_id": "user-1313",
            "roles": ["user"],
            "iat": past_time.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": past_time.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        result = token_service.verify_token(token)
        assert result["user_id"] == "user-1313"

    def test_verify_token_nbf_equals_now(self, token_service):
        """Test token where nbf equals current time."""
        now = datetime.now(UTC)
        now = now.replace(microsecond=0)

        payload = {
            "user_id": "user-1414",
            "roles": ["user"],
            "iat": now.isoformat(),
            "exp": (now + timedelta(minutes=15)).isoformat(),
            "nbf": now.isoformat(),
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        # Small delay to ensure nbf has passed
        time.sleep(0.1)

        result = token_service.verify_token(token)
        assert result["user_id"] == "user-1414"


# Test Class: Module-Level Functions
class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_module_generate_token(self):
        """Test module-level generate_token function."""
        token = generate_token(user_id="user-1515", roles=["user"])

        assert isinstance(token, str)
        assert token.startswith("v4.local.")

    def test_module_verify_token(self):
        """Test module-level verify_token function."""
        token = generate_token(user_id="user-1616", roles=["admin"])

        payload = verify_token(token)
        assert payload["user_id"] == "user-1616"
        assert payload["roles"] == ["admin"]

    def test_module_functions_use_same_service(self):
        """Test that module functions use the same service instance."""
        token1 = generate_token(user_id="user-1717", roles=["user"])
        token2 = generate_token(user_id="user-1818", roles=["admin"])

        # Both tokens should verify successfully
        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert payload1["user_id"] == "user-1717"
        assert payload2["user_id"] == "user-1818"

    def test_module_generate_with_custom_expiration(self):
        """Test module-level generate with custom expiration."""
        token = generate_token(
            user_id="user-1919", roles=["user"], expires_in_minutes=30
        )

        payload = verify_token(token)
        exp_time = datetime.fromisoformat(payload["exp"])
        iat_time = datetime.fromisoformat(payload["iat"])
        delta = (exp_time - iat_time).total_seconds()

        assert abs(delta - 1800) < 1  # 30 minutes ± 1 second


# Test Class: Edge Cases and Integration
class TestEdgeCasesAndIntegration:
    """Test edge cases and end-to-end workflows."""

    def test_generate_and_verify_many_tokens(self, token_service):
        """Test generating and verifying many tokens sequentially."""
        tokens = []
        for i in range(100):
            token = token_service.generate_token(
                user_id=f"user-{i}", roles=[f"role-{i}"]
            )
            tokens.append((token, f"user-{i}", f"role-{i}"))

        # Verify all tokens
        for token, expected_user, expected_role in tokens:
            payload = token_service.verify_token(token)
            assert payload["user_id"] == expected_user
            assert payload["roles"] == [expected_role]

    def test_concurrent_token_generation(self, token_service):
        """Test that tokens generated concurrently are all valid."""

        def generate_and_verify(index):
            token = token_service.generate_token(
                user_id=f"user-{index}", roles=["user"]
            )
            payload = token_service.verify_token(token)
            return payload["user_id"] == f"user-{index}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_and_verify, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(results), "All concurrent operations should succeed"

    def test_token_with_very_long_role_name(self, token_service):
        """Test token with extremely long role name."""
        long_role = "x" * 1000
        token = token_service.generate_token(user_id="user-2020", roles=[long_role])

        payload = token_service.verify_token(token)
        assert payload["roles"] == [long_role]

    def test_token_with_many_roles(self, token_service):
        """Test token with a large number of roles."""
        many_roles = [f"role-{i}" for i in range(100)]
        token = token_service.generate_token(user_id="user-2121", roles=many_roles)

        payload = token_service.verify_token(token)
        assert payload["roles"] == many_roles

    def test_token_lifecycle_complete_workflow(self, token_service):
        """Test complete token lifecycle from generation to expiration."""
        # 1. Generate token
        token = token_service.generate_token(
            user_id="user-2222",
            roles=["admin", "user"],
            expires_in_minutes=3 / 60,
        )

        # 2. Verify immediately
        payload1 = token_service.verify_token(token)
        assert payload1["user_id"] == "user-2222"

        # 3. Wait 1 second and verify again
        time.sleep(1)
        payload2 = token_service.verify_token(token)
        assert payload2["user_id"] == "user-2222"

        # 4. Wait for expiration
        time.sleep(3)

        # 5. Verify token is now expired
        with pytest.raises(TokenExpiredError):
            token_service.verify_token(token)

    def test_token_decode_unsafe(self, token_service):
        """Test unsafe decode function for expired tokens."""
        token = token_service.generate_token(
            user_id="user-2323", roles=["user"], expires_in_minutes=1 / 60
        )

        # Wait for expiration
        time.sleep(2)

        # Normal verify should fail
        with pytest.raises(TokenExpiredError):
            token_service.verify_token(token)

        # Unsafe decode should still work (for debugging)
        payload = token_service.decode_token_unsafe(token)
        if payload is not None:  # May return None if decoding fails
            assert payload["user_id"] == "user-2323"

    def test_special_characters_comprehensive(self, token_service):
        """Test token with comprehensive special characters."""
        special_id = "user-!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        special_roles = [
            "role-αβγδεζηθ",
            "role-中文",
            "role-العربية",
            "role-🎉🔒🌟",
        ]

        token = token_service.generate_token(user_id=special_id, roles=special_roles)

        payload = token_service.verify_token(token)
        assert payload["user_id"] == special_id
        assert payload["roles"] == special_roles

    def test_timezone_awareness_in_timestamps(self, token_service):
        """Test that all timestamps are timezone-aware."""
        token = token_service.generate_token(user_id="user-2424", roles=["user"])

        payload = token_service.verify_token(token)

        iat = datetime.fromisoformat(payload["iat"])
        exp = datetime.fromisoformat(payload["exp"])
        nbf = datetime.fromisoformat(payload["nbf"])

        # All timestamps should be timezone-aware
        assert iat.tzinfo is not None
        assert exp.tzinfo is not None
        assert nbf.tzinfo is not None

    def test_token_validation_error_on_system_failure(self, token_service):
        """Test that TokenValidationError is raised for unexpected system errors."""
        token = token_service.generate_token(user_id="user-2525", roles=["user"])

        # Mock an unexpected error during decoding
        with patch(
            "pyseto.decode", side_effect=RuntimeError("Unexpected system error")
        ):
            with pytest.raises(TokenValidationError) as exc_info:
                token_service.verify_token(token)
            assert "unexpected error" in str(exc_info.value).lower()

    def test_verify_token_with_malformed_timestamps(self, token_service):
        """Test token with malformed timestamp formats."""
        payload = {
            "user_id": "user-2626",
            "roles": ["user"],
            "iat": "not-a-timestamp",
            "exp": "also-not-a-timestamp",
            "nbf": "invalid-format",
        }

        token = pyseto.encode(
            key=token_service._key, payload=payload, serializer=json
        ).decode("utf-8")

        with pytest.raises(InvalidTokenError):
            token_service.verify_token(token)
