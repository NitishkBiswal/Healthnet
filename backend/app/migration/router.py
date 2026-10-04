from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.migration.schemas import (
    TransferAuthorizationRequest,
    TransferExecuteRequest,
    TransferManifestResponse,
    TransferRequestCreate,
    TransferStatus,
)
from app.migration.service import MigrationService
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["Migration"])


def require_admin_or_system():
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        roles = set(user.get("roles", []))
        if Role.ADMIN.value not in roles and Role.SYSTEM.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or system role required",
            )
        return user

    return checker


def require_patient():
    return require_role(Role.PATIENT)


def require_system_or_admin():
    return require_admin_or_system()


@router.post(
    "/transfer-requests",
    response_model=TransferStatus,
    status_code=status.HTTP_201_CREATED,
)
async def create_transfer_request(
    request: TransferRequestCreate,
    user: dict = Depends(require_admin_or_system()),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await MigrationService(session).initiate_transfer(
            request, str(user.get("sub", "unknown"))
        )
        await session.commit()
        return item
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/transfers/{transfer_id}/status", response_model=TransferStatus)
async def get_transfer_status(
    transfer_id: UUID,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    item = await MigrationService(session).get_status(transfer_id)
    if item is None:
        raise HTTPException(404, "Transfer request not found")
    requested_by = item.requested_by
    if Role.ADMIN.value not in user.get("roles", []) and str(user.get("sub")) != requested_by:
        raise HTTPException(403, "You are not allowed to view this transfer")
    return item


@router.post(
    "/transfer-authorizations/{transfer_id}",
    response_model=TransferStatus,
)
async def authorize_transfer(
    transfer_id: UUID,
    request: TransferAuthorizationRequest,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await MigrationService(session).authorize_transfer(
            transfer_id,
            str(user.get("sub", "unknown")),
            request.authorization_reference,
        )
        await session.commit()
        return item
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.post("/transfers/{transfer_id}/issue-token")
async def issue_transfer_token(
    transfer_id: UUID,
    user: dict = Depends(require_system_or_admin()),
    session: AsyncSession = Depends(get_db),
):
    try:
        record, raw_token = await MigrationService(session).issue_transfer_token(
            transfer_id, str(user.get("sub", "system"))
        )
        await session.commit()
        return {
            "transfer_id": transfer_id,
            "authorization_token": raw_token,
            "expires_at": record.expires_at,
        }
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.post(
    "/transfers/{transfer_id}/execute",
    response_model=TransferManifestResponse,
)
async def execute_transfer(
    transfer_id: UUID,
    request: TransferExecuteRequest,
    user: dict = Depends(require_system_or_admin()),
    session: AsyncSession = Depends(get_db),
):
    try:
        manifest = await MigrationService(session).execute_transfer(
            transfer_id, request
        )
        await session.commit()
        return manifest
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
