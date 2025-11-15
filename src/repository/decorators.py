import logging
from collections.abc import Callable
from functools import wraps

logger = logging.getLogger(__name__)


def handle_repo_errors(operation_name: str):
    """Decorator to standardize error handling across repository methods."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}", exc_info=True, extra={"operation": operation_name})
                raise

        return wrapper

    return decorator
