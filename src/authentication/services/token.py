"""
Paseto Token Generation and Validation Service
v4.local (symmetric encryption with XChaCha20-Poly1305)
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pyseto
from pyseto import DecryptError, VerifyError

from src.authentication.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    TokenGenerationError,
    TokenValidationError,
)
from src.config import settings

logger = logging.getLogger(__name__)


class TokenService:
    """
    Service class for PASETO token generation and validation operations.
    Uses PASETO v4.local with XChaCha20-Poly1305 for symmetric encryption.

    Attributes:
        _key: PASETO symmetric key for v4.local tokens
        _instance: Singleton instance
    """

    _instance = None

    def __new__(cls):
        """
        Implement singleton pattern to ensure single TokenService instance.

        Returns:
            TokenService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_key()
        return cls._instance

    def _initialize_key(self) -> None:
        """
        Initialize the PASETO symmetric key from configuration.

        The key must be a 32-byte (256-bit) key for v4.local tokens.
        Validates key length and format before creation.

        Raises:
            TokenGenerationError: If key initialization fails
        """
        try:
            key_material = settings.auth.PASETO_SECRET_KEY

            # Validate key length (must be 32 bytes for v4.local)
            if len(key_material) != 64:  # 32 bytes = 64 hex characters
                raise ValueError(
                    "PASETO_SECRET_KEY must be exactly 32 bytes (64 hex characters)"
                )

            # Create the symmetric key for v4.local
            self._key = pyseto.Key.new(
                version=4, purpose="local", key=bytes.fromhex(key_material)
            )

            logger.info("TokenService initialized with PASETO v4.local key")

        except ValueError as e:
            logger.error(f"Invalid PASETO key configuration: {str(e)}")
            raise TokenGenerationError(str(e), original_error=e)

        except Exception as e:
            logger.error(f"Failed to initialize TokenService: {str(e)}")
            raise TokenGenerationError(
                "Failed to initialize token service", original_error=e
            )

    def _validate_token_inputs(self, user_id: str, roles: list[str]) -> None:
        """
        Validate inputs for token generation.

        Args:
            user_id: The user identifier
            roles: List of role names

        Raises:
            TokenGenerationError: If inputs are invalid
        """
        if not isinstance(user_id, str) or not user_id.strip():
            raise TokenGenerationError("user_id must be a non-empty string")

        if not isinstance(roles, list):
            raise TokenGenerationError("roles must be a list")

        if not roles:
            raise TokenGenerationError("roles list cannot be empty")

        if not all(isinstance(role, str) and role.strip() for role in roles):
            raise TokenGenerationError("all roles must be non-empty strings")

    def generate_token(
        self,
        user_id: str,
        roles: list[str],
        expires_in_minutes: int | None = None,
    ) -> str:
        """
        Generate a PASETO v4.local token with user data.

        The token includes:
        - user_id: Unique identifier for the user
        - roles: List of role names for authorization
        - iat: Issued at timestamp (second precision)
        - exp: Expiration timestamp (second precision)
        - nbf: Not before timestamp (second precision)

        Args:
            user_id: The user's unique identifier (UUID string)
            roles: List of role names assigned to the user
            expires_in_minutes: Token validity period (default from settings)

        Returns:
            str: The encoded PASETO token

        Raises:
            TokenGenerationError: If token generation fails
        """
        # Validate inputs
        self._validate_token_inputs(user_id, roles)

        # Use configured expiration or default
        if expires_in_minutes is None:
            expires_in_minutes = settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES

        try:
            # Calculate timestamps with second-level precision
            now = datetime.now(UTC)
            now = now.replace(microsecond=0)
            expiration = now + timedelta(minutes=expires_in_minutes)

            # Build token payload
            payload = {
                "user_id": user_id,
                "roles": roles,
                "iat": now.isoformat(),
                "exp": expiration.isoformat(),
                "nbf": now.isoformat(),
            }

            # Encode the token
            token = pyseto.encode(
                key=self._key,
                payload=payload,
                serializer=json,
            )

            logger.debug(f"Token generated successfully for user_id: {user_id}")
            return token.decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to generate token: {str(e)}")
            raise TokenGenerationError(
                "An error occurred while generating the token", original_error=e
            )

    def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify and decode a PASETO token.

        This method validates the token's signature, checks expiration,
        verifies not-before time, and returns the decoded payload.

        Args:
            token: The PASETO token string to verify

        Returns:
            dict: The decoded token payload containing user_id, roles, timestamps

        Raises:
            InvalidTokenError: If token format is invalid
            TokenExpiredError: If token has expired
            TokenValidationError: If token verification fails
        """
        # Validate input
        if not isinstance(token, str) or not token.strip():
            raise InvalidTokenError("Token must be a non-empty string")

        # PASETO tokens should start with 'v4.local.'
        if not token.startswith("v4.local."):
            raise InvalidTokenError("Invalid token format - must be PASETO v4.local")

        try:
            # Decode and verify the token
            decoded = pyseto.decode(
                keys=self._key,
                token=token.encode("utf-8"),
                deserializer=json,
            )

            payload = cast(dict[str, Any], decoded.payload)

            # Validate required fields
            self._validate_payload_structure(payload)

            # Check expiration
            self._check_token_expiration(payload)

            # Check not-before time
            self._check_token_not_before(payload)

            logger.debug(
                f"Token verified successfully for user_id: {payload['user_id']}"
            )
            return payload

        except (TokenExpiredError, InvalidTokenError):
            # Re-raise our custom exceptions
            raise

        except VerifyError as e:
            # Handle specific pyseto VerifyError cases
            error_msg = str(e).lower()

            if "expired" in error_msg:
                logger.warning("Token has expired")
                raise TokenExpiredError("Token has expired")

            if (
                "has not been activated yet" in error_msg
                or "not yet valid" in error_msg
            ):
                logger.warning(f"Token not yet valid: {str(e)}")
                raise InvalidTokenError("Token not yet valid (used before nbf time)")

            # For other VerifyError cases (malformed, tampered, etc.)
            logger.warning(f"Token verification failed: {str(e)}")
            raise InvalidTokenError("Token verification failed - invalid token")

        except DecryptError as e:
            logger.warning(f"Token decryption failed: {str(e)}")
            raise InvalidTokenError("Token verification failed - invalid token")

        except ValueError as e:
            # Catch issues with truncated tokens or malformed data
            logger.warning(f"Token parsing error: {str(e)}")
            raise InvalidTokenError("Token is malformed or truncated")

        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            raise TokenValidationError(
                "An unexpected error occurred while verifying the token",
                original_error=e,
            )

    def _validate_payload_structure(self, payload: dict[str, Any]) -> None:
        """
        Validate that the token payload has all required fields and correct types.

        Args:
            payload: The decoded token payload

        Raises:
            InvalidTokenError: If payload structure is invalid
        """
        required_fields = ["user_id", "roles", "iat", "exp", "nbf"]

        for field in required_fields:
            if field not in payload:
                raise InvalidTokenError(
                    f"Token payload missing required field: {field}"
                )

        # Validate field types
        if not isinstance(payload["user_id"], str):
            raise InvalidTokenError("Token payload 'user_id' must be a string")

        if not isinstance(payload["roles"], list):
            raise InvalidTokenError("Token payload 'roles' must be a list")

        if not payload["roles"]:
            raise InvalidTokenError("Token payload 'roles' cannot be empty")

    def _check_token_expiration(self, payload: dict[str, Any]) -> None:
        """
        Check if the token has expired.

        Args:
            payload: The decoded token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If expiration format is invalid
        """
        try:
            exp_str = payload["exp"]
            expiration = datetime.fromisoformat(exp_str)

            # Ensure timezone awareness
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=UTC)

            now = datetime.now(UTC)

            if now >= expiration:
                raise TokenExpiredError("Token has expired")

        except TokenExpiredError:
            raise

        except Exception as e:
            logger.warning(f"Invalid expiration format in token: {str(e)}")
            raise InvalidTokenError("Invalid token expiration format")

    def _check_token_not_before(self, payload: dict[str, Any]) -> None:
        """
        Check if the token is being used before its valid time.

        Args:
            payload: The decoded token payload

        Raises:
            InvalidTokenError: If token is used before nbf time
        """
        try:
            nbf_str = payload["nbf"]
            not_before = datetime.fromisoformat(nbf_str)

            # Ensure timezone awareness
            if not_before.tzinfo is None:
                not_before = not_before.replace(tzinfo=UTC)

            now = datetime.now(UTC)

            if now < not_before:
                raise InvalidTokenError("Token not yet valid (used before nbf time)")

        except InvalidTokenError:
            raise

        except Exception as e:
            logger.warning(f"Invalid not-before format in token: {str(e)}")
            raise InvalidTokenError("Invalid token not-before format")

    def decode_token_unsafe(self, token: str) -> dict[str, Any] | None:
        """
        Decode a token without verification (for debugging/inspection only).

        WARNING: This method does not verify the token signature or check
        expiration. Use only for debugging or logging purposes.

        Args:
            token: The PASETO token string to decode

        Returns:
            dict: The decoded payload, or None if decoding fails
        """
        try:
            # Decode without verification
            decoded = pyseto.decode(
                keys=self._key,
                token=token.encode("utf-8"),
                deserializer=json,
            )

            payload = cast(dict[str, Any], decoded.payload)
            return payload

        except Exception as e:
            logger.debug(f"Failed to decode token (unsafe): {str(e)}")
            return None


# Module-level convenience functions
_token_service = TokenService()


def generate_token(
    user_id: str, roles: list[str], expires_in_minutes: int | None = None
) -> str:
    """
    Module-level convenience function for token generation.

    Args:
        user_id: The user's unique identifier
        roles: List of role names assigned to the user
        expires_in_minutes: Token validity period (optional)

    Returns:
        str: The encoded PASETO token
    """
    return _token_service.generate_token(user_id, roles, expires_in_minutes)


def verify_token(token: str) -> dict[str, Any]:
    """
    Module-level convenience function for token verification.

    Args:
        token: The PASETO token string to verify

    Returns:
        dict: The decoded token payload
    """
    return _token_service.verify_token(token)
