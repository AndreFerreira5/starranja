"""Custom exceptions for Client operations."""


class ClientError(Exception):
    """Base exception for all client related errors."""

    pass


class ClientNotFoundError(ClientError):
    """Raised when a client cannot be found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Client not found: {identifier}")


class DuplicateClientNIFError(ClientError):
    """Raised when attempting to create/update a client with a duplicate NIF."""

    def __init__(self, nif: str):
        self.nif = nif
        super().__init__(f"Client with NIF {nif} already exists. NIF must be unique.")


class DuplicateClientEmailError(ClientError):
    """Raised when attempting to create/update a client with a duplicate Email."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Client with Email {email} already exists. Email must be unique.")


class ClientDatabaseError(ClientError):
    """Raised when a database operation fails unexpectedly."""

    def __init__(self, operation: str, details: str | None = None):
        self.operation = operation
        message = f"Database error during {operation}"
        if details:
            message += f": {details}"
        super().__init__(message)


class InvalidClientDataError(ClientError):
    """Raised when client data validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Invalid {field}: {message}")


class ClientHasActiveWorkOrdersError(ClientError):
    """Raised when attempting to delete a client that has active work orders."""

    def __init__(self, client_id: str, count: int):
        self.client_id = client_id
        self.count = count
        super().__init__(f"Cannot delete client {client_id}: Client has {count} active work orders.")
