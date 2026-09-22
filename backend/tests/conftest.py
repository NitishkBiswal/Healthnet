"""Pytest configuration and shared fixtures for HealthNet backend tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def app_client() -> TestClient:
    """Fixture for creating a FastAPI TestClient with lifespan events.

    Using `with TestClient(...)` ensures the lifespan context manager
    runs, initializing database and Redis connections before tests execute.
    """
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# TODO: async Testcontainers fixtures in Segment 1
