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
    PatientTransferCreate,
    TransferReviewDecision,
)
from app.migration.service import MigrationService
from app.security.dependencies import get_current_user
from app.security.rbac import Role
from app.repository.schemas import RepositoryInfo

router = APIRouter(tags=["Migration"])


async def require_admin_or_system(user: dict = Depends(get_current_user)) -> dict:
    roles = set(user.get("roles", []))
    if Role.ADMIN.value not in roles and Role.SYSTEM.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or system role required",
        )
    return user


async def require_auditor(user: dict = Depends(get_current_user)) -> dict:
    if Role.AUDITOR.value not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Role AUDITOR required")
    return user


async def require_patient(user: dict = Depends(get_current_user)) -> dict:
    if Role.PATIENT.value not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Role PATIENT required")
    return user


@router.post(
    "/transfer-requests",
    response_model=TransferStatus,
    status_code=status.HTTP_201_CREATED,
)
async def create_transfer_request(
    request: TransferRequestCreate,
    user: dict = Depends(require_admin_or_system),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await MigrationService(session).initiate_transfer(
            request, str(user.get("sub", "unknown"))
        )
        response = TransferStatus.model_validate(item)
        await session.commit()
        return response
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.post("/my-transfers", response_model=TransferStatus, status_code=status.HTTP_201_CREATED)
async def create_my_transfer(
    request: PatientTransferCreate,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await MigrationService(session).create_patient_transfer(
            request, str(user.get("sub", "unknown"))
        )
        response = TransferStatus.model_validate(item)
        await session.commit()
        return response
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/transfer-destinations", response_model=list[RepositoryInfo])
async def transfer_destinations(
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    try:
        items = await MigrationService(session).transfer_destinations(
            str(user.get("sub", "unknown"))
        )
        return [RepositoryInfo.model_validate(item) for item in items]
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/admin/transfers", response_model=list[TransferStatus])
async def admin_transfers(
    _: dict = Depends(require_admin_or_system),
    session: AsyncSession = Depends(get_db),
):
    return await MigrationService(session).admin_transfers()


@router.post("/admin/transfers/{transfer_id}/reject", response_model=TransferStatus)
async def reject_admin_transfer(
    transfer_id: UUID,
    decision: TransferReviewDecision,
    user: dict = Depends(require_admin_or_system),
    session: AsyncSession = Depends(get_db),
):
    try:
        if decision.decision != "REJECT":
            raise ValueError("This endpoint only accepts a REJECT decision")
        item = await MigrationService(session).reject_transfer(
            transfer_id, str(user.get("sub", "unknown")), decision.reviewer_note or ""
        )
        response = TransferStatus.model_validate(item)
        await session.commit()
        return response
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/auditor/reviews", response_model=list[TransferStatus])
async def pending_transfer_reviews(
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    return await MigrationService(session).pending_transfer_reviews()


@router.post("/auditor/reviews/{transfer_id}", response_model=TransferStatus)
async def decide_transfer_review(
    transfer_id: UUID,
    decision: TransferReviewDecision,
    user: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await MigrationService(session).review_transfer(
            transfer_id, str(user.get("sub", "unknown")), decision.decision, decision.reviewer_note
        )
        response = TransferStatus.model_validate(item)
        await session.commit()
        return response
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/my-transfers", response_model=list[TransferStatus])
async def get_my_transfers(
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    return await MigrationService(session).get_patient_transfers(
        str(user.get("sub", "unknown"))
    )


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
        response = TransferStatus.model_validate(item)
        await session.commit()
        return response
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.post("/transfers/{transfer_id}/issue-token")
async def issue_transfer_token(
    transfer_id: UUID,
    user: dict = Depends(require_admin_or_system),
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
    user: dict = Depends(require_admin_or_system),
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
