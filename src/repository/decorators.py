import logging
from collections.abc import Callable
from functools import wraps

logger = logging.getLogger(__name__)


def handle_repo_errors(operation_name: str, error_class: type[Exception] | None = None):
    """
    Decorator to standardize error handling and logging across repository methods.

    Args:
        operation_name: Name of the operation for logging (e.g., "create_client")
        error_class: (Optional) Custom exception class to raise on unexpected errors.
                     Must accept arguments (operation_name, error_details).
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error
                logger.error(f"Error in {operation_name}: {e}", exc_info=True, extra={"operation": operation_name})

                # If a specific error class was provided, wrap the exception and raise it
                if error_class:
                    # We assume the error class follows the pattern: Error(operation, details)
                    # e.g., SupplierOrderDatabaseError("create", "timeout")
                    raise error_class(operation_name, str(e)) from e

                # Otherwise, just re-raise the original error (e.g., generic Exception)
                raise

        return wrapper

    return decorator
