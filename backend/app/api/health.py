import time
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings
from app.schemas.base import HealthResponse, AggregateHealthResponse

router = APIRouter(tags=["Health"])

async def check_db(session: AsyncSession) -> HealthResponse:
    start_time = time.time()
    try:
        await session.execute(text("SELECT 1"))
        latency = int((time.time() - start_time) * 1000)
        return HealthResponse(service="PostgreSQL", status="healthy", latency_ms=latency)
    except Exception as e:
        return HealthResponse(service="PostgreSQL", status="unhealthy", latency_ms=0, details={"error": str(e)})

async def check_redis(redis_client: redis.Redis) -> HealthResponse:
    start_time = time.time()
    try:
        await redis_client.ping()
        latency = int((time.time() - start_time) * 1000)
        return HealthResponse(service="Redis", status="healthy", latency_ms=latency)
    except Exception as e:
        return HealthResponse(service="Redis", status="unhealthy", latency_ms=0, details={"error": str(e)})

async def check_fhir() -> HealthResponse:
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.HAPI_FHIR_BASE_URL}/metadata", timeout=2.0)
            response.raise_for_status()
        latency = int((time.time() - start_time) * 1000)
        return HealthResponse(service="HAPI FHIR", status="healthy", latency_ms=latency)
    except Exception as e:
        return HealthResponse(service="HAPI FHIR", status="unhealthy", latency_ms=0, details={"error": str(e)})

async def check_keycloak() -> HealthResponse:
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}", timeout=2.0)
            response.raise_for_status()
        latency = int((time.time() - start_time) * 1000)
        return HealthResponse(service="Keycloak", status="healthy", latency_ms=latency)
    except Exception as e:
        return HealthResponse(service="Keycloak", status="unhealthy", latency_ms=0, details={"error": str(e)})


@router.get("/health", response_model=AggregateHealthResponse)
async def health_check(
    session: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> AggregateHealthResponse:
    services = [
        await check_db(session),
        await check_redis(redis_client),
        await check_fhir(),
        await check_keycloak(),
    ]

    overall_status = "healthy"
    for s in services:
        if s.status == "unhealthy":
            overall_status = "unhealthy"
            break
        elif s.status == "degraded" and overall_status == "healthy":
            overall_status = "degraded"

    return AggregateHealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        services=services
    )

@router.get("/health/db", response_model=HealthResponse)
async def health_check_db(session: AsyncSession = Depends(get_db)) -> HealthResponse:
    return await check_db(session)

@router.get("/health/redis", response_model=HealthResponse)
async def health_check_redis(redis_client: redis.Redis = Depends(get_redis)) -> HealthResponse:
    return await check_redis(redis_client)

@router.get("/health/fhir", response_model=HealthResponse)
async def health_check_fhir() -> HealthResponse:
    return await check_fhir()

@router.get("/health/keycloak", response_model=HealthResponse)
async def health_check_keycloak() -> HealthResponse:
    return await check_keycloak()
