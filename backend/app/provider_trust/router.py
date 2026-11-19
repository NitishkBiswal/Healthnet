from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.provider_trust.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    ProviderCreate,
    ProviderResponse,
    ProviderOnboardRequest,
    ProviderOnboardResponse,
    PractitionerRoleCreate,
    PractitionerRoleResponse,
    TrustStatus,
    ProviderJurisdictionRequestCreate,
    ProviderJurisdictionReview,
    ProviderJurisdictionRequestResponse,
)
from app.provider_trust.service import ProviderTrustService
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["Provider Trust"])


# Use the role checker itself as the FastAPI dependency. Returning it from a
# dependency function would inject the function object instead of the user claims.
require_admin = require_role(Role.ADMIN)


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_organization(
    request: OrganizationCreate,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await ProviderTrustService(session).register_organization(request)
        await session.commit()
        return OrganizationResponse.model_validate(x)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    x = await ProviderTrustService(session).get_organization(org_id)
    if x is None:
        raise HTTPException(404, "Organization not found")
    return OrganizationResponse.model_validate(x)


@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_provider(
    request: ProviderCreate,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await ProviderTrustService(session).register_provider(request)
        await session.commit()
        return ProviderResponse.model_validate(x)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/providers/onboard",response_model=ProviderOnboardResponse,status_code=status.HTTP_201_CREATED)
async def onboard_provider(request: ProviderOnboardRequest, _: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    try:
        provider, username = await ProviderTrustService(session).onboard_provider(request)
        await session.commit()
        return ProviderOnboardResponse(provider=ProviderResponse.model_validate(provider),username=username,
            message="Doctor account and HealthNet Provider ID created successfully.")
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(409,str(exc)) from exc

@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    providers = await ProviderTrustService(session).list_providers()
    return [ProviderResponse.model_validate(x) for x in providers]


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    x = await ProviderTrustService(session).get_provider(provider_id)
    if x is None:
        raise HTTPException(404, "Provider not found")
    return ProviderResponse.model_validate(x)


@router.post("/organizations/{org_id}/status", response_model=OrganizationResponse)
async def set_org_status(
    org_id: UUID,
    status_value: TrustStatus,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await ProviderTrustService(session).set_organization_status(
            org_id, status_value
        )
        await session.commit()
        return OrganizationResponse.model_validate(x)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/providers/{provider_id}/status", response_model=ProviderResponse)
async def set_provider_status(
    provider_id: UUID,
    status_value: TrustStatus,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await ProviderTrustService(session).set_provider_status(
            provider_id, status_value
        )
        await session.commit()
        return ProviderResponse.model_validate(x)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/providers/me/jurisdiction-requests", response_model=list[ProviderJurisdictionRequestResponse])
async def my_jurisdiction_requests(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        items = await ProviderTrustService(session).list_my_jurisdiction_requests(str(user.get("sub", "")))
        return [ProviderJurisdictionRequestResponse.model_validate(item) for item in items]
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/providers/me/jurisdiction-requests", response_model=ProviderJurisdictionRequestResponse, status_code=201)
async def create_my_jurisdiction_request(
    request: ProviderJurisdictionRequestCreate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await ProviderTrustService(session).create_jurisdiction_request(
            str(user.get("sub", "")), request
        )
        await session.commit()
        return ProviderJurisdictionRequestResponse.model_validate(item)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/jurisdiction-requests", response_model=list[ProviderJurisdictionRequestResponse])
async def list_jurisdiction_requests(
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    items = await ProviderTrustService(session).list_jurisdiction_requests()
    return [ProviderJurisdictionRequestResponse.model_validate(item) for item in items]


@router.post("/jurisdiction-requests/{request_id}/review", response_model=ProviderJurisdictionRequestResponse)
async def review_jurisdiction_request(
    request_id: UUID,
    decision: ProviderJurisdictionReview,
    user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        item = await ProviderTrustService(session).review_jurisdiction_request(
            request_id, str(user.get("sub", "unknown")),
            decision.decision, decision.reviewer_note,
        )
        await session.commit()
        return ProviderJurisdictionRequestResponse.model_validate(item)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.post("/roles", response_model=PractitionerRoleResponse, status_code=201)
async def assign_role(
    request: PractitionerRoleCreate,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await ProviderTrustService(session).assign_role(request)
        await session.commit()
        return PractitionerRoleResponse.model_validate(x)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
