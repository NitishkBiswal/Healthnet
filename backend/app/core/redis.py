import redis.asyncio as redis

from app.core.config import settings


class RedisClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.client: redis.Redis | None = None

    async def connect(self) -> None:
        self.client = redis.from_url(self.url, decode_responses=True)

    async def disconnect(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def health_check(self) -> bool:
        if self.client is None:
            return False
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def get_client(self) -> redis.Redis:
        if self.client is None:
            await self.connect()
        return self.client  # type: ignore

    
redis_client = RedisClient(settings.REDIS_URL)


async def init_redis() -> None:
    await redis_client.connect()


async def close_redis() -> None:
    await redis_client.disconnect()


async def get_redis() -> redis.Redis:
    return await redis_client.get_client()
