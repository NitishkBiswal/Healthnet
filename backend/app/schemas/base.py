from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class HealthResponse(BaseModel):
    service: str
    status: str
    latency_ms: int
    details: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

class AggregateHealthResponse(BaseModel):
    status: str
    version: str
    services: list[HealthResponse]

class ErrorResponse(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
