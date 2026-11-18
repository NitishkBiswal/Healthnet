from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.jurisdiction_policy.models import Jurisdiction, PolicyRule
from app.jurisdiction_policy.schemas import PolicyEvaluationRequest, PolicyRuleCreate

class JurisdictionPolicyService:
    def __init__(self,session:AsyncSession): self.session=session
    async def evaluate_policy(self,request:PolicyEvaluationRequest):
        if request.source_jurisdiction==request.destination_jurisdiction:
            return True,"Same-jurisdiction access",None
        result=await self.session.execute(select(PolicyRule).join(Jurisdiction,PolicyRule.jurisdiction_id==Jurisdiction.id).where(
            Jurisdiction.code==request.source_jurisdiction,PolicyRule.active.is_(True),
            Jurisdiction.active.is_(True),
            PolicyRule.purpose==request.purpose,PolicyRule.scope==request.scope)
            .order_by(case((PolicyRule.effect == "DENY", 0), else_=1))
        )
        rule=result.scalars().first()
        if rule is None:return False,"No cross-jurisdiction policy rule permits this request",None
        if rule.effect!="ALLOW":return False,f"Policy rule {rule.name} denies access",rule.id
        return True,f"Policy rule {rule.name} permits access",rule.id
    async def get_rules(self, include_inactive: bool = True):
        statement = select(PolicyRule).order_by(PolicyRule.name)
        if not include_inactive:
            statement = statement.where(PolicyRule.active.is_(True))
        result=await self.session.execute(statement)
        return list(result.scalars())

    async def get_jurisdictions(self):
        result = await self.session.execute(
            select(Jurisdiction).where(Jurisdiction.active.is_(True)).order_by(Jurisdiction.name)
        )
        return list(result.scalars())

    async def add_rule(self,request:PolicyRuleCreate):
        if request.effect not in {"ALLOW", "DENY"}:
            raise ValueError("Policy effect must be ALLOW or DENY")
        jurisdiction=await self.session.scalar(select(Jurisdiction).where(Jurisdiction.code==request.jurisdiction_code))
        if jurisdiction is None: raise ValueError("Jurisdiction not found")
        rule=PolicyRule(jurisdiction_id=jurisdiction.id,**request.model_dump(exclude={"jurisdiction_code"}))
        self.session.add(rule); await self.session.flush(); return rule

    async def deactivate_rule(self, rule_id):
        rule = await self.session.get(PolicyRule, rule_id)
        if rule is None:
            raise ValueError("Policy rule not found")
        rule.active = False
        await self.session.flush()
        return rule
