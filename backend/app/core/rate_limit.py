from fastapi import Depends, HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.redis import get_redis
from app.security.dependencies import get_current_user

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def rate_limit(limit: int, window_seconds: int):
    async def enforce(
        request: Request,
        user: dict = Depends(get_current_user),
        redis=Depends(get_redis),
    ) -> None:
        client_ip = request.client.host if request.client else "unknown"
        route = request.scope.get("route")
        route_name = getattr(route, "name", request.url.path)
        principal = str(user.get("sub", "anonymous"))
        keys = (
            f"healthnet:rate:ip:{client_ip}:{route_name}",
            f"healthnet:rate:user:{principal}:{route_name}",
        )
        try:
            for key in keys:
                count = await redis.eval(
                    _INCREMENT_WITH_EXPIRY, 1, key, window_seconds
                )
                if int(count) > limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Retry after the current window.",
                        headers={"Retry-After": str(window_seconds)},
                    )
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting is unavailable; retry the request shortly.",
                headers={"Retry-After": "5"},
            ) from exc

    return enforce


identity_registration_limit = rate_limit(limit=10, window_seconds=60)
consent_write_limit = rate_limit(limit=20, window_seconds=60)
fhir_write_limit = rate_limit(limit=60, window_seconds=60)
