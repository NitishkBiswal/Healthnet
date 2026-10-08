from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.provider_trust.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    ProviderCreate,
    ProviderResponse,
    PractitionerRoleCreate,
    PractitionerRoleResponse,
    TrustStatus,
)
from app.provider_trust.service import ProviderTrustService
from app.security.dependencies import require_role
from app.security.rbac import Role

router = APIRouter(tags=["Provider Trust"])


def require_admin():
    return require_role(Role.ADMIN)


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
