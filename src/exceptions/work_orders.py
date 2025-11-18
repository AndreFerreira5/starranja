"""Custom exceptions for WorkOrder operations."""


class WorkOrderError(Exception):
    """Base exception for all work order related errors."""

    pass


class WorkOrderNotFoundError(WorkOrderError):
    """Raised when a work order cannot be found."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Work order not found: {identifier}")


class ActiveWorkOrderExistsError(WorkOrderError):
    """Raised when attempting to create a work order for a vehicle that already has an active one."""

    def __init__(self, vehicle_id: str):
        self.vehicle_id = vehicle_id
        super().__init__(
            f"Vehicle {vehicle_id} already has an active work order. "
            "Only one active work order per vehicle is allowed. (RB02)"
        )


class WorkOrderNumberConflictError(WorkOrderError):
    """Raised when there's a concurrency issue generating work order numbers."""

    def __init__(self):
        super().__init__("Work order number generation conflict. Please try again.")


class WorkOrderDatabaseError(WorkOrderError):
    """Raised when a database operation fails unexpectedly."""

    def __init__(self, operation: str, details: str | None = None):
        self.operation = operation
        message = f"Database error during {operation}"
        if details:
            message += f": {details}"
        super().__init__(message)
