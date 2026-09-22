from fastapi import Query, Request
from app.core.database import get_db
from app.core.redis import get_redis

# Re-export core dependencies
__all__ = ["get_db", "get_redis", "PaginationParams", "get_correlation_id"]

class PaginationParams:
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Skip N items"),
        limit: int = Query(100, ge=1, le=1000, description="Limit to N items"),
    ):
        self.skip = skip
        self.limit = limit

async def get_correlation_id(request: Request) -> str | None:
    """Extract correlation ID from request headers."""
    return request.headers.get("X-Correlation-ID")
