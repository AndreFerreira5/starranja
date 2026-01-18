"""Custom exceptions for invoice operations."""


class InvoiceError(Exception):
    """Base exception for all invoice related errors."""

    pass


class InvoiceNotFoundError(InvoiceError):
    """Raised when an invoice cannot be found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Invoice not found: {identifier}")


class InvoiceDatabaseError(InvoiceError):
    """Raised when a database operation fails unexpectedly."""

    def __init__(self, operation: str, details: str | None = None):
        self.operation = operation
        message = f"Database error during {operation}"
        if details:
            message += f": {details}"
        super().__init__(message)


class InvoiceNumberConflictError(InvoiceError):
    """Raised when there's a concurrency issue generating invoice numbers."""

    def __init__(self):
        super().__init__("Invoice number generation conflict. Please try again.")


class ClientAddressMissingError(InvoiceError):
    """Raised when the client address is missing during invoice creation."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        super().__init__(f"Client address is missing for client ID: {client_id}")
