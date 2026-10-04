from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.jurisdiction_policy.schemas import PolicyEvaluationRequest,PolicyEvaluationResult,PolicyRuleCreate
from app.jurisdiction_policy.service import JurisdictionPolicyService
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role
router=APIRouter(tags=["Jurisdiction Policy"])
def require_admin(): return require_role(Role.ADMIN)
@router.post("/policy/evaluate",response_model=PolicyEvaluationResult)
async def evaluate_policy(request:PolicyEvaluationRequest,_:dict=Depends(get_current_user),session:AsyncSession=Depends(get_db)):
    allowed,reason,rule_id=await JurisdictionPolicyService(session).evaluate_policy(request);return PolicyEvaluationResult(allowed=allowed,reason=reason,matched_rule_id=rule_id)
@router.get("/policy/rules")
async def get_policy_rules(_:dict=Depends(require_admin),session:AsyncSession=Depends(get_db)):return await JurisdictionPolicyService(session).get_rules()
@router.post("/policy/rules",status_code=201)
async def create_policy_rule(request:PolicyRuleCreate,_:dict=Depends(require_admin),session:AsyncSession=Depends(get_db)):
    try:x=await JurisdictionPolicyService(session).add_rule(request);await session.commit();return {"id":x.id,"name":x.name}
    except ValueError as exc:await session.rollback();raise HTTPException(400,str(exc)) from exc