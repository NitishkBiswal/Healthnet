from typing import Any, Callable
from fastapi import Depends, HTTPException, status
from app.core.config import settings
from app.security.oauth2 import oauth2_scheme, verify_token
from app.security.rbac import Role

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """Dependency to get the current authenticated user."""
    # STUB: returns a mock user for Segment 0
    if settings.DEBUG:
        return {"sub": "mock_user", "roles": ["ADMIN"]}
    return await verify_token(token)

def require_role(role: Role) -> Callable[..., Any]:
    """Dependency factory to require a specific role."""
    async def role_checker(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        # STUB logic for Segment 0
        if settings.DEBUG:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {role} required"
        )
    return role_checker
