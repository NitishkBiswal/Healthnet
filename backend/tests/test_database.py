import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

@pytest.mark.asyncio
async def test_database_connection() -> None:
    """Test database connection. STUB: marks as skip if no DB available."""
    # Full Testcontainers integration in Segment 1
    pytest.skip("Testcontainers not configured for segment 0")
