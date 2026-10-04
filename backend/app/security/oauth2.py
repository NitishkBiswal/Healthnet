from typing import Any
import httpx
from jose import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_token(token: str) -> dict[str, Any]:
    try:
        discovery = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=5) as client:
            metadata = (await client.get(discovery)).raise_for_status().json()
            jwks = (await client.get(metadata["jwks_uri"])).raise_for_status().json()
        header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
        if key is None: raise ValueError("Signing key not found")
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=metadata["issuer"], options={"verify_aud": False})
        raw_roles = claims.get("realm_access", {}).get("roles", [])
        roles = {str(role).upper() for role in raw_roles}
        allowed_roles = {"PATIENT", "PROVIDER", "ADMIN", "AUDITOR", "SYSTEM"}
        roles &= allowed_roles
        if "sub" not in claims: raise ValueError("Token subject missing")
        return {"sub": claims["sub"], "email": claims.get("email"), "roles": sorted(roles), "claims": claims}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Keycloak access token", headers={"WWW-Authenticate":"Bearer"}) from exc