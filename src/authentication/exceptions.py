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

    This typically indicates system-level issues
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
