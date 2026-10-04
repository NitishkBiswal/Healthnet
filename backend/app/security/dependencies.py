from typing import Any, Callable
from fastapi import Depends, HTTPException, status
from app.security.oauth2 import oauth2_scheme, verify_token
from app.security.rbac import Role

async def get_current_user(token:str=Depends(oauth2_scheme))->dict[str,Any]:
    return await verify_token(token)

def require_role(role:Role)->Callable[...,Any]:
    async def role_checker(user:dict[str,Any]=Depends(get_current_user))->dict[str,Any]:
        if role.value not in user.get("roles",[]): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f"Role {role.value} required")
        return user
    return role_checker
