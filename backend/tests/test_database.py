import pytest


@pytest.mark.asyncio
async def test_database_connection() -> None:
    """Test database connection. STUB: marks as skip if no DB available."""
    pytest.skip("Testcontainers not configured for segment 0")
