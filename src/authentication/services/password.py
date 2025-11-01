"""
Password Hashing and Verification Service
"""

import logging

import argon2
from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from src.config import settings
from src.authentication.exceptions import (
    InvalidPasswordError,
    PasswordHashingError,
    PasswordVerificationError,
)

# Configure logging - note: never log passwords or hashes in production
logger = logging.getLogger(__name__)


class PasswordService:
    """
    Service class for password hashing and verification operations.

    This class encapsulates all password-related cryptographic operations

    Attributes:
        _hasher: Argon2 PasswordHasher instance with configured parameters
    """

    _instance = None

    def __new__(cls):
        """
        Implement singleton pattern to ensure single PasswordHasher instance.

        Returns:
            PasswordService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_hasher()
        return cls._instance

    def _initialize_hasher(self) -> None:
        """
        Initialize the PasswordHasher with configured parameters.

        The parameters are loaded from the application configuration
        """
        try:
            self._hasher = PasswordHasher(
                time_cost=settings.auth.ARGON2_TIME_COST,
                memory_cost=settings.auth.ARGON2_MEMORY_COST,
                parallelism=settings.auth.ARGON2_PARALLELISM,
                hash_len=settings.auth.ARGON2_HASH_LENGTH,
                salt_len=settings.auth.ARGON2_SALT_LENGTH,
                type=argon2.Type.ID,  # Argon2id variant
            )
            logger.info("PasswordHasher initialized with configured parameters")
        except Exception as e:
            logger.error(f"Failed to initialize PasswordHasher: {str(e)}")
            raise PasswordHashingError(
                "Failed to initialize password hashing service", original_error=e
            )

    def _validate_password(self, password: str) -> None:
        """
        Validate password meets minimum security requirements.

        Args:
            password: The plaintext password to validate

        Raises:
            InvalidPasswordError: If password doesn't meet requirements
        """
        if not isinstance(password, str):
            raise InvalidPasswordError("Password must be a string")

        if len(password) < settings.auth.MIN_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"Password must be at least {settings.auth.MIN_PASSWORD_LENGTH} "
                "characters long"
            )

        if len(password) > settings.auth.MAX_PASSWORD_LENGTH:
            raise InvalidPasswordError(
                f"Password must not exceed {settings.auth.MAX_PASSWORD_LENGTH} characters"
            )

        if not password.strip():
            raise InvalidPasswordError("Password cannot be empty or whitespace only")

    def hash_password(self, plain_password: str) -> str:
        """
        Args:
            plain_password: The plaintext password to hash

        Returns:
            str: The hashed password in PHC string format

        Raises:
            InvalidPasswordError: If password doesn't meet requirements
            PasswordHashingError: If hashing operation fails
        """
        # Validate password before hashing
        self._validate_password(plain_password)

        try:
            hashed_password = self._hasher.hash(plain_password)
            logger.debug("Password hashed successfully")
            return hashed_password

        except HashingError as e:
            logger.error(f"Argon2 hashing error: {str(e)}")
            raise PasswordHashingError(
                "Failed to hash password due to system error", original_error=e
            )
        except Exception as e:
            logger.error(f"Unexpected error during password hashing: {str(e)}")
            raise PasswordHashingError(
                "An unexpected error occurred while hashing the password",
                original_error=e,
            )

    def check_password(self, hashed_password: str, plain_password: str) -> bool:
        """
        Verify a plaintext password against a hashed password.

        Args:
            hashed_password: The stored hash to verify against
            plain_password: The plaintext password to verify

        Returns:
            bool: True if password matches, False otherwise

        Raises:
            InvalidPasswordError: If password format is invalid
            PasswordVerificationError: If verification operation fails
        """
        # Validate inputs
        if not isinstance(hashed_password, str) or not hashed_password.strip():
            raise PasswordVerificationError("Invalid hash format")

        if not isinstance(plain_password, str):
            raise InvalidPasswordError("Password must be a string")

        try:
            # Verify the password (raises VerifyMismatchError if incorrect)
            self._hasher.verify(hashed_password, plain_password)
            logger.debug("Password verification successful")
            return True

        except VerifyMismatchError:
            # This is expected for incorrect passwords - not an error
            logger.debug("Password verification failed - incorrect password")
            return False

        except InvalidHashError as e:
            logger.warning(f"Invalid hash format encountered: {str(e)}")
            raise PasswordVerificationError(
                "The stored password hash is invalid or corrupted", original_error=e
            )

        except VerificationError as e:
            logger.error(f"Argon2 verification error: {str(e)}")
            raise PasswordVerificationError(
                "Failed to verify password due to system error", original_error=e
            )

        except Exception as e:
            logger.error(f"Unexpected error during password verification: {str(e)}")
            raise PasswordVerificationError(
                "An unexpected error occurred while verifying the password",
                original_error=e,
            )

    def check_needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if a password hash needs to be rehashed with updated parameters.

        This should be called after successful authentication to determine if
        the password should be rehashed with newer, more secure parameters.

        Args:
            hashed_password: The stored hash to check

        Returns:
            bool: True if rehashing is recommended, False otherwise
        """
        try:
            return self._hasher.check_needs_rehash(hashed_password)
        except Exception as e:
            logger.warning(f"Failed to check if rehash needed: {str(e)}")
            # Return False on error - better to not rehash than to fail
            return False

    def verify_and_update(
        self, hashed_password: str, plain_password: str
    ) -> tuple[bool, str | None]:
        """
        Verify password and return updated hash if parameters have changed.

        This is a convenience method that combines verification
        with the rehashing check, useful during login operations.

        Args:
            hashed_password: The stored hash to verify against
            plain_password: The plaintext password to verify

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, new_hash_if_needed)
                - is_valid: True if password is correct
                - new_hash_if_needed: New hash if rehashing needed, None otherwise

        Raises:
            InvalidPasswordError: If password format is invalid
            PasswordVerificationError: If verification operation fails
        """
        is_valid = self.check_password(hashed_password, plain_password)

        if is_valid and self.check_needs_rehash(hashed_password):
            try:
                new_hash = self.hash_password(plain_password)
                return True, new_hash
            except Exception as e:
                logger.warning(f"Failed to rehash password: {str(e)}")
                # Return valid but without new hash - don't fail login
                return True, None

        return is_valid, None


# Module-level convenience functions for backward compatibility
_password_service = PasswordService()


def hash_password(plain_password: str) -> str:
    """
    Module-level convenience function for password hashing.

    Args:
        plain_password: The plaintext password to hash

    Returns:
        str: The hashed password
    """
    return _password_service.hash_password(plain_password)


def check_password(hashed_password: str, plain_password: str) -> bool:
    """
    Module-level convenience function for password verification.

    Args:
        hashed_password: The stored hash to verify against
        plain_password: The plaintext password to verify

    Returns:
        bool: True if password matches, False otherwise
    """
    return _password_service.check_password(hashed_password, plain_password)
