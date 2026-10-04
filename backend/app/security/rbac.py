from enum import StrEnum

class Role(StrEnum):
    PATIENT="PATIENT"; PROVIDER="PROVIDER"; ADMIN="ADMIN"; AUDITOR="AUDITOR"; SYSTEM="SYSTEM"

ROLE_PERMISSIONS:dict[Role,set[str]]={
    Role.PATIENT:{"read:own","consent:manage"},
    Role.PROVIDER:{"read:patient","write:clinical"},
    Role.ADMIN:{"*"},
    Role.AUDITOR:{"audit:read"},
    Role.SYSTEM:{"*"},
}

def has_permission(roles:list[str],permission:str)->bool:
    return any(permission in ROLE_PERMISSIONS.get(Role(role),set()) or "*" in ROLE_PERMISSIONS.get(Role(role),set()) for role in roles if role in {r.value for r in Role})
