from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.jurisdiction_policy.schemas import (
    JurisdictionResponse,
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicyRuleCreate,
    PolicyRuleResponse,
)
from app.jurisdiction_policy.service import JurisdictionPolicyService
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["Jurisdiction Policy"])
require_admin = require_role(Role.ADMIN)


@router.post("/policy/evaluate", response_model=PolicyEvaluationResult)
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    _: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    allowed, reason, rule_id = await JurisdictionPolicyService(
        session
    ).evaluate_policy(request)
    return PolicyEvaluationResult(
        allowed=allowed, reason=reason, matched_rule_id=rule_id
    )


@router.get(
    "/policy/jurisdictions", response_model=list[JurisdictionResponse]
)
async def get_jurisdictions(
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    return await JurisdictionPolicyService(session).get_jurisdictions()


@router.get("/policy/rules", response_model=list[PolicyRuleResponse])
async def get_policy_rules(
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    return await JurisdictionPolicyService(session).get_rules()


@router.post(
    "/policy/rules",
    response_model=PolicyRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy_rule(
    request: PolicyRuleCreate,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        rule = await JurisdictionPolicyService(session).add_rule(request)
        await session.commit()
        return rule
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.delete("/policy/rules/{rule_id}", response_model=PolicyRuleResponse)
async def deactivate_policy_rule(
    rule_id: UUID,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        rule = await JurisdictionPolicyService(session).deactivate_rule(rule_id)
        await session.commit()
        return rule
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(404, str(exc)) from exc
