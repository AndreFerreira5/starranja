"""
Defines custom exceptions for authentication
operations, providing clear error handling
and appropriate HTTP status code mappings.
"""


class AuthenticationError(Exception):
    """
    Base exception for authentication-related errors.
    This serves as the parent class for all authentication exceptions,
    allowing for broad exception handling when needed.
    """

    def __init__(self, message: str = "Authentication failed", status_code: int = 401):
        """
        Initialize the authentication error.

        Args:
            message: Human-readable error description
            status_code: HTTP status code for API responses
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PasswordHashingError(AuthenticationError):
    """
    Exception raised when password hashing operations fail.
    This typically indicates system-level issues,
    insufficient memory or invalid configuration.
    """

    def __init__(
        self,
        message: str = "Password hashing failed",
        original_error: Exception | None = None,
    ):
        """
        Initialize the password hashing error.

        Args:
            message: Error description
            original_error: The underlying exception that caused this error
        """
        self.original_error = original_error
        super().__init__(message, status_code=500)


class PasswordVerificationError(AuthenticationError):
    """
    Exception raised when password verification operations fail.
    Can occur due to corrupted hash strings or system errors
    during verification (distinct from incorrect passwords).
    """

    def __init__(
        self,
        message: str = "Password verification failed",
        original_error: Exception | None = None,
    ):
        """
        Initialize the password verification error.

        Args:
            message: Error description
            original_error: The underlying exception that caused this error
        """
        self.original_error = original_error
        super().__init__(message, status_code=500)


class InvalidPasswordError(AuthenticationError):
    """
    Exception raised when a provided password doesn't meet security requirements.
    Used for password validation during registration or password changes.
    """

    def __init__(self, message: str = "Password does not meet security requirements"):
        """
        Initialize the invalid password error.

        Args:
            message: Description of why the password is invalid
        """
        super().__init__(message, status_code=400)


# ============================================================================
# Token-specific exceptions
# ============================================================================


class TokenError(AuthenticationError):
    """
    Base exception for token-related errors.
    This serves as the parent class for all token exceptions,
    allowing for broad token error handling when needed.
    """

    def __init__(
        self,
        message: str = "Token operation failed",
        status_code: int = 401,
        original_error: Exception | None = None,
    ):
        """
        Initialize the token error.

        Args:
            message: error description
            status_code: HTTP status code for API responses
            original_error: The underlying exception that caused this error
        """
        self.original_error = original_error
        super().__init__(message, status_code)


class TokenGenerationError(TokenError):
    """
    Exception raised when token generation operations fail.
    This typically indicates system-level issues
    or invalid input parameters during token creation.
    """

    def __init__(
        self,
        message: str = "Token generation failed",
        original_error: Exception | None = None,
    ):
        """
        Initialize the token generation error.

        Args:
            message: Error description
            original_error: The underlying exception that caused this error
        """
        super().__init__(message, status_code=500, original_error=original_error)


class TokenValidationError(TokenError):
    """
    Exception raised when token validation operations fail.
    It indicates a system error during validation.
    """

    def __init__(
        self,
        message: str = "Token validation failed",
        original_error: Exception | None = None,
    ):
        """
        Initialize the token validation error.

        Args:
            message: Error description
            original_error: The underlying exception that caused this error
        """
        super().__init__(message, status_code=500, original_error=original_error)


class InvalidTokenError(TokenError):
    """
    Exception raised when a token is invalid or malformed
    This indicates the token itself is not valid
    """

    def __init__(
        self,
        message: str = "Invalid or malformed token",
        original_error: Exception | None = None,
    ):
        """
        Initialize the invalid token error.

        Args:
            message: Description of why the token is invalid
            original_error: The underlying exception that caused this error
        """
        super().__init__(message, status_code=401, original_error=original_error)


class TokenExpiredError(TokenError):
    """
    Exception raised when a token has expired.
    This is a specific case of an invalid token that warrants
    distinct handling (e.g., prompting for re-authentication).
    """

    def __init__(
        self,
        message: str = "Token has expired",
        original_error: Exception | None = None,
    ):
        """
        Initialize the token expired error.

        Args:
            message: Description of the expiration
            original_error: The underlying exception that caused this error
        """
        super().__init__(message, status_code=401, original_error=original_error)
