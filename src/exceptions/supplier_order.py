"""Custom exceptions for SupplierOrder operations."""


class SupplierOrderError(Exception):
    """Base exception for all supplier order related errors."""

    pass


class SupplierOrderNotFoundError(SupplierOrderError):
    """Raised when a supplier order cannot be found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Supplier order not found: {identifier}")


class SupplierOrderDatabaseError(SupplierOrderError):
    """Raised when a database operation fails unexpectedly."""

    def __init__(self, operation: str, details: str | None = None):
        self.operation = operation
        message = f"Database error during {operation}"
        if details:
            message += f": {details}"
        super().__init__(message)
